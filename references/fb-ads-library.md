# Facebook Ads Library — Scraping Reference

This reference covers the Meta/Facebook Ads Library specifics the flow depends on. All URLs are public; scraping requires a logged-in FB session for reliability.

## Base URL and parameters

Base: `https://www.facebook.com/ads/library/`

Verified query parameters (May 2026):

| Param | Values | Notes |
|---|---|---|
| `q` | URL-encoded keyword | Default match is unordered; use `search_type=keyword_exact_phrase` for exact phrase |
| `country` | ISO 3166-1 alpha-2 (e.g. `US`, `GB`) or `ALL` | Default to `ALL` unless the user specifies otherwise |
| `active_status` | `active` \| `inactive` \| `all` | Use `all` for the relevance pass; `active` to count current ads |
| `ad_type` | `all` \| `political_and_issue_ads` | Commercial app advertising lives in `all` |
| `media_type` | `all` \| `image` \| `video` \| `meme` \| `image_and_meme` \| `none` | Leave as `all` |
| `start_date[min]` / `start_date[max]` | `YYYY-MM-DD` | URL-encode brackets as `%5Bmin%5D` |
| `view_all_page_id` | numeric Page ID | Lists all ads from one Page |
| `search_type` | `keyword_unordered` \| `keyword_exact_phrase` \| `page` | `page` returns Pages, not ads — use this for Phase 1's broad sweep |

## Page-ID namespaces — profile ID ≠ Ad Library Page ID

Facebook uses **two different numeric ID namespaces** for the same advertiser:

| Namespace | Where it works | Where it does NOT |
|---|---|---|
| **Profile ID** (a.k.a. `userID`) — what you see in `facebook.com/profile.php?id=<id>`, the dedup key for Pages in our state (the `page_id` field), and what FB returns from page-search result-card hrefs | Navigating to the Page profile (`facebook.com/<id>`), `userID:"<id>"` in page source | The Ad Library's `view_all_page_id` URL parameter (sometimes works, often does not) |
| **Ad Library Page ID** — what FB Ad Library uses to key its advertiser-scoped views, stored in our state as `view_all_page_id` | `view_all_page_id=<id>` URLs — always renders the Page's ads if the Page advertises | `facebook.com/profile.php?id=<id>` (gives a "page not found" or unrelated entity) |

The two IDs **identify the same advertiser** but are different numbers. They coincide for ~45% of Pages in our 8-project sample (2026-05-15) and diverge for the other ~55%. There is no pattern that tells you which case you're in without testing.

**Implication for the audit**: never write a `view_all_page_id` URL using the profile ID without resolving (or sanity-checking) that it's the Ad Library Page ID first. The empty-state page that FB shows when the IDs mismatch is silent — country=ALL, active_status=all, logged-in user, real Page that is currently running ads → still "No ads match your search criteria." (In other cases the URL silently rewrites and renders an unrelated Page entirely.)

### How to resolve the Ad Library Page ID from the profile ID

Two methods, in priority order:

**Method 1 — via an evidence ad ID (preferred)**:

For each Page, take any one of the ad archive IDs (`ad_archive_id` / `libId` / `lib_id`) captured in Phase 2 scrape data. Fetch the ad-detail HTML (auth-required) and read the `page_id` field from the embedded initial state:

