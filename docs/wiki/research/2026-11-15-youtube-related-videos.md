# Research: YouTube related videos under answers (MedEvolv Mentor)

As checked 2026-11-15. Sources are Google/YouTube developer pages fetched that day (WebFetch summaries, so re-read the quoted clauses before relying on them for legal compliance). No account, key, or API call was made.

## TL;DR
- The key-based path is cheap and workable: `search.list` + `videos.list` = 2 calls per answer. Default quota supports roughly **100 answers/day uncached** (the 100-search/day cap is the binding limit, not the 10,000 general units). With a topic cache it is far more.
- Quota docs as fetched today differ from the older "search costs 100 units" folklore. See section 1.
- Policy burden is modest: store API data max 30 days, show thumbnails unaltered, attribute YouTube, link out, have a privacy policy that mentions YouTube API Services and links Google's policy.
- Scraping / yt-dlp / Invidious / Piped is not allowed by YouTube's ToS. Do not use it.
- Zero-risk fallback: a "Search on YouTube" link to `https://www.youtube.com/results?search_query=...`.
- `relatedToVideoId` is dead (removed 2023-08-07). Use the app's own ontology for "related topics".
- Medical content: no YouTube policy requirement either way. The trust burden is ours (allowlist + honest label).

## 1. YouTube Data API v3 `search.list`

Sources: https://developers.google.com/youtube/v3/getting-started , https://developers.google.com/youtube/v3/determine_quota_cost , https://developers.google.com/youtube/v3/docs/search/list , https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits (all checked 2026-11-15).

- **Default quota (as checked 2026-11-15):** "100 `search.list` calls, 100 `videos.insert` calls, and 10,000 units per day combined for all other endpoints." Docs say the default is subject to change.
- **Cost per call:** `search.list` is listed as 1 unit in a dedicated "Search Queries" bucket capped at 100 calls/day. `videos.list` is 1 unit from the general 10,000 pool. Note: this is a change from the older model where `search.list` cost 100 units out of 10,000 (same practical ceiling of ~100 searches/day). **Verify on the Quotas page of the Cloud console once a key exists**; the docs say the numbers may change.
- **More quota:** complete the "YouTube API Services - Audit and Quota Extension Form". Extensions above default require a compliance audit first (or, if audited in last 12 months, the form directly). Review time is not stated.
- **Pricing:** none of the fetched pages state any price. YouTube Data API access via the default quota has historically been free; the API ToS only mentions amounts "paid by you" in a liability clause. Treat "free at default quota" as likely but unverified here.
- **Params for our use** (all confirmed in the search.list reference):
  - `part=snippet`, `type=video` (required for the video-only filters below)
  - `q=<query>`, `order=relevance` (default)
  - `safeSearch=strict` (options: moderate default / none / strict)
  - `relevanceLanguage=en`, `regionCode=IN`
  - `videoDuration=medium` (4-20 min) or `long` (>20 min); `short` is under 4 min. Lectures often exceed 20 min, so either leave `any` and filter after `videos.list`, or run one call with `medium`.
  - `videoEmbeddable=true` is only needed if we embed a player. We open YouTube in a new tab, so do NOT set it (it would drop good videos).
  - `maxResults` 0-50 (default 5); ask for ~10, show 3-4 after filtering.
  - `channelId` limits results to one channel (useful for allowlist, but one call per channel, so costly).
- **Channel name, duration, views:** `search.list` snippet gives `channelTitle`, `title`, `thumbnails`, `channelId` but not duration or views. Call `videos.list?part=snippet,contentDetails,statistics&id=ID1,ID2,...` (1 unit, comma-separated ids; the doc page does not state a max, 50 is the commonly used batch size). Fields (checked 2026-11-15 on the videos resource page): `snippet.channelTitle`; `contentDetails.duration` ISO 8601 (e.g. `PT15M33S`); `statistics.viewCount` returned as a string. Thumbnails: `default` 120x90, `medium` 320x180, `high` 480x360, others on some videos.
- **Capacity math (default quota):** per answer = 1 search + 1 videos.list. Search bucket 100/day -> **100 answers/day** uncached. General pool use = 100 units, negligible. If your doc reading is the older 100-unit model: 10,000/(100+1) = 99 answers/day, same result. Caching by topic (most MBBS queries repeat topics) can multiply effective capacity several times; a seeded cache per ontology concept would make the live API almost unnecessary.

## 2. Policy constraints

Sources: Developer Policies https://developers.google.com/youtube/terms/developer-policies ; Policies guide https://developers.google.com/youtube/terms/developer-policies-guide ; API Terms https://developers.google.com/youtube/terms/api-services-terms-of-service ; Branding https://developers.google.com/youtube/terms/branding-guidelines (all checked 2026-11-15; WebFetch summaries, verify exact clauses).

