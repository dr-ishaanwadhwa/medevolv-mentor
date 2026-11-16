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
/** Pointer for a [G#] graph fact the answer cites (no fact text). */
export interface GraphCitation {
  n: number;
  fact_id: string;
  book: string;
  edition: string;
  chapter: string;
  pages: string;
}
export interface AnswerEvent {
  text: string;
  status: string;
  route: string;
  citations: AnswerCitation[];
  /** Additive (R1). Older APIs omit both. */
  graph_citations?: GraphCitation[];
  /** HMAC the server checks on POST /api/diagram. Absent or null: no Flowchart chip (D-16). Never stored in shares. */
  answer_sig?: string | null;
}
/** One certified outgoing link of the answer's topic concept (our own ontology data). */
export interface RelatedTopic {
  id: string;
  label: string;
  predicate: string;
  tier: 'certified';
}
export interface TopicEvent {
  topic: string | null;
  related: RelatedTopic[];
}
export interface SpatialAction {
  action: 'highlight';
  fma_ids: string[];
  label: string;
  tier: 'navigation';
  sex?: 'male' | 'female' | null;
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
  topic: TopicEvent;
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
  /** The topic label only: shared pages fetch videos live, no YouTube data is ever stored (V-12). */
  topic?: string | null;
  related?: RelatedTopic[];
  /** A server-issued flowchart, shown read-only on the shared page. */
  diagram_id?: string | null;
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
      ? // answer_sig is dropped: shares are public and the signature has no use there (D-16)
        { ...payload, answer: { ...payload.answer, answer_sig: undefined, citations: stripExcerpts(payload.answer.citations) } }
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

export type FeedbackKind = 'wrong_citation' | 'unhelpful' | 'other' | 'diagram_wrong' | 'video_bad';
export async function sendFeedback(f: { answer_id?: string; question?: string; kind: FeedbackKind; note?: string; target_id?: string }) {
  await json(
    await fetch(url('/api/feedback'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f) }),
  );
}

// ---- flowchart maker (api/diagram.py, PRD 4.1)
export type DiagramKind = 'classification' | 'pathway' | 'sequence' | 'case' | 'drug';
export interface DiagramCite {
  kind: 'passage' | 'fact';
  n: number;
}
export interface DiagramNode {
  id: string;
  label: string;
  role: 'start' | 'step' | 'branch' | 'end' | 'warning';
  group: string | null;
  cites: DiagramCite[];
}
export interface DiagramEdge {
  from: string;
  to: string;
  label: string;
  cites: DiagramCite[];
}
export interface DiagramResponse {
  status: 'ok' | 'declined';
  diagram_id: string | null;
  source: 'ontology' | 'answer' | null;
  kind: DiagramKind | null;
  subject: string | null;
  title: string | null;
  groups: { id: string; title: string }[];
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  fact_sources: GraphCitation[];
  dropped: number;
  reason: string | null;
  version: number;
}
/** What a diagram request ended with; the copy map in lib/copy/diagram.ts turns it into UI. */
export type DiagramResult =
  | { kind: 'ok'; diagram: DiagramResponse }
  | { kind: 'declined'; reason: string }
  | { kind: 'http'; status: number }
  | { kind: 'abort' }
  | { kind: 'network' };

/** The client gives up after 35 s (the server's own budget is 30 s, D-13). */
export const DIAGRAM_CLIENT_TIMEOUT_MS = 35_000;

/** Echoes the answer event's four signed fields unchanged (the browser never builds or signs them). */
export async function requestDiagram(question: string, a: AnswerEvent, signal?: AbortSignal): Promise<DiagramResult> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), DIAGRAM_CLIENT_TIMEOUT_MS);
  signal?.addEventListener('abort', () => ctl.abort());
  try {
    const res = await fetch(url('/api/diagram'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        answer_text: a.text,
        citations: a.citations,
        graph_citations: a.graph_citations ?? [],
        answer_sig: a.answer_sig,
      }),
      signal: ctl.signal,
    });
    if (!res.ok) return { kind: 'http', status: res.status };
    const d = (await res.json()) as DiagramResponse;
    return d.status === 'ok' ? { kind: 'ok', diagram: d } : { kind: 'declined', reason: d.reason ?? 'unknown' };
  } catch {
    return ctl.signal.aborted ? { kind: 'abort' } : { kind: 'network' };
  } finally {
    clearTimeout(timer);
  }
}

/** A stored diagram for a shared page; null when missing, expired, switched off or unreachable. */
export async function getDiagram(id: string): Promise<DiagramResponse | null> {
  try {
    const res = await fetch(url(`/api/diagram/${encodeURIComponent(id)}`), { cache: 'no-store' });
    if (!res.ok) return null;
    const d = (await res.json()) as DiagramResponse;
    return d.status === 'ok' ? d : null;
  } catch {
    return null;
  }
}

// ---- suggested videos (api/videos.py, PRD 4.2)
export interface VideoCard {
  video_id: string;
  title: string;
  channel_title: string;
  channel_id: string;
  thumbnail_url: string;
  duration_seconds: number;
  duration_label: string;
  view_count: number;
  watch_url: string;
  allowlisted: boolean;
  long_lecture: boolean;
}
export interface VideosResponse {
  topic: string;
  videos: VideoCard[];
  fallback_url: string;
  fetched_at: string | null;
  source: 'cache' | 'api' | 'fallback';
  label: string;
}
export type VideosResult = { kind: 'ok'; data: VideosResponse } | { kind: 'off' } | { kind: 'fallback' };

/** POST (the topic travels in the body, never in a URL). 503 = switched off; 429 or any failure = fallback. */
export async function fetchVideos(topic: string, signal?: AbortSignal): Promise<VideosResult> {
  try {
    const res = await fetch(url('/api/videos'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic }),
      signal,
    });
    if (res.status === 503) return { kind: 'off' };
    if (!res.ok) return { kind: 'fallback' };
    return { kind: 'ok', data: (await res.json()) as VideosResponse };
  } catch {
    return { kind: 'fallback' };
  }
}

// ---- anonymous daily counters (api/events.py): at most once per page load per name (PRD 5.3)
const sentEvents = new Set<string>();
export function trackOnce(name: 'video_click' | 'question_sent_from_landing', props?: Record<string, string>) {
  const k = `${name}|${JSON.stringify(props ?? {})}`;
  if (sentEvents.has(k)) return;
  sentEvents.add(k);
  try {
    void fetch(url('/api/events'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(props ? { name, props } : { name }),
      keepalive: true,
    }).catch(() => {});
  } catch {
    /* counters never break the page */
  }
}

// ---- /how "Try your own question" (api/story.py)
export interface StoryExploreNeighbour {
  /** index into the story map (same order as library.bin) */
  i: number;
  sim: number;
  /** textbook display name, e.g. "Harrison's Principles of Internal Medicine (22nd ed.)" */
  book: string;
}
export interface StoryExploreResult {
  question: string;
  refused: boolean;
  neighbours: StoryExploreNeighbour[];
  best: number | null;
  min_similarity: number;
  passes_floor: boolean;
  narration: string;
}

export async function exploreStory(question: string, signal?: AbortSignal): Promise<StoryExploreResult> {
  const res = await fetch(url('/api/story/explore'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
    cache: 'no-store',
    signal,
  });
  return json<StoryExploreResult>(res);
}
