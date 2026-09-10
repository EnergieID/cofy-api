/**
 * Browser APIs jsdom does not implement, stubbed just enough for Carbon's components.
 *
 * Carbon observes element size for positioning; nothing these tests assert on depends on a
 * real measurement, so a stub that never reports is both sufficient and honest about what is
 * not being covered here.
 */
class NoopResizeObserver implements ResizeObserver {
  public observe(): void {}
  public unobserve(): void {}
  public disconnect(): void {}
}

globalThis.ResizeObserver ??= NoopResizeObserver;
