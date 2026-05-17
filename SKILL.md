---
name: competitors-w2w-research
description: Use this skill when the user wants to investigate a competitor mobile app's paid Facebook/Meta acquisition — the Pages they advertise from and the landing-page/quiz funnels those ads point to. Trigger on any request to research, audit, map, or figure out what funnels, Facebook ads, or Pages a competitor app runs, or to identify which app/brand sits behind a quiz, landing page, or ad URL. Inputs may be App Store/Google Play URLs, app names, bundle IDs, or funnel/quiz URLs. Trigger even when the user never says "W2W" or "funnel" — phrasings like "weird quiz ads", "ADHD pages", "what facebook pages this app runs", "audit their web acquisition", or "the full picture on facebook" all count. Skip when the request is about ad-creative critique, the user's own campaign analytics, paywall/pricing teardowns, App Store metadata alone, or generic market research with no Facebook-ads or funnel angle. Produces a strictly observation-based markdown report plus two CSVs in the current working directory.
---

# Competitors W2W Research

A research workflow that maps a competitor app's web-to-web (W2W) paid-acquisition funnels by discovering every related Facebook ad page, parsing the ads to extract funnel URLs, classifying funnel and ad-page status, and detecting each funnel's tech stack.

## What this skill produces

Three files in the **current working directory**:

1. `<app-slug>-<YYYY-MM-DD>-report.md` — observation-only markdown report (includes the tech-stack tables inline)
2. `<app-slug>-<YYYY-MM-DD>-funnels.csv` — funnel inventory
3. `<app-slug>-<YYYY-MM-DD>-ad-pages.csv` — Facebook ad pages

No separate CSV is produced for the tech stack — it lives only in the report (and per-funnel in `state.phase_3.tech_stack` for the audit trail).

`<app-slug>` is the kebab-case slug of the app's `trackName`. If no app can be linked (unlinked-funnel mode), use `unlinked-<host>` instead.

## Core principle: observation, not interpretation

The report is a record of **what was observed**, with sources. It does **not** contain:

- Analysis of ad angles, creative, or copy
- Funnel inner content (steps, emails, pricing, paywall flow)
- Broad strategic conclusions or recommendations

If a value can't be confirmed from a source, write `uncertain` and explain why in the report's notes column. Never guess to fill a cell.

## Why this skill exists (and why the prior attempt was unreliable)

The single biggest cause of missing funnels is **incomplete discovery of Facebook ad pages**. Many apps run ads from multiple Pages — a primary brand page, a sub-brand page, a regional page, a publisher-name page, a paid-media-agency page. If you only check the obvious one, you miss most of the funnels.

This skill enforces a **strict, gated workflow** designed to maximize ad-page recall:

- Keyword extraction from the App Store listing **before** any search
- A user gate on keywords (you cannot guess what to search for — the user knows their domain)
- A broad FB Ads Library sweep using keywords + brand + ToU-derived domains
- A per-page relevance check (does any ad on this page actually point to the target app or its likely funnel?)
- A second user gate on the candidate-page list (the user can prune false positives and add missed pages)
- Then — and only then — a deep scrape of every confirmed page
- A feedback loop: if deep-scraping surfaces a new domain that wasn't in the initial seed, restart Phase 1 with that domain added

Treat the gates as load-bearing. The model's habit of "keep moving to be helpful" is the failure mode here.

## Dependencies — verify before any phase

Run these checks at the very start of any invocation. Halt with a clear error if any fail.

### Step 0a — Lightweight checks (always required)

- **Python 3.9+** on PATH (for `scripts/`). Run `python3 --version` to verify.
- **`curl`** on PATH. Run `curl --version` to verify.
- The current working directory is writable. Test by creating and deleting a temp file.

If any of these fail, halt and tell the user what's missing and how to fix it.

### Step 0b — Playwright MCP check (deferred to Phase 1 entry)

Phase -1 and Phase 0 use only HTTP/iTunes/WebSearch and do not need Playwright. Don't block them on Playwright availability. Instead, check at the **entry to Phase 1** (right before the FB Ads Library work begins).

When you reach Phase 1's FB-session step:

