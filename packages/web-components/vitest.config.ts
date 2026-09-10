import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const sdk = fileURLToPath(new URL("../frontend-sdk/src/index.ts", import.meta.url));

export default defineConfig({
  resolve: {
    // Every package installs its own dependencies, so a linked sibling brings a second copy
    // of these along. `@dodona/lit-state` keeps its read recorder in a module-level
    // singleton and `lit` its element registry in another, so two copies mean a store
    // records a read that the component's controller never sees - reactivity silently stops.
    dedupe: ["lit", "@dodona/lit-state", "@lit/context", "@carbon/web-components"],
    alias: {
      // Test against the sibling's sources, so its build output cannot go stale under us.
      "@cofy/frontend-sdk": sdk,
    },
  },
  test: {
    // Lit components need a DOM; jsdom is enough for the rendering these tests assert on.
    environment: "jsdom",
    setupFiles: ["./test/setup.ts"],
  },
});
