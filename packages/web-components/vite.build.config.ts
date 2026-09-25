import { readdirSync } from "node:fs";
import { extname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const srcDir = fileURLToPath(new URL("src", import.meta.url));

/**
 * Every source file, as its own Rollup entry.
 *
 * Rollup's `output.preserveModules` looks like the tool for keeping `dist` shaped like `src`,
 * but its own docs warn it off: it still tree-shakes, including dropping files "that ... do not
 * have side effects when executed" - which is exactly how this repo lost its icon and custom
 * element registrations to silent dead-code elimination. The docs' own recommended alternative
 * for this is what's here instead: designate every file as its own entry point (Rollup never
 * tree-shakes an entry module away, only unused exports of one), and let Rollup's ordinary
 * chunking hoist genuinely shared code into its own chunk rather than duplicating it.
 */
function entries(): Record<string, string> {
  const files = readdirSync(srcDir, { recursive: true })
    .map(String)
    .filter((file) => file.endsWith(".ts") && !file.endsWith(".d.ts"));

  return Object.fromEntries(
    files.map((file) => [relative(srcDir, join(srcDir, file)).slice(0, -extname(file).length), join(srcDir, file)]),
  );
}

export default defineConfig({
  build: {
    outDir: "dist",
    // Declarations come from `tsc`, run separately - see package.json. Emptying here would
    // race it, whichever script runs second wiping out the other's output.
    emptyOutDir: false,
    lib: {
      entry: entries(),
      formats: ["es"],
    },
    rollupOptions: {
      // A bare specifier - `lit`, `@awesome.me/webawesome`, CodeMirror's own dependency tree -
      // is left as the import it already is, exactly as the `tsc`-built output did, so the
      // *consumer's* single install of each resolves it. Bundling any of it in here instead
      // risks the exact bug `dedupe` exists elsewhere in this repo to prevent: a second copy of
      // a package that keeps module-level state (`@dodona/lit-state`'s read recorder, or here,
      // whatever singleton CodeMirror's own `@lezer/*`/`style-mod` keep) breaks silently the
      // moment two copies both think they are the only one.
      //
      // Two things are deliberately *not* treated as external, despite being bare specifiers:
      // - A resource query (`?raw` and the like) is an instruction for *this* build to resolve
      //   and inline the file, not a runtime import - `@awesome.me/webawesome/.../native.css?raw`
      //   is exactly that, and leaving it external would ship the raw specifier nowhere able to
      //   resolve it instead of the string it is meant to become.
      // - `@oxc-project/runtime`, Rolldown's own helper package for the legacy decorators this
      //   package's components use (`@customElement`, `@property`, ...) - not a dependency we or
      //   a consumer ever installs, so it has to be bundled as part of our own output instead.
      external: (id: string) => !id.includes("?") && !id.startsWith("@oxc-project/runtime") && !id.startsWith(".") && !id.startsWith("/"),
      output: {
        entryFileNames: "[name].js",
      },
    },
    // This package's own components register custom elements and set up icon libraries as
    // import-time side effects; minifying is not worth the risk of a consumer's bundler
    // dropping one it doesn't see used.
    minify: false,
  },
});
