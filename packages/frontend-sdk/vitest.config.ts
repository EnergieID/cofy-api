import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: {
      // Without this, coverage only counts files a test happens to import, so an untested
      // file is invisible rather than counted against the 80% floor CI enforces on this
      // package - naming every file here is what makes an untested one count as 0% instead.
      include: ["src/**/*.ts"],
      reporter: ["text", "lcov", "cobertura"],
    },
  },
});
