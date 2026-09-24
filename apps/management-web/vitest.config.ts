import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // This app is mostly composition of `@cofy/web-components`/`@cofy/frontend-sdk`, which
    // carry their own coverage floor - no threshold here, just a report for visibility.
    coverage: {
      reporter: ["text", "lcov", "cobertura"],
    },
    // The route state reads and writes `window.location`, so these need a document.
    environment: "jsdom",
  },
});
