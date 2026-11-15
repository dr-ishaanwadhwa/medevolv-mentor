'use client';

import { Button } from '@/components/ui';

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="page grid min-h-[60dvh] place-content-center justify-items-start gap-3 py-16" role="alert">
      <div className="label-mono !text-bad">Something broke</div>
      <h1 className="text-3xl font-bold tracking-tight">This page hit an error.</h1>
      <p className="max-w-[50ch] text-muted">Nothing was answered or saved. Try again, and if it keeps happening, reload the page.</p>
      <Button variant="primary" onClick={reset} tip="shell.error.retry">
        Try again
      </Button>
    </div>
  );
}
