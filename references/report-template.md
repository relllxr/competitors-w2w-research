# Report Template

The exact structure of `<app-slug>-<YYYY-MM-DD>-report.md`. Follow this template strictly. Do not add interpretive sections (analysis, recommendations, ad-creative commentary, funnel inner content).

`uncertain` is a valid cell value. Use it whenever a value can't be sourced.

## Template (use literal markdown below; replace bracketed placeholders)

```markdown
# Competitors W2W Research Report — [App Name or "Unlinked funnel: <host>"]

- **Input received**: `[the literal string the user pasted]`
- **Input type**: [app_store_url | bundle_id | app_name | funnel_url]
- **Run date**: [YYYY-MM-DD]
- **State file**: `[./<slug>-state.json]`
- **App linked**: [Yes — id <track_id>, bundle `<bundle_id>` | No — funnel research only]

## Summary

- **App**: [trackName] ([bundle_id]) — [primaryGenreName] by [sellerName]
  - Or: **Funnel host**: [<host>] — owner per ToU: [entity name or "uncertain"]
- **Funnels by status**:
  - Active: [N]
  - Cold: [N]
  - No launches in last 90d: [N]
- **Facebook ad pages with currently active ads**: [N]
- **Total ad pages found**: [N] ([N] Active + [N] Cold)
- **Iterations of Phase 1↔2 loop**: [N]
- **Audit window**: last 90 days from [scrape ISO date]

## Funnels

**Totals**: Total funnels found [N]; active [X]; cold [Y]; no launches in last 90d [Z]; uncertain [U].

| URL | Hosting domain | Status | Ad pages seen on | First seen | Last seen | Evidence (ad IDs) |
|---|---|---|---|---|---|---|
| [funnel url] | [registrable domain] | [Active/Cold/No launches in last 90d/uncertain] | [Page name (id) — comma-separated] | [YYYY-MM-DD] | [YYYY-MM-DD] | [up to 5 ad_archive_ids, comma-separated, ellipsis if more] |

(One row per unique funnel URL across all iterations. The totals line above counts the rows in this table — Total = sum of (active + cold + no-launches + uncertain). Omit the `uncertain` segment when count is 0.)

**Optional columns — only when variant detection fires** (per `flow.md` Phase 2 step 8c). When a hostname has multiple cohort/variant values that produce different post-render slugs or headlines, add these columns so each variant gets its own row:

- `Funnel slug` — the post-SPA-render `location.pathname` captured by the variant render probe (e.g., `/sex_22v4`, `/dog_age_woofz_ppp`).
- `Design family` — free-text classifier the auditor assigns to group variants by their funnel-design family (e.g., "gender-first", "age-first", "no-yelling angle").

If variant detection did not fire for any hostname in this run, omit these columns entirely — do not add empty ones.

## Facebook ad pages

**Totals**: Total pages [N]; active [X]; cold [Y]; uncertain [U].

| Page name | Page ID | Page URL | Status | Active ads (FB UI) | Active ads (script) | Last ad launched | Ad types | Notes |
|---|---|---|---|---|---|---|---|---|
| [page_name] | [page_id] | [page_url] | [Active/Cold/uncertain] | [count or uncertain] | [count] | [YYYY-MM-DD or uncertain] | [app/w2w/both/uncertain] | [empty or "FB UI vs script mismatch", "no ads in window", etc.] |

(One row per approved Page from Phase 1.5 plus any added by loop iterations. The totals line above counts the rows in this table — Total = sum of (active + cold + uncertain). Omit the `uncertain` segment when count is 0.)

**`Page URL`** — the full FB Ads Library Page-view URL filtered to active ads, sorted by total_impressions desc, country=ALL. Format:

```
https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&sort_data[direction]=desc&sort_data[mode]=total_impressions&view_all_page_id=<AD_LIBRARY_PAGE_ID>
```

**The `view_all_page_id` value MUST be the Ad Library Page ID, not the profile ID** — they are different numeric namespaces in FB. Read it from `state.phase_2.iterations[<last>].ad_pages_deep_scraped[].view_all_page_id` (resolved in `references/flow.md` § Phase 2 step 5.5). Do NOT substitute the legacy `page_id` field — that's the profile ID, and it produces silent failures (empty "No ads match" page or unrelated Page rendered). Background: `references/fb-ads-library.md` § "Page-ID namespaces — profile ID ≠ Ad Library Page ID".

If `view_all_page_id_resolution = "keyword_fallback"` for a Page (Phase 2 step 5.5 could not resolve the Ad Library Page ID), write the keyword-search fallback URL described in `references/flow.md` § Phase 2 step 5.5(c) into this column instead, and add to the row's `Notes` cell: `Page URL is a keyword-search fallback; Ad Library Page ID could not be resolved.`

Do NOT use the Page's vanity URL (e.g. `facebook.com/<brand>`) — the audit-quality link is the Ads Library URL that opens directly on that Page's ad inventory.

## Tech stack

Aggregated across all funnels — one **table per UNIQUE stack signature**. If funnels share the same builder + analytics + payments + hosting (etc.), they share one table. Per-funnel exceptions go into the `Notes` row. This keeps the report compact when (as is common) a brand operates many funnels on a shared infrastructure.

Each stack is rendered as a **two-column table** (param → value), NOT as a wide row. This is more readable when there are many params and the values are list-valued.

### Stack [A] — covers [N funnels: all | <comma-separated funnel URLs or shorthand>]

| Param | Value |
|---|---|
| Builder | [builder or custom or uncertain] |
| Analytics | [list or empty] |
| Payments | [list] |
| A/B testing | [list] |
| Email capture | [list] |
| Tag manager | [GTM-XXXXXXX or empty] |
| Hosting / CDN | [list] |
| Other notable scripts | [list] |
| Notes | [errors, per-funnel exceptions, caveats] |

(If there is only ONE unique stack across all funnels, render exactly one such table with the heading `### Stack — covers all N funnels`. If there are MULTIPLE unique stacks, render one `### Stack A`, `### Stack B`, … section per stack, each with its own two-column table. Letter the stacks A, B, C in descending order of how many funnels they cover.)

