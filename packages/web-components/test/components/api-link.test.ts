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

  it("shows the address, and copies it", async () => {
    const element = await mount("https://cofy.example/communities/demo/");

    expect(element.shadowRoot!.querySelector("code")?.textContent).toBe("https://cofy.example/communities/demo/");
    expect(element.shadowRoot!.querySelector("wa-copy-button")?.getAttribute("value")).toBe(
      "https://cofy.example/communities/demo/",
    );
  });

  it("opens the documentation in a new tab", async () => {
    const open = (await mount("https://cofy.example/communities/demo/")).shadowRoot!.querySelector("wa-button");

    expect(open?.getAttribute("href")).toBe("https://cofy.example/communities/demo/docs");
    expect(open?.getAttribute("target")).toBe("_blank");
    expect(open?.querySelector("wa-icon")?.getAttribute("label")).toBe("Documentation");
  });

  it("shows nothing without an address", async () => {
    const element = await mount("");

    expect(element.shadowRoot!.querySelector("code, wa-copy-button, wa-button")).toBeNull();
  });
});
