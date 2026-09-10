import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

// Vite rewrites `import.meta.url` to a `/@fs/` path, so the root comes from the working
// directory, which vitest sets to the package being tested.
const repoRoot = resolve(process.cwd(), "../..");

function sourceFiles(directory: string): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(directory)) {
    if (entry === "node_modules" || entry === "dist") continue;
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) found.push(...sourceFiles(path));
    else if (path.endsWith(".ts")) found.push(path);
  }
  return found;
}

/**
 * The library packages must not reach into the app.
 *
 * This project's only consumer of the components is the console next door, which is exactly
 * the situation in which app-shaped logic quietly settles in a package - or worse, a package
 * starts importing from the app. Anything useful to a second consumer belongs in a package;
 * this is what keeps that honest.
 */
describe("library packages", () => {
  const packages = ["packages/frontend-sdk/src", "packages/web-components/src"];

  it.each(packages)("%s does not import from apps/", (relative) => {
    const offenders = sourceFiles(join(repoRoot, relative)).filter((file) => {
      const source = readFileSync(file, "utf8");
      return /from\s+["'][^"']*(apps\/|@cofy\/management-web)/.test(source);
    });

    expect(offenders).toEqual([]);
  });

  it("web-components depends on the sdk only through its package entry point", () => {
    const offenders = sourceFiles(join(repoRoot, "packages/web-components/src")).filter((file) => {
      const source = readFileSync(file, "utf8");
      return /from\s+["'][^"']*frontend-sdk\/(src|dist)/.test(source);
    });

    expect(offenders).toEqual([]);
  });
});
