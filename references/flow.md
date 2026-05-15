# Flow — Per-Phase Playbook

This is the load-bearing reference for the skill. Follow it in order; do not skip steps. Each phase begins with a "Read state" step and ends with a "Write state" step — state is the source of truth between phases.

## State file schema

State lives at `<app-slug>-state.json` (or `unlinked-<host>-state.json`) in the current working directory. The full schema:

```json
{
  "skill_version": "1",
  "input": {
    "raw": "<the string the user pasted>",
    "type": "app_store_url | bundle_id | app_name | funnel_url",
    "received_at": "ISO-8601"
  },
  "app": {
    "linked": true,
    "track_id": 1234567890,
    "bundle_id": "com.example.app",
    "track_name": "App Name",
    "seller_name": "Publisher Inc.",
    "seller_url": "https://publisher.example.com",
    "track_view_url": "https://apps.apple.com/...",
    "description": "...",
    "release_notes": "...",
    "primary_genre_name": "Health & Fitness",
    "language_codes": ["EN", "ES"],
    "artist_id": 987654321,
    "screenshot_urls": ["..."]
  },
  "phase_0": {
    "completed_at": "ISO-8601",
    "keywords_proposed": ["..."],
    "domains_discovered": ["publisher.example.com", "get.example.com"],
    "domain_evidence": {"publisher.example.com": "sellerUrl from iTunes lookup"}
  },
  "phase_0_5": {
    "approved_at": "ISO-8601",
    "keywords_approved": ["..."]
  },
  "phase_1": {
    "iterations": [
      {
        "iteration": 1,
        "search_seeds": {
          "keywords": ["..."],
          "domains": ["..."],
          "brand_names": ["..."]
        },
        "ad_pages_flagged": [
          {
            "page_id": "1234567890",
            "page_name": "Brand Name",
            "page_url": "https://www.facebook.com/page-username",
            "view_all_url": "https://www.facebook.com/ads/library/?view_all_page_id=1234567890&active_status=all",
            "relevance": "related | candidate",
            "reason": "First-glance ad-card destination -> apps.apple.com/.../id1234567890",
            "first_glance_destinations": ["apps.apple.com/...", "get.example.com/..."]
          }
        ]
      }
    ]
  },
  "phase_1_5": {
    "approved_at": "ISO-8601",
    "approved_page_ids": ["..."]
  },
  "phase_2": {
    "iterations": [
      {
        "iteration": 1,
        "ad_pages_deep_scraped": [
          {
            "page_id": "1234567890",
            "fb_ui_active_ads_count": 12,
            "script_active_ads_count": 12,
            "last_ad_launched": "2026-05-10",
            "ad_types": "both",
            "status": "Active",
            "ads": [
              {
                "ad_archive_id": "...",
                "active": true,
                "start_date": "2026-04-22",
                "end_date": null,
                "destination_url_resolved": "https://example.com/get",
                "destination_kind": "w2w | app",
                "variant_param": "cohort",
                "variant_value": "woofz22_v4"
              }
            ]
          }
        ],
        "funnels": [
          {
            "url": "https://example.com/get",
            "hosting_domain": "example.com",
            "status": "Active",
            "first_seen": "2026-04-22",
            "last_seen": "2026-05-12",
            "ad_pages_seen_on": ["1234567890"],
            "evidence_ad_ids": ["..."]
          }
        ],
        "new_domains_discovered": ["newdomain.com"]
      }
    ]
  },
  "phase_3": {
    "completed_at": "ISO-8601",
    "tech_stack": [
      {
        "funnel_url": "https://example.com/get",
        "builder": "Funnelish",
        "analytics": ["GA4", "Meta Pixel"],
        "payments": ["Stripe.js"],
        "ab_testing": [],
        "email_capture": ["Klaviyo"],
        "tag_manager": "GTM-XXXXXXX",
        "hosting_cdn": ["Cloudflare"],
        "other_notable_scripts": ["..."],
        "notes": "..."
      }
    ]
  },
  "phase_4": {
    "completed_at": "ISO-8601",
    "files_written": ["./calm-2026-05-13-report.md", "./calm-2026-05-13-funnels.csv", "..."]
  }
}
```

