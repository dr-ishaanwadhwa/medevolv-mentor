'use client';

import dynamic from 'next/dynamic';
import { cn } from '@/lib/cn';
import type { AtlasCanvasProps } from './AtlasScene';

export type { AtlasCanvasProps, AtlasHit, AtlasResolved } from './AtlasScene';

function CanvasSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('relative h-full w-full', className)} role="status" aria-label="Loading 3D viewer">
      <div className="absolute inset-0 grid place-items-center">
        <div className="flex w-56 flex-col items-center gap-3 rounded-2xl border border-border bg-surface/90 px-5 py-4 shadow-card">
          <div className="skeleton h-1.5 w-full rounded-full" />
          <span className="label-mono">Starting 3D viewer</span>
        </div>
      </div>
    </div>
  );
}

// three.js is only fetched on routes that render this component.
const Scene = dynamic(() => import('./AtlasScene'), { ssr: false, loading: () => <CanvasSkeleton /> });

export default function AtlasCanvas(props: AtlasCanvasProps) {
  return <Scene {...props} />;
}
