import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CofySecretDialog } from "../../../src/components/secret/cofy-secret-dialog.js";
import { CofySecretList } from "../../../src/components/secret/cofy-secret-list.js";
import { community, mountIn, settle, type } from "./secret-support.js";

async function mount(state = community()): Promise<CofySecretList> {
  const element = new CofySecretList();
  element.slug = "test";
  return mountIn(element, state);
}

function row(element: CofySecretList, name: string): HTMLElement {
  return element.shadowRoot!.querySelector<HTMLElement>(`tr[data-key="${name}"]`)!;
}

function dialog(element: CofySecretList): CofySecretDialog {
  return element.shadowRoot!.querySelector("cofy-secret-dialog")!;
}

async function pressDelete(element: CofySecretList, name: string): Promise<void> {
  row(element, name).querySelector<HTMLElement>(".actions wa-button")!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  await settle(element);
}

describe("cofy-secret-list", () => {
  beforeEach(() => {
    document.body.replaceChildren();
    vi.restoreAllMocks();
  });

  it("lists each secret by name and description, never its value", async () => {
    const element = await mount();

    expect(row(element, "entsoe_key").textContent).toContain("ENTSO-E");
    expect(row(element, "acc")).not.toBeNull();
    expect(element.shadowRoot!.querySelectorAll("thead th")).toHaveLength(3);
  });

  it("opens a secret to give it a new value when its row is clicked, or chosen from the keyboard", async () => {
    const state = community();
    const element = await mount(state);

    row(element, "entsoe_key").click();
    await settle(element);
    expect(dialog(element).open).toBe(true);
    expect(dialog(element).secret?.name).toBe("entsoe_key");

    const [description, value] = Array.from(dialog(element).shadowRoot!.querySelectorAll("wa-input"));
    expect((description as HTMLElement & { value: string }).value).toBe("ENTSO-E");
    type(value!, "rotated");
    await dialog(element).updateComplete;
    dialog(element).shadowRoot!.querySelector<HTMLElement>('wa-button[variant="brand"]')!.click();
    await settle(element);

    expect(state.writes).toEqual([
      {
        method: "PUT",
        path: "/management/communities/test/secrets/entsoe_key",
        body: { name: "entsoe_key", description: "ENTSO-E", value: "rotated" },
      },
    ]);
    expect(dialog(element).open).toBe(false);

    row(element, "acc").dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    await settle(element);
    expect(dialog(element).secret?.name).toBe("acc");
  });

  it("does not open a secret when the click was on its delete button", async () => {
    const element = await mount();
    vi.spyOn(window, "confirm").mockReturnValue(false);

    await pressDelete(element, "acc");

    expect(dialog(element).open).toBe(false);
  });

  it("deletes a secret after asking", async () => {
    const state = community();
    const element = await mount(state);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    await pressDelete(element, "acc");

    expect(state.writes).toEqual([{ method: "DELETE", path: "/management/communities/test/secrets/acc", body: undefined }]);
    expect(element.shadowRoot!.querySelector('tr[data-key="acc"]')).toBeNull();
  });

  it("shows why the server refused to delete a secret still in use, keeping the list", async () => {
    const element = await mount();
    vi.spyOn(window, "confirm").mockReturnValue(true);

    await pressDelete(element, "entsoe_key");

    expect(element.shadowRoot!.querySelector("cofy-problem-details")!.problem!.message).toContain("tariff:spot");
    expect(row(element, "entsoe_key")).not.toBeNull();
  });
});