When a phase completes, write its block. When a phase fails partway, write what you have plus a `partial: true` marker so the next run can resume.

---

## Resume vs. start-over check (before any phase runs)

1. Compute the proposed `<slug>` from the input. For app input, you need to first call `scripts/lookup_app.py` to get `trackName`. For funnel-URL input that hasn't been resolved yet, use `unlinked-<host>` as a temporary slug.
2. If `<slug>-state.json` exists in CWD:
   - Read it. Note the most-recent `*_completed_at` timestamp.
   - If less than 24h old: ask the user — "I found existing state from `<timestamp>`. Resume from `<next pending phase>`, or start over?" Wait for reply.
   - If older than 24h: tell the user the file exists and is stale, default to start-over but offer resume.
3. If no state file exists: proceed to Phase -1 (funnel URL) or Phase 0 (app input).

---

## Phase -1 — Funnel-URL input resolution (only when input is a funnel URL)

Goal: try to link the funnel to an App Store app. If linking succeeds, switch to app-link mode. If it fails, switch to unlinked-funnel mode and continue.

1. **Fetch the funnel page** via `WebFetch` (or `curl -L`). Capture: page title, response headers (note CDN), and the full HTML. Save the HTML to `<temp>/phase_-1_funnel.html`.
2. **Find the ToU and Privacy Policy links.** Look for `<a>` text matching `terms`, `terms of (use|service)`, `privacy (policy|notice)`, `legal`, `imprint`. Also check footer.
3. **Fetch ToU and Privacy Policy.** Extract:
   - Legal entity name (look for patterns like "operated by", "owned by", "© <YEAR> <NAME>", "<NAME> is responsible for"). Save the literal quoted text as evidence.
   - Contact / support email.
   - Any company address.
   - Any links to `apps.apple.com/...` or `play.google.com/...` — these are gold; if present, jump to step 6 with that direct app link.
4. **Look for App Store / Play Store links anywhere on the funnel page or its checkout/thank-you/footer.** Patterns: `apps.apple.com/<cc>/app/...`, `play.google.com/store/apps/details?id=...`. If found, jump to step 6.
5. **Search iTunes for the legal entity name** using `scripts/lookup_app.py --search "<entity>"`. The script searches `https://itunes.apple.com/search?term=...&entity=software`. Show the user the top 5 candidates with: trackName, sellerName, primaryGenreName, trackViewUrl. Ask them to pick the right one (or say "none"). Wait for the user reply.
6. **If an app was identified** (steps 3, 4, or 5):
   - Set `state.app.linked = true` and populate from the iTunes lookup result.
   - Compute the proper `<app-slug>` and **rename the temp state file** from `unlinked-<host>-state.json` to `<app-slug>-state.json`.
   - Proceed to Phase 0.
7. **If no app was identified after step 5**:
   - Set `state.app.linked = false` and `state.app.host = <funnel hostname>`.
   - Use entity name (or hostname) as the brand name throughout.
   - Proceed to Phase 0 in unlinked-funnel mode. Still extract keywords and domains; just from the funnel page and ToU instead of an App Store listing.

---

## Phase 0 — App metadata, keywords, related domains

