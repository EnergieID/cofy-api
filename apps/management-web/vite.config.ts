import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const workspace = (path: string): string => fileURLToPath(new URL(path, import.meta.url));

export default defineConfig(({ command }) => ({
  resolve: {
    // `@dodona/lit-state` keeps a module-level recorder and `lit` a module-level element
    // registry, so a second copy of either silently breaks reactivity. Each package has its
    // own node_modules, which is exactly how a second copy gets in.
    dedupe: ["lit", "@dodona/lit-state", "@lit/context", "@carbon/web-components"],
    // In development the workspace packages resolve to their sources, so editing a component
    // is reflected immediately instead of needing a rebuild first. The production build is
    // deliberately left alone: it goes through each package's real entry points, which is
    // what an outside consumer gets, so a broken `exports` map fails here rather than after
    // publishing.
    alias: [
      // `@dodona/lit-state` ships no `exports` map, which is enough for `dedupe` above to
      // miss it - and every package having its own copy then means the store records a read
      // into one module-level recorder while the component's controller watches another, so
      // reactivity silently stops. Pinning it to a single file leaves no room for that.
      { find: /^@dodona\/lit-state$/, replacement: workspace("node_modules/@dodona/lit-state/dist/index.js") },
      ...(command === "serve"
        ? [
            { find: /^@cofy\/frontend-sdk$/, replacement: workspace("../../packages/frontend-sdk/src/index.ts") },
            { find: /^@cofy\/web-components$/, replacement: workspace("../../packages/web-components/src/index.ts") },
          ]
        : []),
    ],
  },
  server: {
    // Proxying keeps the browser on a single origin during development, so the app talks to
    // the management API exactly as it will when the API serves it - no CORS, no separate
    // base URL to configure.
    proxy: {
      "/management": {
        target: process.env["COFY_MANAGEMENT_API"] ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
}));
