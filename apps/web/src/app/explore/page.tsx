import { Suspense } from 'react';
import type { Metadata } from 'next';
import { ExploreView } from '@/components/explore/ExploreView';

export const metadata: Metadata = { title: 'Explore' };

export default function ExplorePage() {
  return (
    <Suspense fallback={<div className="page py-10" aria-busy />}>
      <ExploreView />
    </Suspense>
  );
}
