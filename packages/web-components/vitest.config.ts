import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const sdk = fileURLToPath(new URL("../frontend-sdk/src/index.ts", import.meta.url));

export default defineConfig({
  resolve: {
    // Every package installs its own dependencies, so a linked sibling brings a second copy
    // of these along. `@dodona/lit-state` keeps its read recorder in a module-level
    // singleton and `lit` its element registry in another, so two copies mean a store
    // records a read that the component's controller never sees - reactivity silently stops.
    dedupe: ["lit", "@dodona/lit-state", "@lit/context", "@awesome.me/webawesome"],
    alias: {
      // Test against the sibling's sources, so its build output cannot go stale under us.
      "@cofy/frontend-sdk": sdk,
    },
  },
  test: {
    coverage: {
      // Without this, coverage only counts files a test happens to import, so an untested
      // file is invisible rather than counted against the 80% floor CI enforces on this
      // package - naming every file here is what makes an untested one count as 0% instead.
      include: ["src/**/*.ts"],
      reporter: ["text", "lcov", "cobertura"],
    },
    // Lit components need a DOM; jsdom is enough for the rendering these tests assert on.
    environment: "jsdom",
    setupFiles: ["./test/setup.ts"],
    // Off by default, which silently resolves every `?raw` CSS import - `nativeStyles` and
    // `layoutStyles` among them - to an empty string rather than failing loudly.
    css: true,
  },
});
