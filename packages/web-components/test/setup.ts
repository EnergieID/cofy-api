/**
 * Browser APIs jsdom does not implement, stubbed just enough for Web Awesome's components.
 *
 * A few tests run in the `node` environment rather than jsdom, and setup files run in both, so
 * everything is guarded on there being a DOM at all.
 *
 * Each stub was added because a component actually reached for the API and threw, not
 * pre-emptively. None of them simulate real behaviour: nothing these tests assert on depends on
 * a real measurement, animation or top layer, so a stub that does nothing is both sufficient
 * and honest about what is not covered. Anything that needs the real thing - focus trapping,
 * positioning, transitions - has to be checked in a browser.
 */

/** Define *name* on *target* only where the environment has not. */
function fallback(target: object, name: string, value: unknown): void {
  if (name in target) return;
  Object.defineProperty(target, name, { value, writable: true, configurable: true });
}

if (typeof globalThis.document !== "undefined") {
  /** Carbon needed this for positioning; Web Awesome's popup and drawer need it too. */
  class NoopResizeObserver implements ResizeObserver {
    public observe(): void {}
    public unobserve(): void {}
    public disconnect(): void {}
  }

  class NoopIntersectionObserver implements IntersectionObserver {
    public readonly root = null;
    public readonly rootMargin = "";
    public readonly thresholds: readonly number[] = [];
    public observe(): void {}
    public unobserve(): void {}
    public disconnect(): void {}
    public takeRecords(): IntersectionObserverEntry[] {
      return [];
    }
  }

  globalThis.ResizeObserver ??= NoopResizeObserver;
  globalThis.IntersectionObserver ??= NoopIntersectionObserver;

  // Several Web Awesome components scroll a newly opened item into view; jsdom has no layout,
  // so there is nothing to scroll, but it still needs to exist.
  fallback(Element.prototype, "scrollIntoView", () => {});

  // Every Web Awesome component is form-associated and calls `setValidity` from `firstUpdated`
  // - `wa-button` included. jsdom implements `attachInternals()` but not the validity half of
  // what it returns, so without these the first render of any component rejects. `validity`
  // reports valid unconditionally, which is consistent with `setValidity` doing nothing: these
  // tests are about rendering and behaviour, not constraint validation.
  const internals: object | undefined = globalThis.ElementInternals?.prototype;
  if (internals !== undefined) {
    fallback(internals, "setValidity", () => {});
    fallback(internals, "setFormValue", () => {});
    fallback(internals, "checkValidity", () => true);
    fallback(internals, "reportValidity", () => true);
    fallback(internals, "validity", { valid: true });
  }

  // The Web Animations API, which `wa-drawer` and `wa-dialog` open and close through. A
  // resolved `finished` lets code awaiting the animation continue instead of hanging.
  fallback(Element.prototype, "animate", (): Animation => {
    const noop = (): void => {};
    return {
      finished: Promise.resolve(),
      cancel: noop,
      finish: noop,
      play: noop,
      pause: noop,
      addEventListener: noop,
      removeEventListener: noop,
    } as unknown as Animation;
  });

  // The top layer - the popover API and `<dialog>` - which is how the drawer opens.
  fallback(HTMLElement.prototype, "showPopover", () => {});
  fallback(HTMLElement.prototype, "hidePopover", () => {});
  fallback(HTMLDialogElement.prototype, "showModal", function (this: HTMLDialogElement): void {
    this.open = true;
  });
  fallback(HTMLDialogElement.prototype, "close", function (this: HTMLDialogElement): void {
    this.open = false;
  });
}