```js
async function resolveAdLibraryPageId(evidenceAdId) {
  const res = await fetch(`https://www.facebook.com/ads/library/?id=${evidenceAdId}`,
                          {credentials: 'include'});
  const html = await res.text();
  return html.match(/"page_id"\s*:\s*"?(\d{6,20})"?/)?.[1] ?? null;
}
```

Run in parallel (chunks of 6–8) for the full Page list — a 33-Page audit resolves in <10 seconds.

**Method 2 — pre-flight check on the existing URL** (use when there are no evidence ad IDs for the Page, or to verify Method 1's output):

```js
async function viewAllPageIdWorks(candidateId) {
  const res = await fetch(`https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&view_all_page_id=${candidateId}`,
                          {credentials: 'include'});
  const html = await res.text();
  return html.length > 800000;   // empty-state ≈709k, working ≈830k+
}
```

The "No ads match your search criteria" phrase is rendered client-side and is NOT in the initial HTML — do not grep for it. The 800k preloaded-data signal is the reliable check.

**Fallback when neither method yields a working ID** (rare: Pages with zero captured evidence and a profile ID that also doesn't work):

Use FB Ad Library keyword search by Page name:

```
https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q=<URL-ENCODED-NAME>&search_type=keyword_unordered
```

Mark the row's resolution as `keyword_fallback`. Phase 4 will write this keyword-search URL into the `Page URL` column and add a note in the `Notes` column that the link is a fallback keyword search, not a Page-scoped view, because Ad Library Page ID resolution failed.

## Two URL patterns this skill uses

**Page search** (Phase 1, broad sweep):
```
https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&search_type=page&q=<URL-ENCODED-SEED>
```
Each result is a Page card with: Page name, Page ID, Page URL.

> ### Critical: use the FB Ads Library Page search, not general Facebook Pages search
>
> `facebook.com/ads/library/?search_type=page&q=...` returns Pages that have **run ads** (the Ads Library corpus). This is what you want.
>
> `facebook.com/search/pages/?q=...` is the general Facebook Pages directory. It returns Pages that **exist**, including ones that have never advertised. If you use this URL, you can completely miss the advertiser Page you actually need to audit — a real failure mode observed in iter-1.
>
> Always use the Ads Library URL above. If the FB SPA appears to return ad results instead of Page cards, the URL may be getting interpreted as a keyword search — see "Robust Page discovery" below for fallbacks.

### Robust Page discovery — multiple strategies

The FB Ads Library UI evolves. If the standard URL doesn't return Page cards as expected, layer these strategies:

1. **Primary**: navigate to `https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&search_type=page&q=<seed>`. Wait for results. Inspect the DOM — if you see Page-card elements (each with a "View ads" or "X ads" link), you're in Page mode. Extract Page IDs from those cards.

2. **Fallback A — UI filter**: navigate to the base Ads Library `https://www.facebook.com/ads/library/`, then via `browser_evaluate` or `browser_snapshot` find and click the **"Advertisers"** tab or similar Page filter. Then type the seed into the search box. The UI version is sometimes more stable than the URL version.

3. **Fallback B — per-keyword ad results, then group by Page**: if Page-mode search refuses to return Pages, do a regular keyword search (`search_type=keyword_unordered`) and look at the advertiser badges on each ad card. Group ads by their advertiser Page and treat each unique Page as a candidate. This is less direct but always available.

4. **Fallback C — direct vanity URL**: if you know or strongly suspect a Page handle (e.g., from web search), construct `https://www.facebook.com/<vanity>/about` and read the Page ID from the page source (look for `"pageID":"<numeric>"` or `"userID":"<numeric>"` in inline JSON, or from a meta tag).

Enumerate exhaustively. **A brand may have 3–8 Pages**: a social-engagement Page, one or two advertising Pages, regional variants, and sometimes Pages named after the parent company or a paid-media agency. Phase 1's job is to collect ALL of them; pruning happens at the Phase 1.5 gate.

**Per-Page ad list** (Phase 1 relevance check + Phase 2 deep scrape):
```
https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&view_all_page_id=<PAGE_ID>
```
Add `start_date[min]=<today-90d>` for the 90-day window used in Phase 2.

### Verify a Page is live before flagging

Some Page handles in search results return "This content isn't available right now" when navigated. Before flagging a candidate Page:

1. Navigate to its `view_all_page_id` URL.
2. If the page renders "isn't available", "page removed", or the body shows the FB error component: discard. Do not include in the candidate list.
3. If the page renders the Ads Library view (with the Page name + ad count + ad cards or "not currently running ads" text): keep.

## Login requirement

**A logged-in FB session is mandatory.** Meta's docs suggest commercial ads are browsable anonymously, but in practice anonymous scraping:
  - caps result lists at ~30 cards per query (vs hundreds when authed),
  - returns inconsistent counts (auth and anonymous can disagree by 10-30%),
  - hides Page-id ⇄ vanity-url mappings the audit needs,
  - is rate-limited and intermittently challenged.

If auth fails or the user cannot log in, HALT — do not silently fall back to anonymous.

**Regional caveat**: some FB accounts (observed: Belarus) receive HTTP 403 on the Ads Library endpoint specifically while the rest of FB works normally. The 403 appears as an infinite spinner with `Failed to load resource: 403` in the console. Workaround: ask the user to connect a VPN to a non-restricted region (US/EU/UK) and re-auth, or use a different account from such a region.

The skill saves the FB session storage to `~/.claude/skills/competitors-w2w-research/.auth/fb_session.json`. Session age >30 days = re-auth.

## Playwright MCP usage

The skill uses the `mcp__playwright__*` tools, not Python Playwright directly. The relevant tools:

