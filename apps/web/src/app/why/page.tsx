import type { Metadata } from 'next';
import { WhyView } from '@/components/why/WhyView';

export const metadata: Metadata = { title: 'Why was I wrong?' };

export default function WhyPage() {
  return <WhyView />;
}
