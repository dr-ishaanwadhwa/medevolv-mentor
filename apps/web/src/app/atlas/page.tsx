import { Suspense } from 'react';
import type { Metadata } from 'next';
import { AtlasView } from '@/components/canvas/AtlasView';

export const metadata: Metadata = { title: '3D Atlas' };

export default function AtlasPage() {
  return (
    <Suspense fallback={<div className="h-page" aria-busy />}>
      <AtlasView />
    </Suspense>
  );
}
