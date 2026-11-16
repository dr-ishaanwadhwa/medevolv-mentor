'use client';

import { CornerDownRight } from 'lucide-react';
import { Chip, Tag } from '@/components/ui';
import type { RelatedTopic } from '@/lib/api';
import { ANSWER_TIPS as T } from '@/lib/tips/answer';
import { relatedQuestion } from '@/lib/related';

/**
 * Up to 6 certified links of the answer's topic concept (PRD 4.2, V-9): our own textbook-derived data, so the row sits
 * inside the answer and does not depend on the videos flag, a YouTube key or quota. A tap asks the topic as a new turn
 * in this thread (`onAsk`); on a shared page, where there is no thread, it opens Ask with the question (`hrefFor`).
 */
export function RelatedTopics({
  related,
  onAsk,
  hrefFor,
  disabled,
}: {
  related: RelatedTopic[] | undefined;
  onAsk?: (question: string) => void;
  hrefFor?: (question: string) => string;
  disabled?: boolean;
}) {
  const items = (related ?? []).filter((r) => r.tier === 'certified').slice(0, 6);
  if (!items.length) return null;
  return (
    <div>
      <div className="label-mono mb-2 flex items-center gap-2">
        Related topics <Tag>from the textbooks</Tag>
      </div>
      <ul className="flex flex-wrap gap-2" aria-label="Related topics from the textbooks">
        {items.map((r) => {
          const q = relatedQuestion(r.label);
          return (
            <li key={r.id}>
              {hrefFor ? (
                <Chip href={hrefFor(q)} tip={T['answer.related']}>
                  <CornerDownRight className="h-4 w-4 text-accent" aria-hidden />
                  {r.label}
                </Chip>
              ) : (
                <Chip onClick={() => onAsk?.(q)} disabled={disabled} tip={T['answer.related']}>
                  <CornerDownRight className="h-4 w-4 text-accent" aria-hidden />
                  {r.label}
                </Chip>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