- `mcp__playwright__browser_navigate` — open a URL
- `mcp__playwright__browser_snapshot` — get the accessibility tree. **Caveat**: on FB Ads Library result pages this can return ~100K+ characters and exceed token limits. For FB Ads Library DOM extraction, prefer `browser_evaluate` with targeted JS queries (see "DOM extraction" below).
- `mcp__playwright__browser_take_screenshot` — for the user to see what's happening during auth
- `mcp__playwright__browser_press_key` — `End` to scroll, `PageDown` for incremental scrolling
- `mcp__playwright__browser_evaluate` — run JS in the page. **This is the primary DOM extraction tool for FB Ads Library** — use it to read ad cards, Page IDs, destination URLs.
- `mcp__playwright__browser_wait_for` — wait for a CSS selector / text before reading

### Auth flow (first time)

1. `browser_navigate` to `https://www.facebook.com/login`.
2. Show the user a screenshot. Tell them: "I've opened Facebook in a browser. Please log in. When you see your news feed, come back here and reply 'logged in'."
3. **Wait** for the user's reply (this is a manual gate; do not poll the page).
4. When the user confirms, navigate to `https://www.facebook.com/ads/library/` to verify the session works (the page should show the Library, not a login redirect).
5. Save the storage state. Playwright MCP exposes a way to capture storage — if not directly available, the session cookie persists in the browser context for this run; for cross-run persistence, document this as a v2 enhancement and continue without persistent storage.

> **Note**: If Playwright MCP doesn't expose a way to persist storage state across runs, log in fresh each invocation but still notify the user clearly.

### Page-search pass (Phase 1)

For each seed `q`:

1. `browser_navigate` to the Page-search URL above.
2. Wait for the results list to render (`browser_wait_for` for a stable element, e.g. text `Page` or the search result count).
3. Use `browser_evaluate` with a JS snippet that selects each Page result card and returns an array of `{page_id, page_name, page_url}`. The Page ID is typically in the link `view_all_page_id=<id>` URL parameter, OR in a `data-` attribute. Find a stable selector during testing.
4. Append results to the working set; de-dup by `page_id`.

### Per-Page relevance check (Phase 1)

For each candidate Page:

1. `browser_navigate` to the per-Page URL above (with `active_status=all`, no date range — we want the recent history).
2. Scroll incrementally (loop: `browser_press_key End`, wait 1–2 seconds, re-snapshot, repeat until scroll position stops changing OR you've loaded ≥50 ads OR you've scrolled 10 times).
3. Use `browser_evaluate` to extract: for each ad card, the destination URL shown in the link-preview block (NOT the FB-wrapped `l.facebook.com/l.php?u=...` — unwrap by reading the `u=` query parameter or by following the link).
4. Apply the relevance rule in `flow.md` § Phase 1 step 6.

### Per-Page deep scrape (Phase 2 — TWO scrapes per Page)

> **Important**: Phase 2 needs **two separate scrapes** per Page. A single combined `active_status=all&start_date[min]=<today-90d>` query MISSES ads that started >90 days ago but are still running today (an ad that started 18 months ago and is still `active=true` will be excluded by `start_date[min]`). Iter-2 user feedback caught this bug.

**Scrape 1 — active ads** (no date filter):
```
https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&view_all_page_id=<PAGE_ID>
```
- Read the FB UI's count: match `~\s*(\d+(?:,\d{3})*)\s+results` in body text. That number is `fb_ui_active_ads_count`.
- If page shows `No ads match your search criteria` or `This advertiser isn't running ads`, count is `0`.
- Every ad visible under this filter is active by construction — don't try to detect Active/Inactive badges per card (unreliable; see DOM extraction notes below).

**Scrape 2 — historical context** (last 90 days, any status):
```
https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&start_date[min]=<YYYY-MM-DD>&view_all_page_id=<PAGE_ID>
```
- Scroll to load all ad cards in the window.
- Extract every ad's full record:

```
{
  "ad_archive_id": "...",
  "active": true|false,
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD" | null,
  "destination_url_raw": "https://l.facebook.com/l.php?u=...",
  "destination_url_unwrapped": "https://example.com/get?utm_source=fb",
  "destination_url_resolved": "https://example.com/get"
}
```

`active` is the `Active`/`Inactive` badge or the FB UI's "Active ad" indicator. `start_date` is the "Started running on" date from the ad card. `end_date` is the "Last shown" date (only present when inactive).

After resolving, also pull the per-Page "Active ads" count from the page header (the number FB displays). This is `fb_ui_active_ads_count`.

## DOM extraction — pragmatic notes

The FB Ads Library SPA renames CSS classes regularly. Do **not** rely on `class` attributes. Use:

