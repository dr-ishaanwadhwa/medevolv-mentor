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
    this.spans = this.sections.map((el) => Math.max(1, el.offsetHeight - stageR.height));
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
