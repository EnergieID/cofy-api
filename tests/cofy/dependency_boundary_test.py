"""
Verify that every import in src/cofy/ is accounted for.

Each import must be one of:
  A. Python standard library
  B. An explicit core dependency (always installed)
  C. An optional dependency allowed for the file's zone
  D. An internal cofy import targeting an accessible zone

Core deps, optional deps, and extra→extra dependencies are all parsed
from pyproject.toml.  The only manual config is:
  - EXTRA_ZONES        — which source path prefix each extra "owns"
  - IMPORT_OVERRIDES   — PyPI names whose import name ≠ normalised name
"""

import ast
import re
import sys
import tomllib
from importlib import resources
from pathlib import Path, PurePosixPath

import pytest

# ── Manual config (everything else is derived from pyproject.toml) ───────

# PyPI names whose import name differs from the normalised form.
IMPORT_OVERRIDES: dict[str, set[str]] = {
    "entsoe-py": {"entsoe"},
}

# Extra name → source path prefix(es) it "owns" (relative to src/cofy/).
EXTRA_ZONES: dict[str, set[str]] = {
    "timeseries": {"modules/timeseries/"},
    "tariff": {"modules/tariff/"},
    "billing": {"modules/billing/"},
    "production": {"modules/production/"},
    "members": {"modules/members/"},
    "directive": {"modules/directive/"},
    "debug": {"api/debug_"},
}

# Zones that are always accessible (no extra required).
CORE_ZONES: set[str] = {"api/", "__init__.py"}


# ── pyproject.toml parsing ───────────────────────────────────────────────
def _parse_pyproject() -> dict:
    path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    return tomllib.loads(path.read_text())


def _dep_name(spec: str) -> str:
    """Extract the bare package name from a PEP 508 dependency string."""
    return re.split(r"[\[>=<~!;@ ]", spec, maxsplit=1)[0].strip()


def _normalise(name: str) -> str:
    """PyPI name → default import name (PEP 503 normalisation)."""
    return re.sub(r"[-_.]+", "_", name).lower()


def _build_config() -> tuple[set[str], dict[str, set[str]], dict[str, set[str]]]:
    """Parse pyproject.toml and return (core_packages, extra_packages, allowed_extras).

    - core_packages: import names always available
    - extra_packages: extra name → set of import names it provides
    - allowed_extras: zone prefix → set of extra names the zone may use
    """
    cfg = _parse_pyproject()
    project_name = cfg["project"]["name"]

    # Core third-party packages
    core = {_normalise(_dep_name(d)) for d in cfg["project"].get("dependencies", [])}

    # Optional packages and inter-extra dependencies
    extra_packages: dict[str, set[str]] = {}
    extra_deps: dict[str, set[str]] = {}

    for extra, specs in cfg["project"].get("optional-dependencies", {}).items():
        if extra == "all":
            continue
        pkgs: set[str] = set()
        deps: set[str] = set()
        for spec in specs:
            name = _dep_name(spec)
            if _normalise(name) == _normalise(project_name):
                # Self-reference like cofy-api[timeseries] → extra dependency
                m = re.search(r"\[([^\]]+)\]", spec)
                if m:
                    deps |= {e.strip() for e in m.group(1).split(",")}
            else:
                pkgs.add(_normalise(name))
                pkgs |= IMPORT_OVERRIDES.get(name, set())
        extra_packages[extra] = pkgs
        extra_deps[extra] = deps

    # Resolve transitive extra deps (e.g. tariff → timeseries)
    def resolve(extra: str, seen: set[str] | None = None) -> set[str]:
        seen = seen or set()
        if extra not in seen:
            seen.add(extra)
            for dep in extra_deps.get(extra, set()):
                resolve(dep, seen)
        return seen

    # Build zone → allowed extras (with transitive resolution)
    allowed_extras: dict[str, set[str]] = {}
    for extra, prefixes in EXTRA_ZONES.items():
        resolved = resolve(extra)
        for prefix in prefixes:
            allowed_extras[prefix] = resolved

    return core, extra_packages, allowed_extras


