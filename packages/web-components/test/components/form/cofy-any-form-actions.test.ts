import { beforeEach, describe, expect, it } from "vitest";
import type { JsonSchema } from "@cofy/frontend-sdk";

import type { MenuAction } from "../../../src/components/form/cofy-action-menu.js";
import { CofyAnyForm } from "../../../src/components/form/cofy-any-form.js";
import { testI18n } from "../../support/i18n.js";

/** An object field, which offers viewing it as YAML. */
const schema: JsonSchema = { type: "object", title: "Source", properties: { type: { type: "string" } } };

async function mount(menuActions: readonly MenuAction[]): Promise<CofyAnyForm> {
  const element = new CofyAnyForm();
  element.i18n = await testI18n();
  element.schema = schema;
  element.root = schema;
  element.pointer = "/source";
  element.value = { type: "x" };
  element.menuActions = menuActions;
  document.body.append(element);
  await element.updateComplete;
  return element;
}

describe("cofy-any-form actions", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("offers viewing a field as YAML through a link when that is all it offers", async () => {
    const element = await mount([]);

    expect(element.shadowRoot!.querySelector("cofy-link-button")?.textContent?.trim()).toBe("View as YAML");
    expect(element.shadowRoot!.querySelector("cofy-action-menu")).toBeNull();
  });

  it("puts the YAML toggle in one menu with the actions it was given", async () => {
    const ran: string[] = [];
    const element = await mount([{ id: "use-resource", label: "Use a resource", run: (): number => ran.push("use") }]);

    const menu = element.shadowRoot!.querySelector("cofy-action-menu")!;
    expect(element.shadowRoot!.querySelector("cofy-link-button")).toBeNull();
    expect(menu.actions.map((action) => action.id)).toEqual(["toggle-yaml", "use-resource"]);

    menu.actions[1]!.run();
    expect(ran).toEqual(["use"]);
  });
});
