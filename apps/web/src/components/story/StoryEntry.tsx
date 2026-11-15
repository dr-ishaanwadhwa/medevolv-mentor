'use client';

import dynamic from 'next/dynamic';
import { Component, type ReactNode } from 'react';
import HowClassic from '@/app/how/HowClassic';

// three.js only ever loads here, on /how.
const Story = dynamic(() => import('./Story'), {
  ssr: false,
  loading: () => <div className="grid min-h-[60dvh] place-items-center font-mono text-xs text-muted">Loading the story…</div>,
});

class Boundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(e: unknown) { console.warn('[how] story failed, showing classic page', e); }
  render() { return this.state.failed ? <HowClassic /> : this.props.children; }
}

export default function StoryEntry() {
  return (
    <Boundary>
      <Story />
    </Boundary>
  );
}