This phase has two tasks. Do them sequentially (Task A depends on the iTunes lookup; Task B uses both the iTunes data and Task A's keywords as input to web search).

### Phase 0 / Task A — Keyword extraction

1. **Look up the app.** If `state.app.track_id` is set, call `python scripts/lookup_app.py --id <track_id>`. Otherwise, if `state.app.bundle_id` is set, call `--bundleId`. Save the full response into `state.app`.
2. **For unlinked-funnel mode**, skip step 1 — use the funnel page title + headings + ToU as the source text.
3. **Extract candidate keywords.** Read the app's `trackName`, `trackCensoredName`, `description`, and `releaseNotes` (or the funnel-page text in unlinked mode). Produce a list of:
   - Brand / app names (the literal product name, plus any alternative spellings or sub-brand names you see).
   - Distinguishing product nouns (e.g., "fasting tracker", "sleep meditation", "language tutor"). Avoid generic words like "app", "premium", "subscription".
   - The 3–5 most distinctive feature phrases that appear in the description (e.g., "intermittent fasting plans", "AI workout coach"). Avoid marketing fluff.
   - Any explicit programs / methods / proprietary system names mentioned in the description.
4. **De-duplicate** and lowercase the list. Aim for 8–15 keywords. Fewer is OK if the app is narrow; more is OK if it's broad.
5. **Save** to `state.phase_0.keywords_proposed`.

### Phase 0 / Cross-task feedback — keywords from domains

After both Task A and Task B run, do one more pass before the Phase 0.5 gate:

- For each domain in `state.phase_0.domains_discovered`, inspect the hostname + first path segment for niche-revealing tokens (e.g., `brage3.cognitivegrowth.net` → `brain age`; `iq.mental-impulse.com` → `iq test`; `meal.brandname.com` → `meal plan`). These are often distinguishing keywords that the App Store listing didn't surface.
- If you find any, propose them as additions to `keywords_proposed`. Mark them with a note like `(from domain inspection)` so the user can see why they were added at the Phase 0.5 gate.

This loop matters because the App Store listing reflects what marketers wrote for ASO, not the language they use for funnel slugs. The funnel slugs often reveal the actual product categories being tested.

### Phase 0 / Task B — Legal & domain discovery

1. **Read the legal/ToU fields** from the iTunes response (`sellerName`, `sellerUrl`) — these are usually authoritative.
2. **Fetch the privacy policy URL** if linked from the App Store listing's description (look in the description text for `privacy` URLs). Also fetch the seller's website (`sellerUrl`) home page.
3. **Extract domains** from those pages: any `<a href>` with a hostname not equal to common CDNs / social / app stores. Look specifically for:
   - The brand's main marketing site.
   - Any `get.<brand>`, `try.<brand>`, `<brand>-app.<tld>`, country-specific variants (`<brand>.de`, `<brand>.com.br`).
   - Domains in the ToU/Privacy text (operated by clauses often list multiple domains).
4. **Web-search** for additional related domains using `WebSearch`:
   - `"<seller_name>" site:facebook.com` — finds their FB Page.
   - `"<seller_name>" terms of use` — finds other domains in their ToU footprint.
   - `"<brand_name>" -site:apps.apple.com -site:play.google.com landing OR funnel OR onboarding` — funnel-style pages.
5. **Save** the deduplicated domain list to `state.phase_0.domains_discovered`. For each, record what evidence justified inclusion in `state.phase_0.domain_evidence`.

When both tasks are done, mark Phase 0 complete and move to the Phase 0.5 gate.

---

## Phase 0.5 — Keyword Confirmation Gate (HARD STOP)

1. Present the keyword list to the user as a numbered list. Also show the discovered domains as a separate list (so the user can prune those too).
2. Ask: *"Approve these keywords and domains? You can edit, remove, or add items. I'll wait for your explicit approval before starting the FB Ads Library sweep."*
3. **Wait.** Do not proceed until the user replies with approval (and any edits).
4. Save the final approved list to `state.phase_0_5.keywords_approved` and `state.phase_0_5.domains_approved`.

---

## Phase 1 — FB Ad Page discovery (broad search + relevance flagging)

**Read** `references/fb-ads-library.md` before this phase. Do not skip it — the FB UI has specifics this file doesn't repeat. In particular, read the "Critical: use the FB Ads Library Page search, not general Facebook Pages search" callout and the "Robust Page discovery" section. Iter-1 missed an entire advertiser Page because it used the wrong Page search.

1. **Verify Playwright MCP is available (Step 0b).** If not, save state and halt per SKILL.md Step 0b.
2. **Verify FB session — auth is mandatory, anonymous is NOT a fallback.**
   a. If `.auth/fb_session.json` exists and is <30 days old → notify the user, proceed.
   b. Else navigate to `facebook.com/ads/library/` and probe DOM for logged-in chrome
      (profile name visible, no "Log in" button in body, no login UI).
      - If logged in → notify "Using the active Playwright Chromium session; FB is logged in" and proceed.
      - If logged OUT → STOP. Open `facebook.com/login` in the visible Chromium window,
        tell the user: "Please log in to Facebook in the browser window I just opened,
        then reply 'logged in'." Wait for explicit user confirmation. Do NOT proceed
        with anonymous scraping even if Ads Library appears to load without login.
3. **Build the search seeds.** Combine:
   - Approved keywords from `state.phase_0_5.keywords_approved`.
   - Approved domains from `state.phase_0_5.domains_approved` (search each as a quoted string AND as the bare domain). **Caveat: FB Ads Library keyword search indexes by ad creative text, NOT by destination URL — so searching a bare domain like `brain-gain.app` rarely surfaces ads.** Domain searches are still worth including because the brand name often appears in ad creatives, but don't rely on domain-as-seed alone.
   - The brand name from `state.app.track_name` and (if different) the publisher name from `state.app.seller_name`.
   - **Angle-specific keywords for the app's niche.** This is critical for recall — brands run angle-specific advertiser Pages (e.g., a brain training app may have a "Master Your ADHD Mind" Page and an "Overcome Trauma" Page that don't include the brand name in their Page name or ads). Add the standard angle keywords for the app's primary genre:
     - **Brain training / cognitive / education**: `adhd`, `adhd brain`, `focus`, `anxiety`, `memory`, `trauma`, `archetype`, `personality`, `intelligence type`, `iq test`, `cognitive`, `brain age`, `dementia`, `mental fitness`
     - **Fasting / weight loss / nutrition**: `intermittent fasting`, `weight loss`, `metabolism`, `glp-1`, `psychology of eating`, `binge eating`, `meal plan`, `body type`, `food sensitivity`
     - **Mental health / therapy / self-help**: `anxiety`, `depression`, `attachment style`, `trauma`, `inner child`, `cbt`, `manifesting`, `relationship type`, `boundaries`
     - **Sleep / meditation / mindfulness**: `sleep tracker`, `insomnia`, `stress`, `meditation`, `breathwork`, `chronotype`
     - **Language learning**: `learn language`, `polyglot`, `accent`, `language type`
     - For other niches, generate angle keywords from psychographic adjacencies — what emotional state / problem / identity does the app appeal to?
   - **Curate the angle list to 5–10 most-relevant terms** for the specific app. Don't try every angle in the list — pick the ones the app actually targets (from its description / screenshots / app reviews).

   Document the FINAL seed list (keywords + angle keywords + domains + brand names) in `state.phase_1.iterations[<n>].search_seeds` for transparency at the Phase 1.5 gate.