**How to group**: two funnels share a stack (and therefore a table) when these params all match exactly: Builder, Analytics list (set), Payments list (set), A/B testing list (set), Email capture list (set), Tag manager value, Hosting/CDN list (set). `Other notable scripts` and `Notes` are merged into a single cell per row.

**`uncertain` builder**: if the fetch failed (HTTP 5xx, DNS failure, Cloudflare challenge) for any funnel, those funnels go in a dedicated `uncertain` stack table regardless of detected hosting/CDN.

**List values**: render lists as comma-separated inline text in the Value column (e.g., `GA4, Meta Pixel, TikTok Pixel`). Empty list = empty cell.

---

*Generated by `competitors-w2w-research` skill. State and source data: `<slug>-state.json`. To regenerate, re-run the skill in this directory.*
```

## CSV outputs — column order

Only TWO CSVs are produced (funnels + ad-pages). The tech-stack table lives in the markdown report only — there is no `tech-stack.csv`.

Each CSV mirrors one of the tables above. Identical column order. Headers in row 1.

**`<slug>-<date>-funnels.csv`:**
```
url,hosting_domain,status,ad_pages_seen_on,first_seen,last_seen,evidence_ad_ids
```

For `ad_pages_seen_on` and `evidence_ad_ids`, join with `|` (pipe) inside the cell — comma would conflict with CSV. Quote the field.

**`<slug>-<date>-ad-pages.csv`:**
```
page_name,page_id,page_url,status,active_ads_fb_ui,active_ads_script,last_ad_launched,ad_types,notes
```

## Formatting rules

- All dates: ISO `YYYY-MM-DD`.
- Numeric counts: integers. If unknown, `uncertain`.
- URLs: keep full URL with scheme. No trailing whitespace.
- Empty lists: write `` (empty cell) in markdown, `""` (empty quoted string) in CSV.
- `uncertain` is one word, lowercase, in any text cell.
- Encode CSV as UTF-8, with `\r\n` line endings, RFC 4180 quoting (double-quotes around fields containing comma, quote, or newline; embedded quotes doubled).
- Page URLs in the Facebook ad pages table (and `ad-pages.csv`) MUST use the canonical FB Ads Library Page-view URL with `active_status=active`, `country=ALL`, `search_type=page`, `sort_data[direction]=desc`, `sort_data[mode]=total_impressions`, and `view_all_page_id=<AD_LIBRARY_PAGE_ID>`. The Page ID **must be the resolved `view_all_page_id` field** (`state.phase_2.iterations[<last>].ad_pages_deep_scraped[].view_all_page_id`) — do NOT write the legacy `page_id` (profile ID) value even if it appears to work for some Pages. Build this URL programmatically rather than copying whatever URL the search results listed. Background: `references/fb-ads-library.md` § "Page-ID namespaces — profile ID ≠ Ad Library Page ID".

## What NOT to add

- A "Recommendations" section.
- A "Key takeaways" section.
- Speculation about what the competitor is trying to do strategically.
- Pricing observations.
- Ad-copy or creative descriptions.
- Funnel content (form fields, paywall variants, etc.).

If the user asks for any of those, do it in a follow-up conversation. The report stays an observation.