- **Caching (Dev Policies III.E.4):** non-authorized API data may be stored only "no longer than 30 calendar days", then deleted or refreshed; statistics (e.g. view counts) not for more than 30 days; keep it reasonably consistent with YouTube and show the most updated data available. Do not substitute your own computed metrics for YouTube's. **Design: TTL 24h-7d, hard max under 30 days.** Store only needed fields.
- **Attribution (III.F.2):** any feature showing YouTube content must make clear YouTube is the source; non-YouTube content must not suggest it is from YouTube. Branding: do not use "YouTube" in our app name; use the YouTube logo/icon (unaltered, fully visible, not the most prominent element, clickable to YouTube) near the feature. Do not imply YouTube endorsement.
- **Thumbnails:** no standalone thumbnail rule in the Developer Policies. The policies guide says thumbnails "must not be altered" and thumbnails/titles must be "visible to the viewer and unmodified". So: use the API-provided URL, no cropping that obscures, no filters, no text overlay on the image. Put the "opens YouTube" icon and duration beside or below it, not on it, to be safe (duration badge on the image is YouTube's own pattern, but treat as a risk; place it in the caption).
- **Links:** III.I.4 forbids removing/altering links in API data. Link each card to the canonical watch URL `https://www.youtube.com/watch?v=ID` (new tab). The guide says links should open the YouTube app when available (mobile web does this by default).
- **Search results (III.C.5):** must not modify/replace YouTube search results or mix in other sources presented as YouTube results. Our "allowlist boost" is fine as long as we do not claim these are "YouTube's results" in rank order. Label them "Suggested videos".
- **Privacy policy (III.A.2):** users must agree to a privacy policy that is prominently accessible, discloses use of YouTube API Services, links Google's Privacy Policy (https://policies.google.com/privacy), and says what data is collected/shared. Also III.A.1: display a link to YouTube's Terms of Service (https://www.youtube.com/t/terms) and state users are bound by them. We send only a topic string to the API, not user identity, but the policy page is still required.
- **Medical/health:** no health-content rule found in Developer Policies. Only mentions: III.I.17 bars use where failure "could lead to death, personal injury" (life-support style; study suggestions do not fit), and health information is listed among personal data not to be inferred/derived about users without consent. Do not log "this user searched for X condition" against a user id beyond what the privacy policy states.
- **Scraping/circumvention:** API ToS 3.1 limits access to the API; 15 forbids circumventing quota; YouTube ToS (https://www.youtube.com/t/terms) forbids accessing the Service "using any automated means (such as robots, botnets or scrapers)" except search engines per robots.txt or with written permission.

## 3. Keyless alternatives

(a) **Search URL link** `https://www.youtube.com/results?search_query=<urlencoded>`: zero API, just a hyperlink out. Fully allowed; no thumbnails, so it is a "Search YouTube for ..." button. Zero quota, zero policy surface except normal ToS. Use as the permanent fallback.

(b) **Scraping / yt-dlp / Invidious / Piped:** prohibited by YouTube ToS (automated access), and the API terms bar non-API access to API-style data. Practical risk: breaks without notice, IP blocks on a small shared Oracle VM, public Invidious/Piped instances are unreliable and frequently shut down, and a trust-first medical product depending on a ToS violation is a liability. **Recommendation: do not use.** (This is a policy/risk statement; I did not test any of these.)

(c) **oEmbed** for known video ids: `https://www.youtube.com/oembed?url=<watch-url>&format=json` returns title, author_name (channel), thumbnail_url without a key. I did not fetch the YouTube endpoint itself (only confirmed the generic oEmbed spec at https://oembed.com/ loads), and it gives no duration/views. Suited to a hand-curated list of known video ids per concept (curated by the team), not for discovery. Policy status of oEmbed vs the API terms is not clearly addressed in the pages read; treat as lower-risk but unverified, and still attribute and link out.

## 4. Quality and safety for medical education

- **Allowlist of channels (candidates only; the team MUST verify every channel id and that each channel is the real, current one, no ids are given here deliberately):** Osmosis from Elsevier; Armando Hasudungan; Ninja Nerd; Dr. Najeeb Lectures; Khan Academy Medicine; Medscape/Lecturio; Marrow; PrepLadder; DAMS; Dr. Bhatia Medical Education; plus any Indian faculty channels the team already trusts (add by name after verifying). Names are from general knowledge, not from any source fetched. Treat them as search terms to verify, not facts.
- **How to use the list cheaply:** do not run one search per channel. Instead, run 1 general search with `maxResults=25`, then sort allowlisted `channelId`s first (client-side ranking) and cap non-allowlist items at 1. The ranking is ours; label it honestly.
- **safeSearch=strict**: filters restricted content but does not guarantee clinical accuracy.
- **Duration:** require 4 to 90 min. Drop under 4 min (shorts-style, low depth), flag over 90 min "long lecture". Parse ISO 8601 from `contentDetails.duration`.
- **Other filters:** require `viewCount` above a floor (e.g. 5k) to drop junk; drop titles with "NEET PG shortcut", "mnemonic only", clickbait cues; drop non-English if `relevanceLanguage=en` leaks.
- **Honest labelling (copy):** "Suggested videos from YouTube. These are not from your textbooks, are not checked by MedEvolv, and may differ from the cited answer. Always trust the cited textbook passages first." Put the YouTube icon beside it. Never mix the cards visually into the cited-answer block; use a separate section under the citations.
- Never show video content as a source of the answer, never feed video text into the answer (cite-or-decline stays textbook-only).

## 5. Query construction and related topics

- Build `q` from the **structured topic label** already extracted (e.g. "nephrotic syndrome"), not from the answer prose. Query 1: `"<topic> lecture MBBS"`. Optional query 2 only if cache cold and budget allows: `"<topic> pathology OR pharmacology explained"` (use the answer's subject/discipline tag, e.g. anatomy, physiology). Use `%7C` for OR in the URL (per the search.list doc). One query is usually enough; keep 1 to protect quota.
- Normalize the cache key: lowercase topic + subject; so repeated asks hit the cache.
- **Related topics:** do not use YouTube for this. `relatedToVideoId` was deprecated 2023-06-12 and stopped working 2023-08-07 (https://developers.google.com/youtube/v3/revision_history , checked 2026-11-15). Use the app's ontology links (neighbors of the concept node: causes, differentials, drugs, investigations) and render them as in-app chips that start a new cited question.

## 6. Recommended design

**Backend (FastAPI)** `GET /api/videos?topic=<label>&subject=<optional>`
- Env: `YOUTUBE_API_KEY` in `.env` (never to the frontend; restrict the key to the YouTube Data API v3 and the VM's IP in the console).
- Flow: normalize key -> cache lookup (SQLite table `video_cache(key, json, fetched_at)`; TTL 7 days, purge anything older than 14, absolutely under the 30-day cap) -> on miss: `search.list` (q, type=video, safeSearch=strict, relevanceLanguage=en, regionCode=IN, maxResults=15, part=snippet) -> `videos.list` (part=snippet,contentDetails,statistics; ids joined) -> filter (duration 4-90 min, view floor, drop duplicates) -> rank (allowlisted channels first, then API order) -> keep top 4 -> store -> return.
- Rate limit: per-IP/user 30 req/min and a global daily counter (alert and degrade at 80 searches/day). Single-flight lock per key to avoid duplicate concurrent searches.
- Degradation: if key missing, quota exhausted (HTTP 403 `quotaExceeded`), or any upstream error: return `{"videos": [], "fallback_url": "https://www.youtube.com/results?search_query=..."}`, status 200. UI shows only the "Search YouTube" link.
- Never log user ids with topic strings (privacy policy consistency).

**Response fields**
```json
{
  "topic": "nephrotic syndrome",
  "videos": [{
    "video_id": "...",
    "title": "...",
    "channel_title": "...",
    "channel_id": "...",
    "thumbnail_url": "https://i.ytimg.com/...",   // medium (320x180), unmodified
    "duration_seconds": 1234,
    "duration_label": "20:34",
    "view_count": 123456,
    "watch_url": "https://www.youtube.com/watch?v=...",
    "allowlisted": true
  }],
  "fallback_url": "https://www.youtube.com/results?search_query=nephrotic+syndrome+lecture+MBBS",
  "fetched_at": "2026-11-15T10:00:00Z",
  "source": "cache|api|fallback"
}
```

**UI card:** thumbnail (unaltered, 16:9, alt = title), title (2 lines), channel name, duration and views in the caption, small "Opens YouTube" external-link icon plus YouTube icon attribution, anchor with `target="_blank" rel="noopener noreferrer"`. A shared section header: "Videos on YouTube" with the honest label from section 4, and a trailing "Search YouTube for more" link (the fallback URL). Related topics chips (ontology) sit in a separate row. Footer/privacy page: mention YouTube API Services, link Google Privacy Policy and YouTube ToS.

**Before shipping (open items):** verify live quota on the Cloud console Quotas page; verify allowlist channel ids; confirm oEmbed policy stance if used; re-read clauses III.A, III.E.4, III.F.2 verbatim; decide whether to apply for audit/extension if daily answers exceed ~100 uncached.
