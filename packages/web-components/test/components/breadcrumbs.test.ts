import { beforeEach, describe, expect, it } from "vitest";

import { CofyBreadcrumbs } from "../../src/components/layout/cofy-breadcrumbs.js";
import { testI18n } from "../support/i18n.js";

async function mount(crumbs: { label: string; href?: string }[]): Promise<CofyBreadcrumbs> {
  const element = new CofyBreadcrumbs();
  element.i18n = await testI18n();
  element.crumbs = crumbs;
  document.body.append(element);
  await element.updateComplete;
  return element;
}

describe("cofy-breadcrumbs", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("renders nothing for an empty trail", async () => {
    const element = await mount([]);

    expect(element.shadowRoot!.querySelector("wa-breadcrumb")).toBeNull();
  });

  it("links every crumb but the last", async () => {
    const element = await mount([
      { label: "Demo Energy Community", href: "#/c/demo" },
      { label: "default" },
    ]);

    const items = Array.from(element.shadowRoot!.querySelectorAll("wa-breadcrumb-item"));

    expect(items.map((item) => item.getAttribute("href"))).toEqual(["#/c/demo", null]);
  });

  it("does not give the current page a click-through href", async () => {
    // wa-breadcrumb-item treats any string - even an empty one - as a real link, so an
    // `href=""` rendered a genuine <a> whose empty target silently navigated to the page's
    // URL without its hash, which this app's hash router then read back as "/". The fix is to
    // not set `href` at all for the current page, which renders a plain, non-navigating
    // button instead of a link.
    const element = await mount([{ label: "default" }]);

    const item = element.shadowRoot!.querySelector("wa-breadcrumb-item")!;

    expect(item.hasAttribute("href")).toBe(false);
    expect(item.shadowRoot!.querySelector("a")).toBeNull();
    expect(item.shadowRoot!.querySelector("button")).not.toBeNull();
  });

  it("marks the current page for assistive technology, since the component does not do it itself", async () => {
    const element = await mount([{ label: "Demo Energy Community", href: "#/c/demo" }, { label: "default" }]);

    const items = Array.from(element.shadowRoot!.querySelectorAll("wa-breadcrumb-item"));

    expect(items.map((item) => item.getAttribute("aria-current"))).toEqual([null, "page"]);
  });
});