4. **For each seed, do an Ads Library Page search** using the URL in `fb-ads-library.md` § Two URL patterns. Read each result list: extract Page ID, Page name, Page URL. **If the URL appears to return ad cards instead of Page cards, follow the fallback strategies in `fb-ads-library.md` § Robust Page discovery — do not give up after one URL.**
5. **De-duplicate** by Page ID. Build the candidate Page set.
6. **Enumerate every candidate Page — do not stop at the first match.** Brands routinely have 3–8 Pages. For each one:
   1. Verify the Page is live (per `fb-ads-library.md` § Verify a Page is live before flagging).
   2. Open its ad library at `https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&view_all_page_id=<page_id>`.
   3. Scroll the page enough that all currently-active and recent ads are loaded.
   4. Collect the **first-glance destination URLs** visible in each ad card (no clicks required; the destination domain is shown in the card link preview).
7. **Apply the relevance rule** to each Page:
   - **Related** — at least one ad on the Page has a destination URL pointing to `apps.apple.com/.../<state.app.track_id>` OR `play.google.com/.../<state.app.bundle_id>` OR a host already in `state.phase_0_5.domains_approved` OR exact-match to the funnel-URL host (in unlinked-funnel mode). Deep-link redirectors (`*.onelink.me`, `*.app.link`, `*.go.link`, `*.adj.st`, `*.smart.link`) count as `apps.apple.com`-equivalent — they are app-install links.
   - **Candidate** — no direct match yet, but at least one destination URL points to a host whose name closely resembles the brand/keywords and looks like a W2W funnel pattern (e.g., `get-<brandish>.com`, `try.<brandish>.app`). Document the reason.
   - **Reject** — no relevant destination found AND the Page's name/bio doesn't match the brand. Do not write to state.
