import type { Metadata } from 'next';
import Link from 'next/link';
import { Tooltip } from '@/components/ui';
import { BulletList, ExtLink, LegalPage, LegalSection } from '@/components/credits/LegalPage';

export const metadata: Metadata = { title: 'Privacy' };

const GOOGLE_PRIVACY = 'https://policies.google.com/privacy';
const YOUTUBE_TERMS = 'https://www.youtube.com/t/terms';

export default function PrivacyPage() {
  return (
    <LegalPage
      eyebrow="Privacy"
      title="What Mentor stores and sends"
      lead="MedEvolv Mentor is a pilot study aid for enrolled MBBS students. There are no accounts and no sign-in. This page lists what we store or send, and why. Last updated 15 November 2026."
    >
      <LegalSection id="questions" title="Your questions">
        <BulletList>
          <li>
            When you ask a question, the question and the passages retrieved from the textbooks are sent to DeepSeek, a
            language model provider, to write the answer. DeepSeek is based in China. For flowcharts, the answer is
            also sent to DeepSeek to draw the diagram.
          </li>
          <li>
            Please do not type names or other details that identify a real patient. Mentor is for study questions.
          </li>
          <li>
            The question text is not saved by us unless you share an answer or send feedback (below).
          </li>
        </BulletList>
      </LegalSection>

      <LegalSection id="shared" title="Shared answers">
        <p>
          If you press Share, the question and answer are stored and given a link. Anyone who has the link can read
          them. Shared answers have no expiry today.
        </p>
      </LegalSection>

      <LegalSection id="feedback" title="Feedback">
        <p>
          If you send feedback on an answer, we store the question, the answer id, the kind of feedback you chose and
          any note you typed.
        </p>
      </LegalSection>

      <LegalSection id="counters" title="Anonymous event counters">
        <p>
          We count a few actions, such as whether a diagram was opened, as daily totals per action name. The counters
          hold no user id, no IP address, no question text, no topic and no video id, and they set no cookies.
        </p>
      </LegalSection>

      <LegalSection id="diagrams" title="Diagram cache">
        <p>
          To avoid redrawing the same flowchart, the server keeps a cache of diagrams. Each entry is keyed by a hash and
          holds only labels and pointers into the textbook data, not your question. Entries are kept for up to 90 days.
        </p>
      </LegalSection>

      <LegalSection id="logs" title="Server logs">
        <p>
          Our server and its web proxy keep ordinary access logs, which include your IP address and the pages and
          interfaces requested. The retention period for these logs has not been fixed yet. We will state it here once
          it is set.
        </p>
      </LegalSection>

      <LegalSection id="local" title="Cookies and data kept in your browser">
        <BulletList>
          <li>
            A first-party cookie named <code className="font-mono text-[0.85em]">mm_asked</code> may be set after your
            first answer, so a returning visit can go straight to Ask. It holds the value 1, has no id, is used for
            nothing else, and lasts one year.
          </li>
          <li>
            <code className="font-mono text-[0.85em]">localStorage</code> holds small preferences, such as your theme
            choice, and the 3D atlas Male or Female choice and dismissed tips where those features are on. They never
            leave your device.
          </li>
          <li>
            The 3D atlas caches model files in your browser&rsquo;s IndexedDB so it can open faster and work with a poor
            connection. You can clear it in your browser settings.
          </li>
        </BulletList>
        <p>We use no advertising or tracking cookies.</p>
      </LegalSection>

      <LegalSection id="youtube" title="Video suggestions and YouTube">
        <p>
          Where video suggestions are switched on, Mentor uses YouTube API Services. By using them you are also
          bound by the{' '}
          <ExtLink href={YOUTUBE_TERMS}>YouTube Terms of Service</ExtLink>, and Google&rsquo;s{' '}
          <ExtLink href={GOOGLE_PRIVACY}>Privacy Policy</ExtLink> applies to the data Google handles.
        </p>
        <BulletList>
          <li>
            The search is made by our server from a topic label such as the name of a condition, never from your
            question text, and your IP address is not sent to YouTube by the search.
          </li>
          <li>
            Thumbnails load from Google servers, so Google receives your IP address when they appear. Opening a video
            takes you to YouTube, which has its own policies.
          </li>
          <li>
            Video details from YouTube are cached on our server for up to 7 days and deleted within 14 days. We do not
            store them anywhere else.
          </li>
        </BulletList>
        <p>
          The{' '}
          <ExtLink href="https://myaccount.google.com/permissions">Google security settings page</ExtLink> lets you
          review and revoke access that apps have to your Google account data; Mentor does not ask you to sign in with
          Google.
        </p>
      </LegalSection>

      <LegalSection id="who" title="Who this is for">
        <p>
          The pilot is meant for enrolled MBBS students. It is not designed for children, and we do not knowingly
          collect data from them.
        </p>
      </LegalSection>

      <LegalSection id="contact" title="Questions, access and deletion requests">
        <p>
          We have not yet published a contact email. For now, use the Feedback button under any answer to ask what is
          stored about you, to ask for a shared answer or feedback entry to be deleted, or to raise a concern. Please
          include the link of the shared answer if it concerns one. We will add a direct contact here when there is one.
        </p>
      </LegalSection>

      <p className="text-sm text-muted">
        See also the{' '}
        <Tooltip tip="shell.legal.terms">
          <Link href="/terms" className="text-accent underline underline-offset-2">
            Terms
          </Link>
        </Tooltip>{' '}
        and{' '}
        <Tooltip tip="shell.legal.credits">
          <Link href="/credits" className="text-accent underline underline-offset-2">
            Credits
          </Link>
        </Tooltip>
        .
      </p>
    </LegalPage>
  );
}
