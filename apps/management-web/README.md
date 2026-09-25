# Cofy management console

The default management console for a Cofy deployment: a web UI for creating and configuring
communities and their modules against the [Cofy Management API](../../packages/management-api).
It's built from [@cofy/web-components](../../packages/web-components) and
[@cofy/frontend-sdk](../../packages/frontend-sdk); route 2 in the [root README](../../README.md)
uses this app, and [apps/demo_multitenant](../demo_multitenant) packages it together with the
management API into a single deployable image.

You don't need to touch this app just to run route 2 - see
[apps/demo_multitenant](../demo_multitenant) for that. Come here if you want to run the console
on its own, customise it (branding, translations, pages), or use it as a starting point for your
own.

## Running locally

Expects a management API on `:8000` (see
[apps/demo_multitenant](../demo_multitenant#running) for how to start one against seeded local
data):

```sh
npm install
npm run dev
```

Serves the console at http://127.0.0.1:5173, proxying `/management` requests to the API so the
browser only ever talks to one origin - no CORS, no base URL to configure. Point it at a
different API with `COFY_MANAGEMENT_API=http://host:port npm run dev`.

## Customising

- **Branding** - [src/brand.css](src/brand.css) is the one place the console's colour is
  decided: eleven CSS custom properties (a light/dark colour ramp), and Web Awesome derives
  every button, link and focus ring from them. No code, no build step.
- **Translations** - the app's own strings live in `public/locales/<lang>/app.yaml`;
  `@cofy/web-components`' strings live in `public/locales/<lang>/components.yaml`, overriding
  the library's own copy under
  [packages/web-components/locales](../../packages/web-components/locales). Add a language by
  adding both files; correct a string by editing one.
- **Icons** - [src/icons.ts](src/icons.ts) stops Web Awesome fetching icons from its default CDN
  at runtime (useful if the console runs on an isolated network); swap in your own icon set
  there if needed.
- **Pages** - adding a page is one new module under [src/pages](src/pages) plus one entry in
  [src/routes.ts](src/routes.ts); nothing else needs to know about it.

## Development

```sh
npm install
npm test
npm run check
npm run lint
npm run build      # outputs to dist/, served by the management API in production - see
                    # apps/demo_multitenant/Dockerfile
```