8. **Write** the flagged Pages to `state.phase_1.iterations[<n>].ad_pages_flagged`. Include the `first_glance_destinations` array so the next phase has context, plus the live-verification result.
9. **Empty-Phase-1 guard.** If zero Pages are flagged:
   - Do NOT proceed to Phase 1.5 silently. Stop and report to the user: "Phase 1 found zero relevant Pages from the approved seeds. Options: (a) expand the seed list with new keywords/domains, (b) try alternate Page-search strategies in `fb-ads-library.md`, (c) accept the negative finding and skip to Phase 4 to render a 'no advertiser activity found' report."
   - Wait for the user's choice. Their decision is part of the audit.
10. Move to Phase 1.5 gate (only on the FIRST iteration of Phase 1; loop iterations skip the gate).

---

## Phase 1.5 — Candidate Pages Confirmation Gate (HARD STOP, first iteration only)

1. Present the full flagged list as a table with: Page name, Page URL, relevance flag, the one-line reason, and the first-glance destinations.
2. Ask: *"Approve this ad-page list? You can remove false positives, add Pages I missed, or change a Page's flag. I won't start scraping until you approve."*
3. **Wait** for explicit approval and apply edits.
4. Save approved Page IDs to `state.phase_1_5.approved_page_ids`. Continue to Phase 2.

If the loop sends control back to Phase 1, **do not** run the 1.5 gate again — go straight from Phase 1's flagging to Phase 2 with the newly-added Pages.

---

## Phase 2 — Deep ad scraping + funnel extraction + status classification

> **CRITICAL — read this first.** Phase 2 must do **TWO separate scrapes per Page**, not one combined. Iter-2 user feedback caught a real bug here: a single `active_status=all&start_date[min]=<today-90d>` scrape MISSES currently-active ads that started >90d ago but are still running. The 90-day start-date filter is a HISTORICAL filter, not a "currently active" filter. Always do active+historical separately.

For each approved Page (`state.phase_1_5.approved_page_ids` plus any added by loop iterations):

### Step 2.A — Count currently-active ads

1. **Navigate** to `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&view_all_page_id=<page_id>` (no date filter).
2. **Read the FB UI's count from page text**. Use `browser_evaluate` to match these patterns in `document.body.innerText`:
   - `~\s*(\d+(?:,\d{3})*)\s+results` — most common (e.g., `~1,900 results`)
   - `About\s+(\d+(?:,\d{3})*)\s+(?:results|ad)`
   - `(\d+(?:,\d{3})*)\s+ads?\s+match`
   - Or the explicit message `No ads match your search criteria` / `This advertiser isn't running ads` → count is 0
3. Save as `fb_ui_active_ads_count`. **Every ad visible under `active_status=active` IS active by construction** — do not try to per-card detect "Active" badges (the badge sits in a sibling element to the Library-ID container and per-card detection is unreliable).
4. Scroll a few times and extract destination URLs to learn what funnels the ACTIVE ads point to. Build the per-Page `active_destination_distribution` map.

### Step 2.B — Collect historical context (last 90 days)

