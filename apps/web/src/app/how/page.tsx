import type { Metadata } from 'next';
import { LinkButton } from '@/components/ui';

export const metadata: Metadata = { title: 'How it works' };

const BOOKS = [
  ['KD Tripathi', 'Pharmacology'],
  ['Guyton & Hall', 'Physiology'],
  ['Robbins', 'Pathology'],
  ['Davidson', 'Medicine'],
  ['Harrison', 'Internal Medicine'],
  ['Microbiology', 'Textbook'],
  ["Gray's Anatomy", 'for Students'],
];

const PIPELINE = [
  ['Safety check', 'Requests for personal dosing or treatment are refused before anything is searched.'],
  ['Route', 'The question is classed as single, compound, or a long clinical case, and split into look-ups if needed.'],
  ['Search', 'Passages are retrieved from the seven textbooks only.'],
  ['Relevance filter', 'If the best match is too weak, the language model is never called and the answer is a decline.'],
  ['Write from evidence', 'The model is handed numbered passages and told to use nothing else, citing each claim as [n].'],
  ['Citation check', 'Each [n] is checked against the passages that were actually sent. Unsupported answers decline.'],
];

const EVALS = [
  ['39 / 39', 'questions got the right behaviour: answer, decline or refuse', 'Our 39-question product set, 13 Nov 2026'],
  ['30 / 30', 'answers carried at least one citation', 'Same run'],
  ['9 / 9', 'steps of the live demo script passed', 'Rehearsal on the live site, 14 Nov 2026'],
  ['90.8%', 'correct chapter within the top 3 search results', 'Tripathi, 446 questions'],
];

function Card({ n, title, children }: { n?: string; title: string; children: React.ReactNode }) {
  return (
    <section className="card space-y-2 p-5">
      {n && <div className="font-mono text-xs font-semibold text-accent">{n}</div>}
      <h2 className="text-lg font-semibold leading-snug">{title}</h2>
      <div className="space-y-2 text-[0.94rem] leading-relaxed text-muted">{children}</div>
    </section>
  );
}

export default function HowPage() {
  return (
    <div className="page space-y-5 py-6 sm:py-10">
      <header className="pb-2">
        <div className="label-mono !text-accent">How it works</div>
        <h1 className="mt-1.5 text-[1.9rem] font-bold leading-tight tracking-tight sm:text-4xl">
          The trust layer is the product.
        </h1>
        <p className="mt-3 max-w-[60ch] text-muted">
          MedEvolv Mentor is a study companion for MBBS students. It answers from standard textbooks, shows exactly where each
          claim comes from, and says so when the books do not cover a question.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card n="01" title="Cite or decline">
          <p>
            Every claim carries a numbered citation: book, edition, chapter and page. If the sources do not support an answer,
            the app declines instead of guessing, and &ldquo;the books don&apos;t settle this&rdquo; is a designed state, not
            an error.
          </p>
        </Card>
        <Card n="02" title="Seven textbooks, nothing else">
          <p>Answers are drawn only from these books. There is no web search and no general model memory presented as fact.</p>
          <ul className="flex flex-wrap gap-1.5 pt-1">
            {BOOKS.map(([a, b]) => (
              <li key={a} className="rounded-full bg-accent-soft px-2.5 py-1 font-mono text-[0.72rem] text-accent">
                {a} · {b}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card n="03" title="The verification layer">
        <ol className="grid gap-x-6 gap-y-3 pt-1 sm:grid-cols-2">
          {PIPELINE.map(([t, d], i) => (
            <li key={t} className="flex gap-3">
              <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-accent-soft font-mono text-xs font-semibold text-accent">
                {i + 1}
              </span>
              <span>
                <span className="block font-medium text-ink">{t}</span>
                {d}
              </span>
            </li>
          ))}
        </ol>
        <p className="pt-2">Every answer has a &ldquo;How this answer was made&rdquo; panel that shows these steps for that question.</p>
      </Card>

      <Card n="04" title="Measured, and where it stops">
        <div className="grid gap-3 pt-1 sm:grid-cols-2">
          {EVALS.map(([big, what, where]) => (
            <div key={what} className="rounded-xl border border-border bg-bg p-3.5">
              <div className="text-2xl font-bold tracking-tight text-ink">{big}</div>
              <div className="mt-0.5 text-sm text-ink">{what}</div>
              <div className="mt-1 font-mono text-[0.7rem] text-muted">{where}</div>
            </div>
          ))}
        </div>
        <p className="pt-2">
          These are results on our own question sets, not a clinical-safety guarantee. Retrieval metrics are not yet measured
          for every book. This is a study aid, not medical advice, and not a substitute for your teachers.
        </p>
      </Card>

      <Card n="05" title="3D links are navigation only">
        <p>
          Anatomy answers can link to the 3D atlas. Those links only locate the structure; they are tagged &ldquo;navigation
          only&rdquo; and are never a clinical claim.
        </p>
      </Card>

      <div className="flex flex-wrap gap-3 pt-2">
        <LinkButton href="/" variant="primary" size="lg">
          Ask a question
        </LinkButton>
        <LinkButton href="/why" size="lg">
          Why was I wrong?
        </LinkButton>
      </div>
    </div>
  );
}
