import type { Metadata } from 'next';
import { AskYourOwn, SharedAnswer } from '@/components/chat/SharedAnswer';

export const metadata: Metadata = {
  title: 'Shared answer',
  robots: { index: false, follow: false, nocache: true },
};

export default async function SharedPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="page py-6 sm:py-10">
      <div className="label-mono mb-4 !text-accent">Shared from MedEvolv Mentor</div>
      <SharedAnswer id={id} />
      <AskYourOwn />
      <p className="mt-4 text-xs text-muted">A study aid, not medical advice. Share cards carry textbook pointers only, no copied passages.</p>
    </div>
  );
}
