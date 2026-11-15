import { streamPost, type StreamHandlers } from './sse';

/** Empty in dev/prod when Next (or Caddy) proxies /api. Set NEXT_PUBLIC_API_BASE to call FastAPI directly (e.g. if the dev proxy buffers SSE). */
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? '').replace(/\/$/, '');
const url = (p: string) => `${API_BASE}${p}`;

// ---- wire types (mirror api/schemas.py)
export interface StepEvent {
  stage: string;
  title: string;
  detail: string;
  status: 'ok' | 'warn' | 'stop';
  ms: number;
}
export interface AnswerCitation {
  index: number;
  cited: boolean;
  book: string;
  edition: string;
  chapter: string;
  pages: string;
  section_id: string;
  excerpt?: string | null;
}
export interface AnswerEvent {
  text: string;
  status: string;
  route: string;
  citations: AnswerCitation[];
}
export interface SpatialAction {
  action: 'highlight';
  fma_ids: string[];
  label: string;
  tier: 'navigation';
}
export interface VerdictEvent {
  status: 'verdict' | 'insufficient';
  correct_option: number | null;
  chosen_wrong_because: string;
  explanation: string;
  citations: AnswerCitation[];
  viva_questions: string[];
}

export type ChatEvents = {
  step: StepEvent;
  answer: AnswerEvent;
  spatial: { actions: SpatialAction[] };
  done: { ms: number };
  error: { message: string; error_type?: string };
};
export type WhyEvents = {
  step: StepEvent;
  verdict: VerdictEvent;
  done: { ms: number };
  error: { message: string; error_type?: string };
};

export function streamChat(question: string, h: StreamHandlers<ChatEvents>, signal?: AbortSignal) {
  return streamPost<ChatEvents>(url('/api/chat/stream'), { question }, h, signal);
}
export function streamWhy(
  body: { question: string; options: string[]; chosen: number },
  h: StreamHandlers<WhyEvents>,
  signal?: AbortSignal,
) {
  return streamPost<WhyEvents>(url('/api/why/stream'), body, h, signal);
}

// ---- stored answers (share) + feedback
export interface ChatPayload {
  answer: AnswerEvent;
  spatial: SpatialAction[];
}
export interface WhyPayload {
  options: string[];
  chosen: number;
  verdict: VerdictEvent;
}
export interface AnswerRecord {
  id: string;
  kind: 'chat' | 'why';
  question: string;
  payload: ChatPayload | WhyPayload;
  created_at: number;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json() as Promise<T>;
}

/** Share cards carry pointers only: textbook excerpts are stripped before saving. */
const stripExcerpts = (cs: AnswerCitation[]) => cs.map((c) => ({ ...c, excerpt: null }));

export async function saveAnswer(kind: 'chat', question: string, payload: ChatPayload): Promise<string>;
export async function saveAnswer(kind: 'why', question: string, payload: WhyPayload): Promise<string>;
export async function saveAnswer(kind: 'chat' | 'why', question: string, payload: ChatPayload | WhyPayload): Promise<string> {
  const safe =
    'answer' in payload
      ? { ...payload, answer: { ...payload.answer, citations: stripExcerpts(payload.answer.citations) } }
      : { ...payload, verdict: { ...payload.verdict, citations: stripExcerpts(payload.verdict.citations) } };
  const res = await fetch(url('/api/answers'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind, question, payload: safe }),
  });
  return (await json<{ id: string }>(res)).id;
}

export async function getAnswer(id: string): Promise<AnswerRecord> {
  return json<AnswerRecord>(await fetch(url(`/api/answers/${encodeURIComponent(id)}`), { cache: 'no-store' }));
}

export type FeedbackKind = 'wrong_citation' | 'unhelpful' | 'other';
export async function sendFeedback(f: { answer_id?: string; question?: string; kind: FeedbackKind; note?: string }) {
  await json(
    await fetch(url('/api/feedback'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f) }),
  );
}
