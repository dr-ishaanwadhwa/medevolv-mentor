'use client';

import { Plus, Sparkles, X } from 'lucide-react';
import { Button } from '@/components/ui';
import { LETTERS } from '@/lib/format';
import { cn } from '@/lib/cn';
import { useWhy } from '@/store/why';

export function WhyForm() {
  const { form, setForm, setOption, addOption, removeOption, prefill, submit } = useWhy();
  const valid = form.question.trim() && form.options.every((o) => o.trim()) && form.chosen >= 0;
  const missing = !form.question.trim()
    ? 'Add the question'
    : form.options.some((o) => !o.trim())
      ? 'Fill every option'
      : form.chosen < 0
        ? 'Mark the option you picked'
        : '';

  return (
    <form
      className="card space-y-5 p-4 sm:p-5"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <div>
        <div className="mb-1.5 flex items-center justify-between gap-2">
          <label htmlFor="why-q" className="label-mono">
            The question
          </label>
          <Button size="sm" variant="ghost" onClick={prefill} className="-mr-2">
            <Sparkles className="h-4 w-4" /> Try an example
          </Button>
        </div>
        <textarea
          id="why-q"
          value={form.question}
          onChange={(e) => setForm({ question: e.target.value })}
          rows={5}
          maxLength={3000}
          placeholder="Paste the question stem from your QBank or paper"
          className="w-full resize-y rounded-xl border border-border bg-bg px-3.5 py-3 text-base leading-snug placeholder:text-muted/70 focus:border-accent/60"
        />
      </div>

      <fieldset>
        <legend className="label-mono mb-1.5">Options, and the one you picked</legend>
        <div className="space-y-2" role="radiogroup" aria-label="The option you picked">
          {form.options.map((o, i) => {
            const picked = form.chosen === i;
            return (
              <div
                key={i}
                className={cn(
                  'flex items-center gap-1 rounded-xl border bg-bg pr-1 transition-colors',
                  picked ? 'border-accent bg-accent-soft/50' : 'border-border',
                )}
              >
                <label className="grid h-11 min-w-[44px] cursor-pointer place-items-center" title="I picked this">
                  <input
                    type="radio"
                    name="picked"
                    checked={picked}
                    onChange={() => setForm({ chosen: i })}
                    aria-label={`I picked option ${LETTERS[i]}`}
                    className="peer sr-only"
                  />
                  <span
                    className={cn(
                      'grid h-7 w-7 place-items-center rounded-full border font-mono text-xs font-semibold transition-colors peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent',
                      picked ? 'border-accent bg-accent text-accent-ink' : 'border-border bg-surface text-muted',
                    )}
                  >
                    {LETTERS[i]}
                  </span>
                </label>
                <input
                  value={o}
                  onChange={(e) => setOption(i, e.target.value)}
                  maxLength={300}
                  aria-label={`Option ${LETTERS[i]}`}
                  placeholder={`Option ${LETTERS[i]}`}
                  className="h-11 min-w-0 flex-1 bg-transparent px-1 text-base outline-none placeholder:text-muted/70"
                />
                {picked && <span className="hidden shrink-0 font-mono text-[0.68rem] uppercase tracking-wider text-accent sm:inline">I picked</span>}
                {form.options.length > 2 && (
                  <button
                    type="button"
                    onClick={() => removeOption(i)}
                    aria-label={`Remove option ${LETTERS[i]}`}
                    className="grid h-11 w-11 shrink-0 place-items-center rounded-lg text-muted hover:bg-surface2 hover:text-bad"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
        {form.options.length < 6 && (
          <Button size="sm" variant="ghost" onClick={addOption} className="mt-2 -ml-2">
            <Plus className="h-4 w-4" /> Add option
          </Button>
        )}
      </fieldset>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" variant="primary" size="lg" disabled={!valid}>
          Why was I wrong?
        </Button>
        {missing && <span className="text-sm text-muted">{missing}</span>}
      </div>
    </form>
  );
}
