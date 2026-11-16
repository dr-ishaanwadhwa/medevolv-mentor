import { Check, X } from 'lucide-react';
import { Chip, LinkButton, Tag } from '@/components/ui';
import { ModelCredit } from '@/components/credits/ModelCredit';
import type { Features } from '@/lib/features';
import { CHIASM_FMA, citeLabel, citedBookIndexes, declined, heroAnswer, journey, why, type Pointer } from './captures';
import { COPY, LANDING_MODE, MODE_COPY } from './copy';
import { BOOK_SHORT, BOOKS, EXAMPLES, FACTS, NOT_YET, askHref, coverage } from './facts';
import { ChiasmIllustration, FlowIllustration, LibraryIllustration } from './Illustrations';
import { LandingStage } from './LandingStage';

/** Replace "[2][4]" markers with small superscripts a screen reader reads as "source 2, source 4". The spoken words
 * are real (visually hidden) text: aria-label on a role-less <sup> is ignored by VoiceOver and NVDA. */
function Marked({ text }: { text: string }) {
  const parts = text.split(/(\[\d+\])/g).filter((p) => p !== '');
  return (
    <>
      {parts.map((p, i) => {
        const m = /^\[(\d+)\]$/.exec(p);
        const afterMarker = i > 0 && /^\[\d+\]$/.test(parts[i - 1]);
        return m ? (
          <sup key={i} className="ml-0.5 font-mono text-[0.68em] text-accent">
            <span className="sr-only">{afterMarker ? ', source ' : ' source '}</span>
            {m[1]}
          </sup>
        ) : (
          <span key={i}>{p}</span>
        );
      })}
    </>
  );
}

function Pointers({ cites }: { cites: Pointer[] }) {
  return (
    <ul className="mt-3 flex flex-wrap gap-2" aria-label="Sources">
      {cites.map((c) => (
        <li key={c.index} className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface2 px-3 py-1 font-mono text-[0.72rem] text-ink">
          <span className="text-accent">{c.index}</span>
          {citeLabel(c)}
        </li>
      ))}
    </ul>
  );
}

const panel = 'rounded-card border border-border bg-surface/90 p-5 shadow-card backdrop-blur-md sm:p-6';
const h2 = 'mt-2 text-2xl font-bold tracking-tight sm:text-3xl';
const sceneCls = 'flex min-h-[100svh] items-center py-16 md:py-20';
const wrap = 'mx-auto w-full max-w-6xl px-4 sm:px-6';

