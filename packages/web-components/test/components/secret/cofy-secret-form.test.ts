import { beforeEach, describe, expect, it } from "vitest";

import { CofySecretForm } from "../../../src/components/form/cofy-secret-form.js";
import type { CofySecretDialog } from "../../../src/components/secret/cofy-secret-dialog.js";
import { community, mountIn, settle, type } from "./secret-support.js";

function secret(name: string): { type: "secret"; name: string } {
  return { type: "secret", name };
}

async function mount(value: unknown, state = community()): Promise<CofySecretForm> {
  const element = new CofySecretForm();
  element.schema = { type: "object", properties: { type: { const: "secret" }, name: { type: "string" } }, "x-secret": true };
  element.root = element.schema;
  element.pointer = "/api_key";
  element.label = "Api Key";
  element.value = value;
  return mountIn(element, state);
}

function changes(element: CofySecretForm): unknown[] {
  const values: unknown[] = [];
  element.addEventListener("field-change", (event) => values.push((event as CustomEvent<{ value: unknown }>).detail.value));
  return values;
}

function newSecret(element: CofySecretForm): HTMLElement {
  return element.shadowRoot!.querySelector<HTMLElement>("cofy-field-shell wa-button")!;
}

function dialog(element: CofySecretForm): CofySecretDialog {
  return element.shadowRoot!.querySelector("cofy-secret-dialog")!;
}

describe("cofy-secret-form", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("offers the community's secrets by name, under the field's own label", async () => {
    const element = await mount(secret("entsoe_key"));

    const options = Array.from(element.shadowRoot!.querySelectorAll("wa-option"));
    expect(options.map((option) => option.getAttribute("value"))).toEqual(["entsoe_key", "acc"]);
    expect(options[0]!.textContent).toContain("ENTSO-E");
    expect(element.shadowRoot!.querySelector("cofy-field-shell")!.label).toBe("Api Key");
  });

  it("holds the secret picked", async () => {
    const element = await mount("");
    const values = changes(element);

    const picker = element.shadowRoot!.querySelector<HTMLElement & { value: string }>("wa-select")!;
    picker.value = "acc";
    picker.dispatchEvent(new Event("change", { bubbles: true }));

    expect(values).toEqual([secret("acc")]);
  });

  it("creates a new secret, then holds it", async () => {
    const state = community();
    const element = await mount("", state);
    const values = changes(element);

    newSecret(element).click();
    await settle(element);
    const opened = dialog(element);
    expect(opened.open).toBe(true);

    const [name, , value] = Array.from(opened.shadowRoot!.querySelectorAll("wa-input"));
    expect(opened.shadowRoot!.querySelector("wa-radio-group")).toBeNull(); // the value is always given
    type(name!, "nl_key");
    type(value!, "nl-secret");
    await opened.updateComplete;
    opened.shadowRoot!.querySelector<HTMLElement>('wa-button[variant="brand"]')!.click();
    await settle(element);

    expect(state.writes).toEqual([
      {
        method: "POST",
        path: "/management/communities/test/secrets",
        body: { name: "nl_key", description: null, value: "nl-secret" },
      },
    ]);
    expect(values).toEqual([secret("nl_key")]);
    expect(dialog(element).open).toBe(false);
  });

  it("puts creating a secret beside the picker", async () => {
    const element = await mount(secret("entsoe_key"));

    const row = element.shadowRoot!.querySelector("cofy-field-shell > .picker")!;
    expect(row.querySelector("wa-select")).not.toBeNull();
    expect(row.querySelector("wa-button")!.textContent.trim()).toBe("New secret");
  });

  it("disables the picker, saying why, while there are no secrets yet", async () => {
    const state = community();
    state.secrets = [];
    const element = await mount("", state);

    const picker = element.shadowRoot!.querySelector("wa-select")!;
    expect(picker.hasAttribute("disabled")).toBe(true);
    expect(picker.getAttribute("placeholder")).toBe("No secrets are configured yet");
    expect(newSecret(element).hasAttribute("disabled")).toBe(false);
  });
});
