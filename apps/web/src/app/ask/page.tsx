import type { Metadata } from 'next';
import { ChatView } from '@/components/chat/ChatView';

export const metadata: Metadata = { title: 'Ask' };

/** Ask lives at /ask (PRD D-6). Until the landing switch, / renders the same view. */
export default function AskPage() {
  return <ChatView />;
}