- `data-testid` attributes when present.
- Anchor by visible text (e.g., "Started running on", "Library ID").
- Library ID format: `Library ID: <numeric>` is a stable adjacent label to the ad_archive_id.
- The destination URL in the card preview shows: the destination domain in small text under the headline. Click-through preview captures the full path. If only the domain is visible, click "See ad details" or extract from the wrapped `l.facebook.com/l.php?u=` link associated with the ad's CTA button.

### Page-ID extraction

Page IDs no longer appear consistently in result-card URL parameters (`view_all_page_id=...` is for the per-Page view, not always in search results). Reliable sources for a numeric Page ID:

1. Inline JSON on the Page's profile or Ads Library view: search the page source for `"pageID":"<numeric>"` or `"userID":"<numeric>"`. `pageID` is the more authoritative when both are present.
2. The href of an "ads" link on a result card — extract the `view_all_page_id` query parameter.
3. From a vanity URL: navigate to `https://www.facebook.com/<vanity>/about` (or just `/<vanity>`) and grep the source for the two patterns above.

> **Note on namespaces:** the ID extracted here is the **profile ID** (stored in state as `page_id`). It is the right value for dedup, profile-URL navigation, and as the foreign key between Phase 1 and Phase 2. It is **not** always the same as the **Ad Library Page ID** (the value that goes into the `view_all_page_id=` URL parameter and is stored in state as `view_all_page_id`). See § "Page-ID namespaces — profile ID ≠ Ad Library Page ID" above for the resolution method that converts one to the other. Phase 2 step 5.5 (`references/flow.md`) does this conversion before any Page URL is rendered.

Use `browser_evaluate` with a small JS snippet to do this — pass the result back as JSON.

### Recommended JS snippets

For result-card Page ID extraction:
```js
() => Array.from(document.querySelectorAll('a[href*="view_all_page_id="]'))
  .map(a => {
    const m = a.href.match(/view_all_page_id=(\d+)/);
    return m ? { page_id: m[1], page_name: a.textContent.trim().slice(0, 80), page_url: a.href } : null;
  })
  .filter(Boolean)
```

For ad-card destination extraction (per-Page deep scrape):
```js
() => Array.from(document.querySelectorAll('a[href*="l.facebook.com/l.php"]'))
  .map(a => {
    const m = a.href.match(/[?&]u=([^&]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  })
  .filter(Boolean)
```

Adapt selectors as needed if FB changes its DOM. The principles — anchor on stable URL/href patterns, not CSS classes — are durable even when FB ships UI changes.

If a stable extraction strategy isn't yielding results, broaden the JS to select all anchors and inspect everything. Better to over-collect and filter than to under-collect.

### Variant render probe (Phase 2 step 8c)

When grouping ads into funnels surfaces multiple values for a variant query param (`cohort`, `funnel`, `variant`, etc.), navigate Playwright to each variant URL, wait 5–8s for SPA hydration, then run this JS verbatim to capture the post-render state:

```js
// Variant render probe (after navigate + ~5s wait)
() => ({
  variant_value: new URLSearchParams(location.search).get('cohort')
                 ?? new URLSearchParams(location.search).get('funnel')
                 ?? new URLSearchParams(location.search).get('variant'),
  final_slug: location.pathname,
  title: document.title,
  headers: Array.from(document.querySelectorAll('h1, h2, h3, [role="heading"]'))
    .slice(0, 5)
    .map(h => h.textContent.trim().slice(0, 120))
    .filter(Boolean),
  body_sample: document.body.innerText.slice(0, 600)
})
```

Compare `final_slug` and `headers` across variant values to decide whether to split into separate funnel rows (per `flow.md` Phase 2 step 8c decision rule).

## Rate / etiquette

- Wait 0.5–1.5s between Page navigations.
- If you see a checkpoint or login prompt mid-run, halt and instruct the user to re-authenticate (delete the auth file).
- Do not parallelize per-Page scrapes inside this skill — keep it sequential to avoid challenge flows.

## What to record in state

For each Page:
- `page_id`, `page_name`, `page_url`, `view_all_url`
- `fb_ui_active_ads_count` (Phase 2)
- `script_active_ads_count` = count of ads where `active: true` you extracted yourself
- `last_ad_launched` = `max(start_date)` across all ads
- `ad_types` = `app | w2w | both` per `flow.md` Phase 2 step 6
- `status` = `Active | Cold` per `status-classification.md`

For each ad: full record per the schema above.

These records feed `phase_2.ad_pages_deep_scraped[].ads` in state and the `ad-pages.csv` table at the end.