STDLIB: frozenset[str] = sys.stdlib_module_names
CORE_PACKAGES, EXTRA_PACKAGES, ALLOWED_EXTRAS = _build_config()
ALL_ZONES: set[str] = {z for zs in EXTRA_ZONES.values() for z in zs} | CORE_ZONES


# ── Zone matching (single implementation for both files and imports) ─────
def _match_zone(path: str) -> str | None:
    """Find the zone that *path* belongs to (longest prefix wins)."""
    for zone in sorted(ALL_ZONES, key=lambda z: len(z), reverse=True):
        if zone.endswith("/"):
            if path.startswith(zone) or path.rstrip("/") + "/" == zone:
                return zone
        elif path == zone or path == zone.removesuffix(".py"):
            return zone
    return None


def _allowed_packages(relpath: str) -> set[str]:
    """All third-party import names a file at *relpath* may use."""
    allowed = set(CORE_PACKAGES)
    for prefix, extras in ALLOWED_EXTRAS.items():
        if relpath.startswith(prefix) or relpath == prefix:
            for extra in extras:
                allowed |= EXTRA_PACKAGES.get(extra, set())
    return allowed


def _accessible_zones(relpath: str) -> set[str]:
    """All internal zones a file at *relpath* may import from."""
    zones = set(CORE_ZONES)
    own = _match_zone(relpath)
    if own:
        zones.add(own)
    for prefix, extras in ALLOWED_EXTRAS.items():
        if relpath.startswith(prefix) or relpath == prefix:
            for extra in extras:
                zones |= EXTRA_ZONES.get(extra, set())
    return zones


# ── Import extraction ────────────────────────────────────────────────────
def _extract_imports(path: Path, relpath: str) -> tuple[set[str], set[str]]:
    """Return (third_party_names, cofy_internal_subpaths) from static analysis."""
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError:
        return set(), set()

    third_party: set[str] = set()
    internal: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _classify(alias.name, 0, relpath, third_party, internal)

        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                _classify(node.module, 0, relpath, third_party, internal)
            elif node.level and node.level > 0:
                # Relative import → resolve to cofy-internal path
                parts = list(PurePosixPath(relpath).parent.parts)
                base = parts[: max(0, len(parts) - (node.level - 1))]
                if node.module:
                    base += node.module.split(".")
                internal.add("/".join(base))

    return third_party, internal


def _classify(module: str, level: int, relpath: str, third_party: set[str], internal: set[str]) -> None:
    top = module.split(".")[0]
    if top == "cofy":
        rest = module.split(".", 1)[1] if "." in module else ""
        internal.add(rest.replace(".", "/"))
    elif top not in STDLIB:
        third_party.add(top)


# ── Test ─────────────────────────────────────────────────────────────────
def _collect() -> list[tuple[str, Path]]:
    with resources.as_file(resources.files("cofy")) as root:
        return [(str(f.relative_to(root)), f) for f in sorted(root.rglob("*.py"))]


_CASES = _collect()


@pytest.mark.parametrize(("relpath", "filepath"), _CASES, ids=[c[0] for c in _CASES])
def test_imports_respect_dependency_boundaries(relpath: str, filepath: Path):
    third_party, internal = _extract_imports(filepath, relpath)

    # Third-party: must be stdlib, core, or an allowed extra
    allowed = _allowed_packages(relpath)
    undeclared = third_party - allowed
    assert not undeclared, f"{relpath} imports undeclared third-party packages: {undeclared}. Allowed: {allowed}."

    # Internal: target zone must be accessible
    zones = _accessible_zones(relpath)
    for imp in internal:
        if not imp:
            continue
        target = _match_zone(imp)
        if target is None:
            continue
        assert target in zones, (
            f"{relpath} imports from zone '{target}' "
            f"(via cofy.{imp.replace('/', '.')}) which is not accessible. "
            f"Accessible zones: {zones}."
        )
