import { Landing } from '@/components/landing/Landing';
import { fetchFeatures } from '@/lib/features';

/** `/` is the landing (PRD 4.L, D-6). Ask lives at /ask; `/?q=` links are redirected there by next.config.mjs, and
 * returning askers by src/middleware.ts. robots noindex is inherited from the root layout (L-11). */
export default async function LandingPage() {
  // server-side flags (1 s timeout, all-false on failure): "make it yours" exists in the HTML only when live (L-10)
  const features = await fetchFeatures();
  return <Landing features={features} />;
}
