import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CofyStore } from "@cofy/frontend-sdk";

import type { CofyTokenDialog } from "../../../src/components/token/cofy-token-dialog.js";
import { CofyTokenList } from "../../../src/components/token/cofy-token-list.js";
import { community, KEY, mountIn, settle, type } from "./token-support.js";

async function mount(state = community()): Promise<{ element: CofyTokenList; cofy: CofyStore }> {
  const element = new CofyTokenList();
  element.slug = "test";
  return mountIn(element, state);
}

function row(element: CofyTokenList, name: string): HTMLElement {
  return element.shadowRoot!.querySelector<HTMLElement>(`tr[data-key="${name}"]`)!;
}

function dialog(element: CofyTokenList): CofyTokenDialog {
  return element.shadowRoot!.querySelector("cofy-token-dialog")!;
}

function inputs(element: CofyTokenList): Element[] {
  return Array.from(dialog(element).shadowRoot!.querySelectorAll("wa-input"));
}

async function pressBrand(element: CofyTokenList): Promise<void> {
  dialog(element).shadowRoot!.querySelector<HTMLElement>('wa-button[variant="brand"]')!.click();
  await settle(element);
}

describe("cofy-token-list", () => {
  beforeEach(() => {
    document.body.replaceChildren();
    vi.restoreAllMocks();
  });

  it("lists each token with its description and expiry, marking an expired one", async () => {
    const { element } = await mount();

    expect(row(element, "app").textContent).toContain("Our app");
    expect(row(element, "app").textContent).toContain("Never");
    expect(row(element, "app").querySelector("wa-badge")).toBeNull();
    expect(row(element, "old").querySelector("wa-format-date")?.getAttribute("date")).toBe("2000-01-01T00:00:00Z");
    expect(row(element, "old").querySelector("wa-badge")?.textContent).toContain("Expired");
  });

  it("creates a token and shows its key once, without it reaching the list", async () => {
    const state = community();
    const { element, cofy } = await mount(state);

    element.shadowRoot!.querySelector<HTMLElement>('cofy-heading wa-button[variant="brand"]')!.click();
    await settle(element);
    const [name, description, expires] = inputs(element);
    type(name!, "meter");
    type(description!, "The meter reader");
    type(expires!, "2030-06-01");
    await dialog(element).updateComplete;
    await pressBrand(element);

    expect(state.writes).toEqual([
      {
        method: "POST",
        path: "/management/communities/test/tokens",
        body: { name: "meter", description: "The meter reader", expires: "2030-06-01T00:00:00Z" },
      },
    ]);
    expect(dialog(element).open).toBe(true);
    const copy = dialog(element).shadowRoot!.querySelector("wa-copy-button")!;
    expect(copy.getAttribute("value")).toBe(KEY);
    expect(row(element, "meter")).not.toBeNull();
    expect(JSON.stringify(cofy.tokens.all("test"))).not.toContain(KEY);

    await pressBrand(element);
    expect(dialog(element).open).toBe(false);

    element.shadowRoot!.querySelector<HTMLElement>('cofy-heading wa-button[variant="brand"]')!.click();
    await settle(element);
    expect(dialog(element).shadowRoot!.querySelector("wa-copy-button")).toBeNull();
  });

  it("changes a token's description and expiry, never sending a key", async () => {
    const state = community();
    const { element } = await mount(state);

    row(element, "old").click();
    await settle(element);
    expect(dialog(element).token?.name).toBe("old");
    const [description, expires] = inputs(element);
    expect((expires as HTMLElement & { value: string }).value).toBe("2000-01-01");
    type(description!, "Renewed");
    type(expires!, "");
    await dialog(element).updateComplete;
    await pressBrand(element);

    expect(state.writes).toEqual([
      {
        method: "PUT",
        path: "/management/communities/test/tokens/old",
        body: { name: "old", description: "Renewed", expires: null },
      },
    ]);
    expect(dialog(element).open).toBe(false);
  });

  it("does not open a token when the click was on its delete button", async () => {
    const { element } = await mount();
    vi.spyOn(window, "confirm").mockReturnValue(false);

    row(element, "app").querySelector<HTMLElement>(".actions wa-button")!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await settle(element);

    expect(dialog(element).open).toBe(false);
  });

  it("deletes a token after asking", async () => {
    const state = community();
    const { element } = await mount(state);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);

    row(element, "app").querySelector<HTMLElement>(".actions wa-button")!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await settle(element);

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("app"));
    expect(state.writes).toEqual([{ method: "DELETE", path: "/management/communities/test/tokens/app", body: undefined }]);
    expect(row(element, "app")).toBeNull();
  });
});
