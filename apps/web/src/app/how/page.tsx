import type { Metadata } from 'next';
import HowClassic from './HowClassic';
import StoryEntry from '@/components/story/StoryEntry';

export const metadata: Metadata = { title: 'How it works' };

export default async function HowPage({ searchParams }: { searchParams: Promise<{ [k: string]: string | string[] | undefined }> }) {
  const sp = await searchParams;
  if (sp.classic) return <HowClassic />;
  return <StoryEntry />;
}
