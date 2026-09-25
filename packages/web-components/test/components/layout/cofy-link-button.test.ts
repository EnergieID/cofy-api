import { beforeEach, describe, expect, it } from "vitest";

import "../../../src/components/layout/cofy-link-button.js";
import type { CofyLinkButton } from "../../../src/components/layout/cofy-link-button.js";

async function mountLinkButton(): Promise<CofyLinkButton> {
  const element = document.createElement("cofy-link-button");
  element.textContent = "Remove";
  document.body.append(element);
  await element.updateComplete;
  return element;
}

/** The real, native `<button>` a step further in: `<wa-button>` renders it inside its own
 * shadow root, one level below `cofy-link-button`'s. */
function innerButton(element: CofyLinkButton): HTMLButtonElement {
  const waButton = element.shadowRoot!.querySelector("wa-button")!;
  return waButton.shadowRoot!.querySelector("button")!;
}

describe("cofy-link-button", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("renders its slotted content inside a real, native button", async () => {
    const element = await mountLinkButton();

    expect(element.textContent?.trim()).toBe("Remove");
    // A real <button> - focus, keyboard activation, and disabled handling are the platform's,
    // not reimplemented here the way a hand-rolled `<a role="button">` would have to.
    expect(innerButton(element).tagName).toBe("BUTTON");
  });

  it("fires click on click, and stops the original from propagating further", async () => {
    const element = await mountLinkButton();
    const wrapper = document.createElement("div");
    document.body.append(wrapper);
    wrapper.append(element);

    let outerClicks = 0;
    wrapper.addEventListener("click", () => outerClicks++);
    let clicks = 0;
    element.addEventListener("click", () => clicks++);

    innerButton(element).dispatchEvent(new MouseEvent("click", { bubbles: true, composed: true }));

    expect(clicks).toBe(1);
    expect(outerClicks).toBe(0);
  });

  it("reacts to whatever produces a click on the real button - mouse or the browser's own Enter/Space translation", async () => {
    // jsdom does not simulate a real browser's own "Enter/Space activates a focused button"
    // behaviour, so this drives it the way that behaviour actually manifests - a `click` on the
    // button - rather than dispatching a keydown jsdom would not translate into one anyway.
    const element = await mountLinkButton();
    let clicks = 0;
    element.addEventListener("click", () => clicks++);

    innerButton(element).click();

    expect(clicks).toBe(1);
  });

  it("does not let a nested cofy-link-button's click reach an ancestor's own listener", async () => {
    // The same shape a previous bug had with wa-expand bubbling through nested accordions -
    // this proves the fix (the re-dispatched event does not bubble at all) actually holds.
    const outer = await mountLinkButton();
    const inner = document.createElement("cofy-link-button");
    inner.textContent = "Inner";
    outer.append(inner);
    await inner.updateComplete;

    let outerClicks = 0;
    outer.addEventListener("click", () => outerClicks++);
    let innerClicks = 0;
    inner.addEventListener("click", () => innerClicks++);

    innerButton(inner).dispatchEvent(new MouseEvent("click", { bubbles: true, composed: true }));

    expect(innerClicks).toBe(1);
    expect(outerClicks).toBe(0);
  });
});
