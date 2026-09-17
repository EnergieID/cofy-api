import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // The route state reads and writes `window.location`, so these need a document.
    environment: "jsdom",
  },
});
