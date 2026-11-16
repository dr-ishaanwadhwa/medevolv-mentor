import type { Metadata } from 'next';
import Link from 'next/link';
import { Tooltip } from '@/components/ui';
import { BulletList, ExtLink, LegalPage, LegalSection } from '@/components/credits/LegalPage';

export const metadata: Metadata = { title: 'Terms' };

export default function TermsPage() {
  return (
    <LegalPage
      eyebrow="Terms"
      title="Terms of use"
      lead="MedEvolv Mentor is a pilot study aid for enrolled MBBS students. By using it you accept these terms. Last updated 15 November 2026."
    >
      <LegalSection id="study-aid" title="A study aid, not medical advice">
        <BulletList>
          <li>
            Mentor helps you study from the indexed textbooks. It is not medical advice, and it must not be used to
            decide anything about a real patient, a diagnosis or a treatment.
          </li>
          <li>
            Answers cite the book, chapter and page, or decline. Check the cited passage before you rely on an answer.
            Mistakes are possible, including in diagrams and in the 3D models.
          </li>
          <li>
            Textbook content stays with its publishers. Mentor shows short excerpts to support an answer and does not
            replace the books.
          </li>
        </BulletList>
      </LegalSection>

      <LegalSection id="use" title="Using the service">
        <BulletList>
          <li>The pilot is for enrolled MBBS students. Use it for your own study.</li>
          <li>Do not enter details that identify a real patient.</li>
          <li>
            Do not try to overload the service or to get around its limits. We may rate limit or block use that does.
          </li>
          <li>
            The service is a pilot. It may change, be unavailable or be withdrawn, and it is provided as it is, without
            promises of availability or accuracy.
          </li>
        </BulletList>
      </LegalSection>

      <LegalSection id="shared" title="Sharing">
        <p>
          A shared answer is readable by anyone with its link. Share only what you are happy for others to read. See the{' '}
          <Tooltip tip="shell.legal.privacy">
            <Link href="/privacy" className="text-accent underline underline-offset-2">
              Privacy
            </Link>
          </Tooltip>{' '}
          page.
        </p>
      </LegalSection>

      <LegalSection id="videos" title="Video suggestions (YouTube)">
        <p>
          Suggested videos from YouTube. These are not from your textbooks, are not checked by MedEvolv, and may differ
          from the cited answer. Always trust the cited textbook passages first.
        </p>
        <p>
          Video suggestions use YouTube API Services. By using the video suggestions you agree to be bound by the{' '}
          <ExtLink href="https://www.youtube.com/t/terms">YouTube Terms of Service</ExtLink>. Google&rsquo;s{' '}
          <ExtLink href="https://policies.google.com/privacy">Privacy Policy</ExtLink> describes how Google handles
          data.
        </p>
      </LegalSection>

      <LegalSection id="models" title="3D models">
        <p>
          The 3D models are open datasets used under their own licences, listed with their changes on the{' '}
          <Tooltip tip="shell.legal.credits">
            <Link href="/credits" className="text-accent underline underline-offset-2">
              Credits
            </Link>
          </Tooltip>{' '}
          page. They are reference anatomy, and real anatomy varies.
        </p>
      </LegalSection>

      <LegalSection id="contact" title="Questions and complaints">
        <p>
          We have not yet published a contact email. For now, use the Feedback button under any answer to ask a question,
          report a problem or make a complaint. We will add a direct contact here when there is one.
        </p>
      </LegalSection>
    </LegalPage>
  );
}
