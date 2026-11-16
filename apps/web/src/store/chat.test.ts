import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../lib/api', () => ({
  streamChat: vi.fn(() => Promise.resolve()),
  requestDiagram: vi.fn(),
}));

import { requestDiagram, streamChat } from '../lib/api';
import { markAsked, useChat } from './chat';

const answer = { text: 'A [1]. B [1]. C [1].', status: 'answered', route: 'single', citations: [], answer_sig: 'sig' };

beforeEach(() => {
  useChat.setState({ turns: [], busy: false, diagramPaused: false, diagramOff: false, diagramCooldownUntil: 0 });
  vi.mocked(streamChat).mockClear();
});

describe('mm_asked cookie (D-5)', () => {
  it('writes mm_asked=1 for a year, once', () => {
    const doc = { cookie: '' };
    markAsked(doc);
    expect(doc.cookie).toBe('mm_asked=1; Path=/; Max-Age=31536000; SameSite=Lax');
    doc.cookie = 'theme=dark; mm_asked=1';
    markAsked(doc);
    expect(doc.cookie).toBe('theme=dark; mm_asked=1');
  });
});

describe('related-topic tap (V-9)', () => {
  it('appends a new turn to the same thread, keeping the earlier turns', () => {
    useChat.setState({
      turns: [{ id: 't1', question: 'Nephrotic syndrome?', steps: [], spatial: [], phase: 'done', answer }],
    });
    useChat.getState().ask('Minimal change disease');
    const turns = useChat.getState().turns;
    expect(turns.map((t) => t.question)).toEqual(['Nephrotic syndrome?', 'Minimal change disease']);
    expect(turns[1].phase).toBe('streaming');
    expect(streamChat).toHaveBeenCalledWith('Minimal change disease', expect.anything(), expect.anything());
  });
});

describe('drawDiagram', () => {
  const turn = { id: 't1', question: 'Q', steps: [], spatial: [], phase: 'done' as const, answer, shareId: 'old' };

  it('one request while loading; an ok diagram clears the old share id', async () => {
    let resolve!: (v: unknown) => void;
    vi.mocked(requestDiagram).mockReturnValueOnce(new Promise((r) => (resolve = r)) as never);
    useChat.setState({ turns: [turn] });
    useChat.getState().drawDiagram('t1');
    useChat.getState().drawDiagram('t1');
    expect(requestDiagram).toHaveBeenCalledTimes(1);
    resolve({ kind: 'ok', diagram: { status: 'ok', diagram_id: 'd1' } });
    await new Promise((r) => setTimeout(r, 0));
    const t = useChat.getState().turns[0];
    expect(t.diagram).toMatchObject({ s: 'ok' });
    expect(t.shareId).toBeUndefined();
  });

  it('budget pauses, 503 switches off, 429 cools down for a minute', async () => {
    for (const [r, check] of [
      [{ kind: 'declined', reason: 'budget' }, () => expect(useChat.getState().diagramPaused).toBe(true)],
      [{ kind: 'http', status: 503 }, () => expect(useChat.getState().diagramOff).toBe(true)],
      [{ kind: 'http', status: 429 }, () => expect(useChat.getState().diagramCooldownUntil).toBeGreaterThan(Date.now() + 50_000)],
    ] as const) {
      vi.mocked(requestDiagram).mockResolvedValueOnce(r as never);
      useChat.setState({ turns: [{ ...turn, diagram: undefined }] });
      useChat.getState().drawDiagram('t1');
      await new Promise((res) => setTimeout(res, 0));
      check();
      expect(useChat.getState().turns[0].diagram).toMatchObject({ s: 'failed' });
    }
  });

  it('never runs for an unsigned answer', () => {
    vi.mocked(requestDiagram).mockClear();
    useChat.setState({ turns: [{ ...turn, answer: { ...answer, answer_sig: null } }] });
    useChat.getState().drawDiagram('t1');
    expect(requestDiagram).not.toHaveBeenCalled();
  });
});
