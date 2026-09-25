import { cp, readFile, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vite";

const workspace = (path: string): string => fileURLToPath(new URL(path, import.meta.url));

/**
 * Serves `@cofy/web-components`' own translations under `/locales`, beside the app's.
 *
 * The library ships its `components` namespace as YAML rather than bundling it, so a
 * deployment can correct or add a translation without a rebuild - which means something has
 * to put those files on the same origin as the app. Vite's `public/` covers the app's own
 * files; this covers the library's.
 *
 * The app wins where both have a file, so overriding one of the library's strings is a matter
 * of dropping a file into `public/locales`.
 */
function libraryLocales(): Plugin {
  const source = workspace("../../packages/web-components/locales");
  const ours = workspace("public/locales");
  const exists = async (path: string): Promise<boolean> => stat(path).then(() => true, () => false);

  return {
    name: "cofy-library-locales",
    configureServer(server): void {
      // Registered before Vite's own middleware rather than after it: the SPA fallback answers
      // anything still unhandled with `index.html`, so a locale served later never gets asked
      // for. That means checking `public/` here instead of letting Vite do it, which is what
      // keeps the app's copy of a file winning over the library's.
      server.middlewares.use("/locales", (request, response, next) => {
        const path = decodeURIComponent((request.url ?? "").split("?")[0] ?? "");
        if (!/^\/[a-z]{2}(-[A-Za-z]+)?\/[a-z-]+\.yaml$/.test(path)) {
          next();
          return;
        }
        exists(ours + path)
          .then(async (mine) => (mine ? null : readFile(source + path)))
          .then((body) => {
            // `null` means the app has its own copy, which Vite serves from `public/`.
            if (body === null) {
              next();
              return;
            }
            response.setHeader("content-type", "text/yaml; charset=utf-8");
            response.end(body);
          })
          .catch(() => {
            // A locale nobody has is missing, not a page. Falling through would hand i18next
            // the SPA fallback's `index.html` to parse as YAML.
            response.statusCode = 404;
            response.end();
          });
      });
    },
    async closeBundle(): Promise<void> {
      // `force: false` leaves the app's copies alone, matching dev's precedence.
      if (await exists(source)) await cp(source, workspace("dist/locales"), { recursive: true, force: false });
    },
  };
}

export default defineConfig(({ command }) => ({
  plugins: [libraryLocales()],
  resolve: {
    // `@dodona/lit-state` keeps a module-level recorder and `lit` a module-level element
    // registry, so a second copy of either silently breaks reactivity. Each package has its
    // own node_modules, which is exactly how a second copy gets in.
    dedupe: ["lit", "@dodona/lit-state", "@lit/context", "@awesome.me/webawesome"],
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