1. **Navigate** to `https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&start_date[min]=<today-90d>&view_all_page_id=<page_id>`. Scroll to load every ad card in that date window.
3. **Iterate every ad card and extract**: `ad_archive_id`, `start_date`, `end_date` (if available), the destination URL shown in the link preview. Unwrap `l.facebook.com/l.php?u=...` redirects.
   - **Do NOT try to read the per-card Active/Inactive badge here.** That badge is rendered in a sibling element to the Library-ID container, and walking-up-to-find-card heuristics often miss it. Instead: the Step 2.A scrape with `active_status=active` already gave you the active ads; treat ads from Step 2.B as the historical superset.
4. **Resolve destination URLs**: for any URL not on `apps.apple.com` or `play.google.com`, follow redirects with `curl -sIL --max-redirs 10 -o /dev/null -w "%{url_effective}" <url>` to get the final landed URL. Save the resolved URL.
5. **Tag each ad** with `destination_kind`:
   - `app` if the resolved host is `apps.apple.com` or `play.google.com`, OR if the host is a known app-install deep-link redirector (`*.onelink.me`, `*.app.link`, `*.go.link`, `*.adj.st`, `*.smart.link`, `app.adjust.com`). These are not funnels — they deep-link to the app store.
   - `w2w` otherwise (a real web destination — the funnel).
6. **Compute the Page's ad_types column**: `app` if all ads are app, `w2w` if all are w2w, `both` if mixed.
7. **Compute the Page's status**:
   - If `fb_ui_active_ads_count` from Step 2.A is `≥ 1` → **Active**
   - Else if Step 2.B returned any ads with `start_date` in the last 90 days → **Cold**
   - Else → for ad pages, **Cold** with `last_ad_launched = uncertain` and note "Page exists in Ads Library but no ads in 90-day window". (Funnels use a separate "No launches in last 90d" status — see status-classification.md.)
   - Save status + `script_active_ads_count` (from Step 2.A) + `last_ad_launched` (max start_date across 2.A + 2.B).
8. **Group ads into funnels, with variant detection.**

   a. **Initial pass**: group by `host + pathname` (ignoring query string).

   b. **Variant param detection**: within each group, scan ad destination URLs for
      recurring query params with multiple distinct values. Common variant param names:
      `cohort`, `funnel`, `variant`, `v`, `flow`, `version`, `experiment`, `bucket`.

   c. **If multiple values observed for a variant param**, run a "render probe":
      For each unique variant value, navigate Playwright to
      `https://<host><pathname>?<param>=<value>&lang=en`, wait 5–8 s for SPA hydration,
      then capture (via `browser_evaluate`):
        - post-render `location.pathname` (SPAs often rewrite to a step-specific slug)
        - first 5 visible h1/h2/h3 headings
        - first 600 chars of body text
      Optional: take screenshot for the audit trail.

      Decision rule:
        - If different variant values produce DIFFERENT post-render slugs OR
          DIFFERENT first headings → treat each as a SEPARATE funnel
          (one row per variant value in funnels.csv; the `url` field is the canonical
          `?<param>=<value>` URL).
        - If all variant values produce the SAME slug and SAME headline →
          keep them grouped under one funnel; list the variant values as
          a sub-field for evidence.

   d. **Beforeunload-dialog hazard**: FB Pixel and similar trackers install a
      `beforeunload` listener after SPA hydration. Subsequent `browser_evaluate`
      calls fail with "Tool does not handle the modal state". Mitigations:
        - Call `browser_handle_dialog(accept=true)` after each navigation,
          OR
        - Navigate to `about:blank` between variant probes to clear page state.

   e. For each funnel (now possibly several per host):
   - `hosting_domain` is the registrable domain of the URL (use `tldextract` in `scripts/` if helpful — but a simple split on `.` is usually fine for known TLDs).
   - `ad_pages_seen_on` is the list of Page IDs whose ads landed here.
   - `first_seen` is the earliest `start_date` across all ads landing here; `last_seen` is the latest non-null end_date or scrape_date if active.
   - `status` per the status reference.
   - `evidence_ad_ids` is the list of `ad_archive_id`s landing here (cap at 25 — used for sourcing, not exhaustive).

      Per-variant first_seen/last_seen requires either filtering captured ad records by variant value OR scraping each variant URL separately — note `uncertain` for the cells you can't isolate.
