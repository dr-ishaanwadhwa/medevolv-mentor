import { LinkButton } from '@/components/ui';

export default function NotFound() {
  return (
    <div className="page grid min-h-[60dvh] place-content-center justify-items-start gap-3 py-16">
      <div className="label-mono !text-accent">404</div>
      <h1 className="text-3xl font-bold tracking-tight">That page is not in the books.</h1>
      <p className="max-w-[50ch] text-muted">The link may be mistyped or the page may have moved.</p>
      <LinkButton href="/" variant="primary">
        Back to Ask
      </LinkButton>
    </div>
  );
}
