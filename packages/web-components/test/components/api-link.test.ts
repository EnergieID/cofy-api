import { beforeEach, describe, expect, it } from "vitest";

import { CofyApiLink } from "../../src/components/community/cofy-api-link.js";
import { testI18n } from "../support/i18n.js";

async function mount(url: string): Promise<CofyApiLink> {
  const element = new CofyApiLink();
  element.i18n = await testI18n();
  element.url = url;
  document.body.append(element);
  await element.updateComplete;
  return element;
}

describe("cofy-api-link", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("links to the address, opening it in a new tab", async () => {
    const link = (await mount("https://cofy.example/communities/demo/")).shadowRoot!.querySelector("a");

    expect(link?.textContent).toBe("https://cofy.example/communities/demo/");
    expect(link?.getAttribute("href")).toBe("https://cofy.example/communities/demo/");
    expect(link?.getAttribute("target")).toBe("_blank");
  });

  it("copies the address", async () => {
    const element = await mount("https://cofy.example/communities/demo/");

    expect(element.shadowRoot!.querySelector("wa-copy-button")?.getAttribute("value")).toBe(
      "https://cofy.example/communities/demo/",
    );
  });

  it("shows nothing without an address", async () => {
    const element = await mount("");

    expect(element.shadowRoot!.querySelector("a, wa-copy-button")).toBeNull();
  });
});
