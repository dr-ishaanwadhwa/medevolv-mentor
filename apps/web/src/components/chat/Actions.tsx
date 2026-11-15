'use client';

import { useState } from 'react';
import { Check, Flag, Link2, Loader2, Send } from 'lucide-react';
import { Button, Chip } from '@/components/ui';
import { sendFeedback, type FeedbackKind } from '@/lib/api';
import { useUi } from '@/store/ui';
import { cn } from '@/lib/cn';

export function ShareButton({ shareId, onShare }: { shareId?: string; onShare: () => Promise<string> }) {
  const toast = useUi((s) => s.toast);
  const [busy, setBusy] = useState(false);
  const click = async () => {
    setBusy(true);
    try {
      const id = shareId ?? (await onShare());
      const link = `${window.location.origin}/a/${id}`;
      try {
        await navigator.clipboard.writeText(link);
        toast('Link copied');
      } catch {
        toast(link, 9000); // clipboard blocked: show the link so it can be copied by hand
      }
    } catch {
      toast('Could not create a share link');
    } finally {
      setBusy(false);
    }
  };
  return (
    <Chip onClick={click} disabled={busy} aria-label="Copy a share link">
      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Link2 className="h-4 w-4" />}
      Share
    </Chip>
  );
}

const KINDS: { v: FeedbackKind; label: string }[] = [
  { v: 'wrong_citation', label: 'Wrong citation' },
  { v: 'unhelpful', label: 'Unhelpful' },
  { v: 'other', label: 'Other' },
];

export function FeedbackButton({ question, answerId }: { question: string; answerId?: string }) {
  const toast = useUi((s) => s.toast);
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<FeedbackKind | null>(null);
  const [note, setNote] = useState('');
  const [state, setState] = useState<'idle' | 'sending' | 'sent'>('idle');

  const send = async () => {
    if (!kind) return;
    setState('sending');
    try {
      await sendFeedback({ question, answer_id: answerId, kind, note: note.trim() || undefined });
      setState('sent');
      toast('Thanks, that was recorded');
      setOpen(false);
    } catch {
      setState('idle');
      toast('Could not send feedback');
    }
  };

  if (state === 'sent')
    return (
      <span className="inline-flex min-h-[44px] items-center gap-1.5 px-2 text-sm text-muted md:min-h-[34px]">
        <Check className="h-4 w-4 text-good" /> Feedback sent
      </span>
    );
  return (
    <>
      <Chip onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <Flag className="h-4 w-4" /> Report a problem
      </Chip>
      {open && (
        <div className="basis-full animate-fade-up rounded-xl border border-border bg-surface2/50 p-3.5">
          <div className="mb-2.5 flex flex-wrap gap-2" role="radiogroup" aria-label="What went wrong">
            {KINDS.map((k) => (
              <button
                key={k.v}
                type="button"
                role="radio"
                aria-checked={kind === k.v}
                onClick={() => setKind(k.v)}
                className={cn(
                  'min-h-[44px] rounded-full border px-3.5 text-sm md:min-h-[34px]',
                  kind === k.v ? 'border-accent bg-accent-soft text-accent' : 'border-border bg-surface text-ink hover:bg-surface2',
                )}
              >
                {k.label}
              </button>
            ))}
          </div>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={1000}
            rows={2}
            placeholder="Optional note (which citation, what was missing)"
            aria-label="Optional note"
            className="w-full resize-none rounded-lg border border-border bg-surface px-3 py-2 text-base placeholder:text-muted/70 md:text-sm"
          />
          <div className="mt-2.5 flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" variant="primary" disabled={!kind || state === 'sending'} onClick={send}>
              <Send className="h-3.5 w-3.5" /> Send
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