9. **Identify new domains**: any `hosting_domain` in this iteration that is NOT in `state.phase_0_5.domains_approved` AND was NOT a seed used in Phase 1. Save as `new_domains_discovered` for the iteration.

### Loop control

- If `new_domains_discovered` for this iteration is non-empty AND iteration count is `< 5`:
  - Add the new domains to the search seeds (for THIS run only; do not pollute the approved list).
  - Restart Phase 1 with the expanded seeds.
- Else:
  - Mark Phase 2 complete and proceed to Phase 3.

### No-funnels terminal case

If every Phase 2 iteration completes with 0 ads (every approved Page has 0 ads, both currently active and in the 90-day window): the audit's mechanical answer is "no funnels via ads."

Do **not** silently produce an empty report. Instead:

1. Carry every domain from `state.phase_0_5.domains_approved` (the Phase 0 controlled domains the user approved) into the funnels table as rows with `status = uncertain` and `notes = "Domain known from app's ToU / seller URL / web search but never observed in any scraped ad."` This is the tie-breaker from `references/status-classification.md` and it makes the report informative rather than blank.
2. Each ad page still gets its row with `script_active_ads_count = 0`, `status = Cold`, `last_ad_launched = uncertain`, and a clear note like `"Page exists with N followers. Ads Library returns 'no ads in selected country/category' across all parameters."`.
3. Run Phase 3 (tech-stack) on the `uncertain` funnel rows — they still have tech stacks the user might find useful.
4. The Phase 4 report's Summary section explicitly states: "The audit found NO Facebook ads on any approved advertiser Page in the 90-day window. The funnels listed below are domains known from the app's legal/seller footprint, not from observed ads." Keep it observational.

---

## Phase 3 — Tech-stack detection (per-funnel run, aggregated in the report)

For each unique funnel URL collected across all Phase 2 iterations:

1. Call `python scripts/detect_tech_stack.py <funnel_url>`.
2. Parse the JSON output. Save the row into `state.phase_3.tech_stack` (per-funnel, in state — this is the raw data).
3. If the script returns `error`, capture the error and write `uncertain` for all fields with the error in the notes column. Move on — do not block the report on a single funnel failing detection.

**Important: at Phase 4 render time, you will COLLAPSE these per-funnel rows by unique stack signature for the report.** The per-funnel detail stays in `state.phase_3.tech_stack` (audit trail), but the report's tech-stack table groups funnels sharing the same (builder, analytics-set, payments-set, ab_testing-set, email_capture-set, tag_manager, hosting_cdn-set). See `references/report-template.md` § Tech stack for grouping rules.

`references/tech-stack-detection.md` lists which signatures the script checks and why. If a funnel is clearly built on something not in the script's coverage, write the observation into the `other_notable_scripts` column manually.

---

## Phase 4 — Render report + CSVs

1. Read the full state.
2. Compute the slug and date prefix. Filenames:
   - `<slug>-<YYYY-MM-DD>-report.md`
   - `<slug>-<YYYY-MM-DD>-funnels.csv`
   - `<slug>-<YYYY-MM-DD>-ad-pages.csv`

   No separate CSV is produced for the tech stack — it lives in the report's markdown tables only. Per-funnel tech-stack data remains in `state.phase_3.tech_stack` for the audit trail.
3. Render the markdown report per `references/report-template.md` — strict structure, observation-only, `uncertain` for unsourced cells. The report includes the tech-stack tables inline (one per unique stack signature).
4. Write the two CSVs from the funnels + ad-pages tables (one row per record, headers in row 1, UTF-8, double-quoted strings, ISO dates).
5. Save the file paths to `state.phase_4.files_written`.
6. Print a short summary to the user: file paths created, # funnels by status, # ad pages by status, iterations run. Do **not** include any analysis or recommendation — point them to the report.

End of workflow.
