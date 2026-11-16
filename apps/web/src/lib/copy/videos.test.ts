import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { VIDEOS_COPY, captionLine, cardLinkName, viewsLabel, youtubeSearchUrl } from './videos';

describe('videos copy', () => {
  it('equals shared/copy/videos.json (the one source the API mirrors too)', () => {
    const shared = JSON.parse(readFileSync(join(__dirname, '../../../../../shared/copy/videos.json'), 'utf8'));
    expect(VIDEOS_COPY).toEqual(shared);
  });
  it('builds the same fallback link as the API, from the topic label only', () => {
    expect(youtubeSearchUrl('  Nephrotic   Syndrome ')).toBe(
      'https://www.youtube.com/results?search_query=nephrotic+syndrome+lecture+MBBS',
    );
  });
  it('formats views and captions', () => {
    expect(viewsLabel(123456)).toBe('123K views');
    expect(viewsLabel(1_250_000)).toBe('1.3M views');
    expect(viewsLabel(5400)).toBe('5.4K views');
    expect(viewsLabel(999)).toBe('999 views');
    expect(captionLine('20:34', 123456)).toBe('20:34 · 123K views');
    expect(cardLinkName('T', 'C', '20:34')).toBe('Video: T, C, 20:34, opens YouTube in a new tab');
  });
});