function Hero() {
  const hero = heroAnswer(journey.answer, journey.citations);
  return (
    <section id="landing-hero" data-scene="0" aria-labelledby="landing-h1" className={sceneCls}>
      <div className={wrap}>
        <div className="max-w-xl space-y-5">
          <div className={panel}>
            {MODE_COPY.label && <Tag className="mb-3">{MODE_COPY.label}</Tag>}
            <h1 id="landing-h1" className="text-[1.9rem] font-bold leading-[1.1] tracking-tight sm:text-4xl">{MODE_COPY.headline}</h1>
            <p className="mt-3 text-[1.02rem] leading-relaxed text-muted">{MODE_COPY.sub}</p>

            <div className="mt-5 rounded-xl border border-border bg-bg/70 p-4" role="group" aria-label="A real answer">
              <p className="label-mono !text-accent">{COPY.heroKicker}</p>
              <p className="mt-2 text-sm font-medium text-ink">{journey.question}</p>
              <p className="mt-2 text-[0.95rem] leading-relaxed text-ink">
                {hero.sentences.map((s, i) => (
                  <span key={i}>{i > 0 && ' '}<Marked text={s} /></span>
                ))}
              </p>
              <Pointers cites={hero.used} />
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <LinkButton href="/ask" variant="primary" size="lg" data-landing-cta="hero" tip="landing.cta">{MODE_COPY.cta}</LinkButton>
              <LinkButton href="/how" size="lg" tip="landing.how">{COPY.howLink}</LinkButton>
            </div>

            <div className="mt-5">
              <p className="label-mono">Try one</p>
              <ul className="mt-2 flex flex-wrap gap-2">
                {EXAMPLES.map((e) => (
                  <li key={e.id}>
                    {/* the whole question is visible (it wraps): a truncated chip hides what the student is about to send */}
                    <Chip
                      href={askHref(e.q)}
                      data-landing-cta={`example-${e.id}`}
                      tip="landing.example"
                      className="items-start whitespace-normal rounded-2xl py-2 text-left"
                    >
                      <span className="shrink-0 whitespace-nowrap pt-0.5 font-mono text-[0.68rem] uppercase tracking-wider text-accent">{e.year}</span>
                      <span>{e.q}</span>
                    </Chip>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className={panel} role="group" aria-labelledby="landing-coverage">
            <p id="landing-coverage" className="label-mono">What is in the library</p>
            <p className="mt-2 text-sm leading-relaxed text-ink">
              <strong>Covers:</strong>{' '}
              {coverage().map((g, i) => (
                <span key={g.subject}>
                  {i > 0 && '; '}
                  {g.subject} ({g.books.map((b) => `${b.name}${b.edition ? ` ${b.edition}` : ''}`).join(', ')})
                </span>
              ))}
              .
            </p>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              <strong className="text-ink">Not yet:</strong> {NOT_YET.join(', ')}.
            </p>
            <LibraryIllustration className="only-static mx-auto mt-4 w-full max-w-sm" />
            <p className="mt-3 font-mono text-[0.72rem] text-muted">
              {FACTS.passages.value} {FACTS.passages.text}. {FACTS.passages.caveats[0]}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function WhyScene() {
  const v = why.verdict;
  const wrongBecause = v.chosen_wrong_because;
  const used = new Set([...wrongBecause.matchAll(/\[(\d+)\]/g)].map((m) => Number(m[1])));
  const cites = v.citations.filter((c) => used.has(c.index));
  return (
    <section id="landing-why" data-scene="1" aria-labelledby="landing-why-h" className={sceneCls}>
      <div className={wrap}>
        <div className="max-w-xl">
          <div className={panel}>
            <p className="label-mono !text-accent">{COPY.why.kicker}</p>
            <h2 id="landing-why-h" className={h2}>{COPY.why.title}</h2>
            <p className="mt-2 text-muted">{COPY.why.body}</p>

            <div className="mt-4 rounded-xl border border-border bg-bg/70 p-4">
              <p className="text-sm font-medium">{why.question}</p>
              <ol className="mt-3 space-y-2" type="A">
                {why.options.map((o, i) => {
                  const picked = i === why.chosen;
                  const right = i === v.correct_option;
                  return (
                    <li
                      key={o}
                      className={
                        'flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm ' +
                        (right ? 'border-good bg-good-soft text-ink' : picked ? 'border-bad bg-bad-soft text-ink' : 'border-border bg-surface')
                      }
                    >
                      <span><span className="mr-2 font-mono text-xs text-muted">{String.fromCharCode(65 + i)}</span>{o}</span>
                      {right && <span className="inline-flex items-center gap-1 text-xs font-medium text-good"><Check className="h-3.5 w-3.5" aria-hidden />Correct</span>}
                      {picked && !right && <span className="inline-flex items-center gap-1 text-xs font-medium text-bad"><X className="h-3.5 w-3.5" aria-hidden />Your pick</span>}
                    </li>
                  );
                })}
              </ol>
              <p className="mt-3 text-sm leading-relaxed"><Marked text={wrongBecause} /></p>
              <Pointers cites={cites} />
              <p className="label-mono mt-4">Three viva questions</p>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                {v.viva_questions.map((q) => <li key={q}>{q}</li>)}
              </ul>
            </div>
            <div className="mt-5">
              <LinkButton href="/why" variant="secondary" data-landing-cta="why" tip="landing.why">{COPY.why.cta}</LinkButton>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function DeclineScene() {
  return (
    <section id="landing-decline" data-scene="2" aria-labelledby="landing-decline-h" className={sceneCls}>
      <div className={wrap}>
        <div className="max-w-xl">
          <div className={panel}>
            <p className="label-mono !text-accent">{COPY.decline.kicker}</p>
            <h2 id="landing-decline-h" className={h2}>{COPY.decline.title}</h2>
            <p className="mt-2 text-muted">{COPY.decline.body}</p>
            <figure className="mt-4 rounded-xl border border-border bg-bg/70 p-4">
              <figcaption className="label-mono">{COPY.decline.caption(declined.captured_at)}</figcaption>
              <p className="mt-2 text-sm font-medium">{declined.question}</p>
              <p className="mt-3 text-lg font-semibold">{COPY.decline.card}</p>
              <p className="mt-1 text-sm text-muted">{declined.text}</p>
            </figure>
          </div>
        </div>
      </div>
    </section>
  );
}

function BodyScene() {
  const loc = journey.spatial.find((s) => s.fma_ids?.includes(CHIASM_FMA));
  return (
    <section id="landing-body" data-scene="3" aria-labelledby="landing-body-h" className={sceneCls}>
      <div className={wrap}>
        <div className="max-w-xl">
          <div className={panel}>
            <p className="label-mono !text-accent">{COPY.body.kicker}</p>
            <h2 id="landing-body-h" className={h2}>{COPY.body.title}</h2>
            <p className="mt-2 text-muted">{COPY.body.body}</p>
            <figure className="only-static mt-4">
              <ChiasmIllustration className="w-full max-w-sm" />
              <figcaption className="mt-1 text-xs text-muted">{COPY.body.staticCaption}</figcaption>
            </figure>
            {loc && (
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <LinkButton href={`/atlas?select=${CHIASM_FMA}`} variant="secondary" data-landing-cta="view3d" tip="landing.view3d">
                  {COPY.body.cta}: {loc.label}
                </LinkButton>
              </div>
            )}
            <ModelCredit model="bodyparts3d" className="mt-3" />
          </div>
        </div>
      </div>
    </section>
  );
}

function MoreScene({ features }: { features: Features }) {
  const live = features.diagram && features.videos;
  const f = FACTS.behaviour;
  return (
    <section id="landing-more" data-scene="4" aria-labelledby="landing-more-h" className={sceneCls}>
      <div className={wrap}>
        <div className="max-w-xl space-y-5">
          {live && (
            <div className={panel}>
              <p className="label-mono !text-accent">{COPY.more.kicker}</p>
              <h2 id="landing-more-h" className={h2}>{COPY.more.title}</h2>
              <FlowIllustration className="mt-4 w-full max-w-sm" />
              <div className="mt-4 rounded-xl border border-dashed border-border p-3">
                <p className="label-mono">{COPY.more.videoNote}</p>
                <div className="mt-2 grid grid-cols-2 gap-2" aria-hidden>
                  {[0, 1].map((i) => (
                    <div key={i} className="aspect-video rounded-lg bg-surface2" />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div className={panel}>
            {live ? (
              <p className="label-mono !text-accent">{COPY.measured.kicker}</p>
            ) : (
              <h2 id="landing-more-h" className="label-mono !text-accent">{COPY.measured.kicker}</h2>
            )}
            <p className="mt-3 text-[1.02rem] leading-relaxed">
              <strong className="font-mono text-2xl text-accent">{f.value}</strong>{' '}
              {f.text} ({f.date}).
            </p>
            <p className="mt-2 text-xs leading-relaxed text-muted">{f.sample}.</p>
            <p className="mt-3 text-xs leading-relaxed text-muted">{f.caveats[0]}</p>
            <p className="mt-1 text-xs leading-relaxed text-muted">{f.caveats[1]}</p>
            <p className="mt-5 text-ink">{COPY.measured.cta}</p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <LinkButton href="/ask" variant="primary" size="lg" data-landing-cta="final" tip="landing.cta">{MODE_COPY.cta}</LinkButton>
              <LinkButton href="/how" size="lg" tip="landing.how">{COPY.howLink}</LinkButton>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Landing({ features }: { features: Features }) {
  // which galaxies glow in the hero and in the Why scene: the books the captured answers really cited
  const heroBooks = citedBookIndexes(journey.citations);
  const whyBooks = citedBookIndexes(why.verdict.citations);
  return (
    <LandingStage mode={LANDING_MODE} bookLabels={BOOKS.map((b) => BOOK_SHORT[b.id] ?? b.id)} heroBooks={heroBooks} whyBooks={whyBooks} ctaLabel={MODE_COPY.cta}>
      <Hero />
      <WhyScene />
      <DeclineScene />
      <BodyScene />
      <MoreScene features={features} />
    </LandingStage>
  );
}
