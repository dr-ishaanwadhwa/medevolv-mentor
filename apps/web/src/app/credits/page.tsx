import type { Metadata } from 'next';
import Link from 'next/link';
import { Tooltip } from '@/components/ui';
import { ExtLink, LegalPage, LegalSection } from '@/components/credits/LegalPage';
import { MODELS, MODEL_ORDER } from '@/components/credits/models';

export const metadata: Metadata = { title: 'Credits' };

export default function CreditsPage() {
  return (
    <LegalPage
      eyebrow="Credits"
      title="3D models and data we build on"
      lead="The 3D atlas and every 3D view in Mentor use open anatomy models. Each is credited below with its source, licence and the changes we made."
    >
      {MODEL_ORDER.map((id) => {
        const m = MODELS[id];
        return (
          <section key={id} id={id} aria-labelledby={`${id}-h`} className="card space-y-4 p-5">
            <div>
              <h2 id={`${id}-h`} className="text-lg font-semibold">
                {m.title}
              </h2>
              <p className="mt-1 text-sm text-muted">
                {m.creators}. Licensed under{' '}
                <ExtLink href={m.licenseUrl}>{m.licenseName}</ExtLink>.
              </p>
            </div>
            <dl className="grid gap-x-6 gap-y-3 text-[0.93rem] sm:grid-cols-[8rem_1fr]">
              <dt className="label-mono pt-0.5">Version</dt>
              <dd>{m.version}</dd>
              <dt className="label-mono pt-0.5">Source</dt>
              <dd>
                <ExtLink href={m.sourceUrl}>{m.sourceLabel}</ExtLink>
                {m.extra && (
                  <>
                    {'; '}
                    <ExtLink href={m.extra.url}>{m.extra.label}</ExtLink>
                  </>
                )}
              </dd>
              <dt className="label-mono pt-0.5">Licence</dt>
              <dd>
                <ExtLink href={m.licenseUrl}>Creative Commons Attribution 4.0 International</ExtLink>
              </dd>
              <dt className="label-mono pt-0.5">Changes made</dt>
              <dd>{m.changes}</dd>
              <dt className="label-mono pt-0.5">Scope</dt>
              <dd>{m.note}</dd>
            </dl>
          </section>
        );
      })}

      <LegalSection title="About the female model">
        <p>
          The Female view in the 3D atlas shows the female study model: a male BodyParts3D body reshaped to a female
          form, with female organs from the Human Reference Atlas. It is for orientation only. It is credited on this
          page whether or not that view is switched on for you, and next to the 3D view whenever Female is active. The
          reshaping comes from human-atlas-enhanced, MIT licence, copyright (c) 2026 ashemag; see the app&apos;s
          third-party notices.
        </p>
      </LegalSection>

      <LegalSection title="Not a clinical tool">
        <p>
          These models are reference anatomy for study. Real anatomy varies, and nothing here is for decisions about a
          real patient. See the <Tooltip tip="shell.legal.terms"><Link href="/terms" className="text-accent underline underline-offset-2">Terms</Link></Tooltip>.
        </p>
      </LegalSection>
    </LegalPage>
  );
}
