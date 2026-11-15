import { clamp } from './math';

/** Scroll engine: maps window scroll to a continuous story coordinate s = chapterIndex + progress(0..1). */
export class ScrollEngine {
  starts: number[] = [];
  spans: number[] = [];
  constructor(private sections: HTMLElement[], private stage: HTMLElement) {
    this.measure();
  }
  measure() {
    const stageR = this.stage.getBoundingClientRect();
    const top = stageR.top; // sticky offset (topbar height)
    const sy = window.scrollY;
    this.starts = this.sections.map((el) => el.getBoundingClientRect().top + sy - top);
    // A chapter runs until the next one starts (no dead tail where p is pinned at 1 and no panel shows);
    // only the last chapter ends a viewport early, where the sticky stage stops.
    const n = this.sections.length;
    this.spans = this.sections.map((el, i) =>
      Math.max(1, i < n - 1 ? this.starts[i + 1] - this.starts[i] : el.offsetHeight - stageR.height));
  }
  /** Raw (unsmoothed) story coordinate for the current scroll. */
  target(): number {
    const y = window.scrollY;
    let k = 0;
    for (let i = 0; i < this.starts.length; i++) if (this.starts[i] <= y + 0.5) k = i;
    const p = clamp((y - this.starts[k]) / this.spans[k]);
    return k + p;
  }
  scrollTo(k: number, p = 0.14, smooth = true) {
    const y = this.starts[k] + this.spans[k] * p;
    window.scrollTo({ top: y, behavior: smooth ? 'smooth' : 'auto' });
  }
}