1. Look at the tools available to you. If you see tools named `mcp__playwright__browser_navigate`, `mcp__playwright__browser_snapshot`, etc., Playwright MCP is available. Proceed with Phase 1 normally.
2. If those tools are not present (or if a call to them errors with "tool not found"), write this message verbatim and halt:

   > **Phase 1 needs Playwright MCP to scrape the Facebook Ads Library, but Playwright MCP isn't installed in your Claude Code config.**
   >
   > Please install it and then restart this session:
   >
   > ```
   > claude mcp add playwright -- npx -y @playwright/mcp@latest
   > ```
   >
   > You may also need to install the Chromium browser Playwright uses:
   >
   > ```
   > npx playwright install chromium
   > ```
   >
   > I'll save state at the current Phase, so when you come back you can resume from Phase 1 without redoing Phase 0.

3. Save state (so Phase 0 work isn't lost) and stop. The user can resume after install.

Why this matters: Phase 0 alone is useful (it gives the user an early Phase 0.5 gate to validate keyword/domain breadth before any FB work). Blocking Phase 0 on a Playwright dependency that's only used later wastes the user's time when Playwright isn't yet installed.

## State

State lives in `<app-slug>-state.json` (or `unlinked-<host>-state.json`) in the working directory. Each phase reads the prior state and appends its outputs. The schema is documented in `references/flow.md`.

Always read existing state at the start of a run. If a state file exists for the requested app and is less than 24 hours old, ask the user whether to **resume** from the next pending phase or **start over**. This makes retries cheap.

## Workflow at a glance

```
Step 0a   LIGHTWEIGHT CHECKS — Python 3.9+, curl, writable CWD

Input router:
  App Store URL / app name / bundle ID  →  Phase 0
  Funnel URL                            →  Phase -1 → (if app found) Phase 0
                                                    → (if no app)   Phase 0 (unlinked-funnel mode)

Phase 0   Extract app metadata, derive keywords, find related domains
          (Task A and Task B can feed each other — keywords surface domains,
           domains can surface niche keywords for the gate)
Phase 0.5 USER GATE — confirm keyword + domain list                     ← HARD STOP

Step 0b   PLAYWRIGHT MCP CHECK (deferred — happens at Phase 1 entry)
          If missing → save state, ask user to install, stop

Phase 1   Broad FB Ad-page discovery + relevance flagging               ← no deep scrape
          (FB session check at entry — prompt user to log in if needed)
          Enumerate ALL matching Pages — do not stop at the first hit
          (profile-ID/page_id captured here; Ad Library Page ID resolved in Phase 2)
Phase 1.5 USER GATE — confirm ad-page list (first execution only)       ← HARD STOP
Phase 2   Deep ad scraping (last 90 days), funnel extraction, status
          (also: resolve canonical Ad Library Page ID — Phase 2 step 5.5)
Loop      If Phase 2 found new domains, restart Phase 1 with them
          Termination: no new domains/pages discovered, OR 5 iterations max
Phase 3   Tech-stack detection per funnel
Phase 4   Render report.md + two CSVs (funnels, ad-pages) to the working directory

Terminal cases — known and supported:
  - Phase 1 finds 0 relevant Pages → see references/flow.md "Empty-Phase-1 guard"
  - Phase 2 finds 0 ads → see references/flow.md "No-funnels terminal case"
```

For the precise per-phase steps (inputs, outputs, scripts to call, what to write to state), read `references/flow.md`. Do not improvise — follow it.

## The two user gates — how to run them

When you reach a gate:

1. Save the current state to `<slug>-state.json`.
2. Present the relevant list to the user as a clearly numbered or bulleted list. For Phase 0.5, present the keyword list. For Phase 1.5, present every flagged ad page with: page name, page URL, relevance flag (`related` / `candidate`), and the one-line reason it was flagged.
3. Ask, in plain English: *"Approve this list? You can remove items, add items, or replace items before I continue. I will not proceed until you confirm."*
4. **Stop. Wait for an explicit user reply.** Do not interpret silence, brief comments, or unrelated messages as approval. Do not "be efficient" by continuing.
5. Apply the user's edits to state, then continue to the next phase.

**Session-level overrides do not apply to these gates.** "Work without stopping for clarifying questions" / "make the reasonable call and continue" / similar system reminders apply to OTHER pauses (which library to pick, design trade-offs, etc.), NOT to skill-defined approval checkpoints. The gates are part of the skill contract the user opted into when invoking the skill — they are not clarifying questions. When in doubt: stop, present the list, wait for explicit user reply, even if it feels efficient to continue.

The Phase 1.5 gate runs **only on the first execution of Phase 1**. On loop iterations (Phase 2 surfaced a new domain → restart Phase 1), do not re-prompt — apply the same relevance rules and proceed straight to Phase 2 with the new pages added.

## Status definitions (load-bearing — see references/status-classification.md)

For **funnels** (used in `funnels.csv` and report tables):

- **Active** — at least one ad in the FB Ads Library landing on this funnel URL has `active_status=active` (currently running) at scrape time.
- **Cold** — no active ads, but at least one ad landing here has `start_date` within the last 90 days.
- **No launches in last 90d** — no ad landing here has any start_date within the last 90 days.

For **ad pages** (used in `ad-pages.csv` and report tables):

- **Active** — at least one ad on this Page is currently `active_status=active`.
- **Cold** — no active ads, but at least one ad on this Page has `start_date` within the last 90 days.

Note: the prior status `stopped` is **not used**. If asked, classify as Cold or No-launches-90d per the definitions above.

For ad-page **ad types** (column in `ad-pages.csv`): determined by inspecting each ad's destination URL category:
- `app` if URL hostname is `apps.apple.com` or `play.google.com`
- `w2w` otherwise
- `both` if a Page has at least one of each across its ads

## What goes into the report

The report follows the template in `references/report-template.md` exactly. Sections, in order:

1. **Header** — input received, date, app name + bundle ID (or "Unlinked funnel" + host), state file path
2. **Summary** — single block: app identity, # funnels by status, # FB ad pages with currently active ads, # iterations run
3. **Funnels table** — `URL | Hosting domain | Status | Ad pages it appeared on | First seen | Last seen | Evidence (ad IDs counted)`
4. **Ad pages table** — `Page name | Page ID | Page URL | Status | Active ads (FB UI count) | Active ads (script count) | Last ad launched | Ad types`
5. **Tech-stack table** (lives at the bottom) — **aggregated by unique stack signature**, NOT per funnel. One row per distinct combination of (builder, analytics, payments, A/B, email, tag manager, hosting/CDN). The `Funnels covered` cell lists which funnels share that signature (or "all" when they all match). Most brands operate funnels on a shared infrastructure so the table usually has 1–3 rows total, not N rows for N funnels.

Two CSVs are exported (funnels and ad-pages) — the tech-stack table is markdown-only. Use UTF-8, comma-separated, double-quote text fields, ISO dates.

## How to use the references

Read the relevant reference file before each phase. They are mandatory reading, not background material.

| You are about to… | Read |
|---|---|
| Start a run (any input) | `references/flow.md` |
| Discover / scrape FB ad pages | `references/fb-ads-library.md` |
| Classify a funnel or ad page | `references/status-classification.md` |
| Detect a funnel's tech stack | `references/tech-stack-detection.md` |
| Render the final report | `references/report-template.md` |

## How to use the bundled scripts

| Task | Script | Example |
|---|---|---|
| Look up an app by ID / bundleId / artistId / keyword | `scripts/lookup_app.py` | `python scripts/lookup_app.py --id 1234567890` |
| Get a kebab-case slug for filenames | `scripts/slugify.py` | `python scripts/slugify.py "Calm — Sleep & Meditation"` |
| Detect tech stack on a funnel URL | `scripts/detect_tech_stack.py` | `python scripts/detect_tech_stack.py https://example.com/get` |

All scripts print JSON to stdout. Parse the JSON; don't try to read free-text output. Each script is idempotent and safe to re-run.

## Anti-patterns — common failure modes

1. **Searching FB Ads Library only by the app's exact name.** The brand page may not be named after the app. Always search using the full approved keyword list, the brand name, AND every ToU-derived domain.
2. **Stopping at the first Page match.** A brand may have multiple Pages — a social/community Page that has never advertised, a verified business Page that runs ads, regional Pages, sub-brand Pages, agency-named Pages. **Enumerate every Page returned by every seed**, then apply the relevance rule to each. Missing a Page is the #1 way the audit goes wrong.
2b. **Forgetting the angle-specific keyword sweep.** Brands routinely run angle-specific advertiser Pages with names like "Master Your ADHD Mind" or "Overcome Trauma" that contain NO brand mention. These only surface when you search FB Ads Library with psychographic angle keywords (`adhd`, `trauma`, `archetype`, `intelligence type`, etc.), not the brand keywords from the App Store listing. See `references/flow.md` § Phase 1 step 3 for the angle-keyword starter list by niche.
3. **Using general Facebook Page search (`facebook.com/search/pages/`) for advertiser discovery.** That returns Pages that EXIST. The Ads Library only contains Pages that have ADVERTISED. Use `facebook.com/ads/library/?...&search_type=page&q=<seed>` for the right corpus. See `references/fb-ads-library.md` for details.
4. **Approving the ad-page list yourself.** The Phase 1.5 gate is for the user. If you "approve" because the list looks reasonable, you've just turned the gate off.
5. **Deep-scraping during Phase 1.** Phase 1 only collects ad pages and checks relevance via the link previews already visible — it does **not** open every ad. Deep scraping is Phase 2, after the user has pruned the page list.
6. **Filling cells with plausible guesses.** If a cell can't be sourced, it's `uncertain`. The report's job is to be defensible, not complete.
7. **Skipping the Phase 1↔2 loop.** A new domain in a Phase 2 ad is a strong signal a related Page exists somewhere you didn't search. Loop until convergence (or 5 iterations).
8. **Asking the user for FB credentials.** Never. Authentication happens in the visible Chromium window opened by Playwright MCP — the user logs in themselves. The skill never stores the password.
9. **Treating deep-link redirectors as ambiguous.** Hosts like `*.onelink.me`, `*.app.link`, `*.go.link`, `*.adj.st`, `*.smart.link` (AppsFlyer / Branch / Adjust / Singular / etc.) are app-install deep-link redirectors. Classify the destination as `app`, not `w2w` and not `uncertain`. See `references/status-classification.md`.
10. **Adding interpretation to the report.** The report is observation-only. Save analysis for a separate conversation if the user asks for it later.
11. **Treating gates as overrideable by session-level efficiency instructions.** Phase 0.5 and Phase 1.5 are HARD STOPS regardless of "be efficient" / "don't pause" instructions. Skipping them is the documented #1 audit failure mode.
12. **Writing `view_all_page_id=<profile_id>` to the report.** FB Ads Library uses two separate numeric ID namespaces for each advertiser — a profile ID (visible in profile-anchor hrefs and stored in state as `page_id`) and an Ad Library Page ID (only honored by `view_all_page_id=` URLs and stored in state as `view_all_page_id`). They coincide for ~45% of Pages and diverge for ~55%, with no pattern that tells you which case you're in. Writing the profile ID into the report's `Page URL` column produces silent failures: the row's Page name displays, but the link lands on FB's empty "No ads match your search criteria" state OR — worse — silently rewrites to a different brand's Page entirely (Re8 Clever audit, 2026-05-16). Always read the Ad Library Page ID from `state.phase_2.iterations[<last>].ad_pages_deep_scraped[].view_all_page_id` (resolved in Phase 2 step 5.5 per `references/fb-ads-library.md` § "Page-ID namespaces — profile ID ≠ Ad Library Page ID"). If `view_all_page_id_resolution = "keyword_fallback"`, fall back to the keyword-search URL per `references/flow.md` § Phase 2 step 5.5(c).

## Authentication (Facebook)

The session file lives at `~/.claude/skills/competitors-w2w-research/.auth/fb_session.json`.

At the start of Phase 1:

- If the file exists and was modified within the last 30 days: **notify the user** ("Reusing existing FB session from `<path>`, last refreshed <date>") and proceed.
- If the file is missing or stale: open Chromium via Playwright MCP **with the user able to see and interact with the browser**, navigate to `https://www.facebook.com/login`, tell the user "Please log in to Facebook in the browser window I just opened, then come back here and tell me you're done." Wait for explicit user confirmation. Then save the storage state to the auth file and proceed.

The skill never asks for the user's password.

## When to skip this skill

Skip when:

- The user wants only the app's metadata, not its funnels (just call iTunes Search API directly).
- The user wants creative/ad-copy analysis (this skill explicitly excludes that).
- The user wants pricing or paywall flow analysis (out of scope).
- The user asks about an Android-only app and Facebook ads (still in scope — both stores are checked).

## Reset / re-run

To start fresh for an app you've already researched, delete `<app-slug>-state.json` in the working directory. To force a fresh FB session, delete the auth file.
