import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CofyGrantDialog } from "../../../src/components/grant/cofy-grant-dialog.js";
import { CofyGrantList } from "../../../src/components/grant/cofy-grant-list.js";
import { community, mountIn, settle } from "./grant-support.js";

async function mount(state = community()): Promise<CofyGrantList> {
  const element = new CofyGrantList();
  element.slug = "test";
  return mountIn(element, state);
}

function row(element: CofyGrantList, email: string): HTMLElement | null {
  return element.shadowRoot!.querySelector<HTMLElement>(`tr[data-key="${email}"]`);
}

function dialog(element: CofyGrantList): CofyGrantDialog {
  return element.shadowRoot!.querySelector("cofy-grant-dialog")!;
}

describe("cofy-grant-list", () => {
  beforeEach(() => {
    document.body.replaceChildren();
    vi.restoreAllMocks();
  });

  it("lists each grant with its role and whether its person has linked their account", async () => {
    const element = await mount();

    expect(row(element, "ann@example.com")!.textContent).toContain("Account linked");
    expect(row(element, "bob@example.com")!.textContent).toContain("Awaiting first login");
    expect(row(element, "bob@example.com")!.textContent).toContain("Community admin");
  });

  it("grants access through its dialog", async () => {
    const state = community();
    const element = await mount(state);

    element.shadowRoot!.querySelector<HTMLElement>('cofy-heading wa-button[variant="brand"]')!.click();
    await settle(element);
    expect(dialog(element).open).toBe(true);

    const email = dialog(element).shadowRoot!.querySelector("wa-input")! as HTMLElement & { value: string };
    email.value = "cas@example.com";
    email.dispatchEvent(new Event("input"));
    await dialog(element).updateComplete;
    dialog(element).shadowRoot!.querySelector<HTMLElement>('wa-button[variant="brand"]')!.click();
    await settle(element);

    expect(state.writes).toEqual([
      {
        method: "POST",
        path: "/management/communities/test/grants",
        body: { email: "cas@example.com", role: "community_admin" },
      },
    ]);
    expect(dialog(element).open).toBe(false);
    expect(row(element, "cas@example.com")).not.toBeNull();
  });

  it("revokes a grant after asking", async () => {
    const state = community();
    const element = await mount(state);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    row(element, "bob@example.com")!.querySelector<HTMLElement>(".actions wa-button")!.click();
    await settle(element);

    expect(state.writes).toEqual([
      { method: "DELETE", path: "/management/communities/test/grants/bob@example.com", body: undefined },
    ]);
    expect(row(element, "bob@example.com")).toBeNull();
  });
});
