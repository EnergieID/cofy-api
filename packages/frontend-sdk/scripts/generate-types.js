/**
 * Regenerate `src/generated/api.ts` from the management API's OpenAPI document.
 *
 * The document is read straight out of the Python app rather than from a running server, so
 * generating types needs nothing started and cannot pick up a stale process.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const managementApi = resolve(packageRoot, "../management-api");

const openapi = execFileSync(
  "uv",
  [
    "run",
    "--project",
    managementApi,
    "--directory",
    managementApi,
    "python",
    "-c",
    "import json; from cofy.management.main import app; print(json.dumps(app.openapi()))",
  ],
  { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 },
);

// openapi-typescript reads a path, not stdin.
const scratch = mkdtempSync(join(tmpdir(), "cofy-openapi-"));
const document = join(scratch, "openapi.json");
try {
  writeFileSync(document, openapi);
  // `--default-non-nullable` (on by default) marks a field with a schema default as always
  // present. That is true of a response, but these schemas are request bodies too, and there
  // a defaulted field is exactly the one the caller may leave out.
  const args = ["openapi-typescript", document, "-o", "src/generated/api.ts", "--default-non-nullable", "false"];
  execFileSync("npx", args, {
    cwd: packageRoot,
    stdio: "inherit",
  });
} finally {
  rmSync(scratch, { recursive: true, force: true });
}
