import { beforeEach, describe, expect, it } from "vitest";

import { CofyHeading } from "../../src/components/layout/cofy-heading.js";
import { testI18n } from "../support/i18n.js";

async function mount(): Promise<CofyHeading> {
  const element = new CofyHeading();
  element.i18n = await testI18n();
  document.body.append(element);
  await element.updateComplete;
  return element;
}

describe("cofy-heading", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("renders the title as a real heading, not a styled-down one", async () => {
    const element = await mount();
    element.innerHTML = '<span slot="title">Modules</span>';
    await element.updateComplete;

    const heading = element.shadowRoot!.querySelector("h3")!;
    const slot = heading.querySelector<HTMLSlotElement>("slot")!;
    expect(slot.assignedNodes()[0]!.textContent).toBe("Modules");
  });

  it("puts the description in its own slot, read by the assigned element", async () => {
    const element = await mount();
    element.innerHTML = '<span slot="description">What this collects.</span>';
    await element.updateComplete;

    const slot = element.shadowRoot!.querySelector<HTMLSlotElement>('slot[name="description"]')!;
    expect(slot.assignedNodes()[0]!.textContent).toBe("What this collects.");
  });

  it("renders actions when given some", async () => {
    const element = await mount();
    element.innerHTML = '<button slot="actions">Add module</button>';
    await element.updateComplete;

    const slot = element.shadowRoot!.querySelector<HTMLSlotElement>('slot[name="actions"]')!;
    expect(slot.assignedNodes()).toHaveLength(1);
  });

  it("has nothing assigned to actions when a caller supplies none", async () => {
    const element = await mount();

    const slot = element.shadowRoot!.querySelector<HTMLSlotElement>('slot[name="actions"]')!;
    expect(slot.assignedNodes()).toHaveLength(0);
  });
});
