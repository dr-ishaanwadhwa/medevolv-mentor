'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { exploreStory, type StoryExploreResult } from '@/lib/api';
import { Button } from '@/components/ui';
import type { StoryBook } from './data';
import { bookNick } from './data';
import { bookColor } from './palette';

export const SUGGESTIONS = [
  'Mechanism of action of metformin',
  'Branches of the facial nerve',
  'Who won the 2011 cricket world cup?',
];
const MAX_LEN = 300;

/** "Try your own question" form (measured chapter). The result lives in the parent so the 3D scene can read it. */
export default function TryQuestion({ live, books, dark, result, onResult }: {
  /** true only while the measured chapter is the one on screen; leaving it cancels a pending request */
  live: boolean;
  books: StoryBook[];
  dark: boolean;
  result: StoryExploreResult | null;
  onResult: (r: StoryExploreResult | null) => void;
}) {
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle');
  const ac = useRef<AbortController | null>(null);

  useEffect(() => () => ac.current?.abort(), []);
  useEffect(() => {
    if (live) return;
    ac.current?.abort();
    setStatus('idle');
  }, [live]);

  const ask = async (text: string) => {
    const question = text.trim();
    if (!question || question.length > MAX_LEN) return;
    ac.current?.abort();
    const c = new AbortController();
    ac.current = c;
    setQ(question);
    onResult(null); // a new question replaces the old result
    setStatus('loading');
    try {
      const r = await exploreStory(question, c.signal);
      if (c.signal.aborted) return;
      setStatus('idle');
      onResult(r);
    } catch {
      if (c.signal.aborted) return;
      setStatus('error');
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    void ask(q);
  };

  const busy = status === 'loading';
  return (
    <div className="st-try" data-try>
      <form className="st-try-form" onSubmit={submit} role="search">
        <label htmlFor="st-try-input" className="st-try-h">Try your own question</label>
        <div className="st-try-row">
          <input
            id="st-try-input"
            className="st-try-input"
            type="text"
            value={q}
            maxLength={MAX_LEN}
            placeholder="e.g. What does the optic chiasm do?"
            autoComplete="off"
            onChange={(e) => setQ(e.target.value)}
            disabled={busy}
          />
          <Button type="submit" variant="primary" className="st-try-btn" disabled={busy || !q.trim()} aria-busy={busy || undefined}>
            {busy ? 'Searching…' : 'Search'}
          </Button>
        </div>
      </form>
      <div className="st-try-chips" aria-label="Example questions">
        {SUGGESTIONS.map((s) => (
          <button key={s} type="button" className="st-try-chip" disabled={busy} onClick={() => void ask(s)}>{s}</button>
        ))}
      </div>
      <div role="status" aria-live="polite" className={`st-try-status${status === 'error' ? ' st-try-status-err' : ''}`}>
        {status === 'loading' && 'Searching the textbooks…'}
        {status === 'error' && 'Couldn’t reach the library. Try again.'}
      </div>
      {result && <ExploreCard r={result} books={books} dark={dark} />}
    </div>
  );
}

function bookIndex(name: string, books: StoryBook[]): number {
  const t = books.findIndex((b) => b.title === name);
  if (t >= 0) return t;
  return books.findIndex((b) => b.id === name);
}

function ExploreCard({ r, books, dark }: { r: StoryExploreResult; books: StoryBook[]; dark: boolean }) {
  // per-book counts, keyed by the textbook display name the API returns
  const counts = new Map<string, number>();
  r.neighbours.forEach((n) => counts.set(n.book, (counts.get(n.book) ?? 0) + 1));
  const rows = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  const gauge = !r.refused && r.best !== null;
  return (
    <div className="st-try-card" data-try-card>
      <p>{r.narration}</p>
      {gauge && (
        <>
          <div className="st-gauge" aria-hidden="true">
            <i style={{ width: `${Math.min(1, Math.max(0, r.best ?? 0)) * 100}%` }} />
            <u style={{ left: `${r.min_similarity * 100}%` }} />
          </div>
          <div className="st-gauge-l"><span>best match {(r.best ?? 0).toFixed(2)} vs cut-off {r.min_similarity}</span></div>
        </>
      )}
      {rows.length > 0 && (
        <div className="st-try-books">
          {rows.map(([name, n]) => {
            const bi = bookIndex(name, books);
            const col = bookColor(bi >= 0 ? books[bi].id : name, Math.max(0, bi), dark);
            const label = bi >= 0 ? (bookNick[books[bi].id] ?? books[bi].title) : name;
            return (
              <span key={name} className="st-try-book"><i style={{ background: col }} />{label}<b>{n}</b></span>
            );
          })}
        </div>
      )}
      {!r.refused && (
        <p className={`st-try-verdict ${r.passes_floor ? 'st-try-verdict-ok' : 'st-try-verdict-no'}`}>
          {r.passes_floor
            ? 'These passages would be sent to the model as evidence'
            : 'Below the cut-off: the app would say it couldn’t find this'}
        </p>
      )}
    </div>
  );
}
