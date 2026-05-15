# Status Classification Rules

These are the only valid status values. Do not invent new ones. If a record cannot be classified, use `uncertain` and explain in the notes column — the user will fix it on review.

## For funnels

A funnel is a unique destination URL (post-redirect-resolution) that one or more ads land on.

| Status | Rule |
|---|---|
| **Active** | At least one ad in the scraped corpus that lands on this funnel URL has `active = true` (currently running in FB Ads Library) at the time of scrape. |
| **Cold** | No ads currently `active = true`, AND at least one ad has `start_date` within the last 90 days. |
| **No launches in last 90d** | Neither of the above. Every ad landing on this URL has `start_date` older than 90 days from the scrape date. |

Tie-breaking:
- If a funnel has BOTH currently-active ads AND old-start-date ads: **Active**. Status reflects the strongest current signal.
- If a funnel was discovered via Phase 2 but no ad on the scraped pages currently lands there (only inferred from older data): rely on `last_seen`. If `last_seen` is within 90d: **Cold**. Else: **No launches in last 90d**.
- If no ad-history evidence at all (funnel surfaced only via a domain in Phase 0 but never seen in ads): **uncertain** — write the funnel into the table with status `uncertain` and notes "domain known from ToU/seller URL but not seen in any scraped ad."

## For Facebook ad pages

| Status | Rule |
|---|---|
| **Active** | At least one ad on this Page has `active = true` at scrape time. |
| **Cold** | No ad on this Page is currently `active`, AND at least one ad has `start_date` within the last 90 days. |

If a Page was in the Phase 1 list but Phase 2 found ZERO ads on it (even after the 90-day window): this Page is genuinely dormant. Record it with status `Cold` and `script_active_ads_count = 0`, `last_ad_launched = uncertain`. Note in the report that the Page exists but ran nothing in the audit window.

The status `No launches in last 90d` is **not used for ad pages** — only for funnels. (Rationale: a funnel that hasn't been advertised in 90d is a different signal from an ad page that has historically run ads but is currently quiet. Pages collapse to Active/Cold; funnels carry the third state.)

## Verification: FB-UI count vs script count

`fb_ui_active_ads_count` is the number FB's Library UI displays. `script_active_ads_count` is what you extracted yourself. They should match within ±1 (FB updates lag a few seconds).

If they diverge by more than 1:
- Note this in the report's ad-pages table notes column.
- Do not "correct" either number — both are observations. Cross-checking is the user's job.
- If divergence is huge (e.g., FB UI shows 50, you extracted 3): something is wrong with extraction — re-run that Page, and if it persists, flag it for the user.

## Last-launch date

`last_ad_launched` for a Page = `max(start_date)` across all ads on the Page in the scraped window.

If no ads in the 90-day window: leave as `uncertain` and notes "no ads in 90-day window."

## Ad type for the ad-pages table

Determined per Page by inspecting every ad's `destination_kind`:

- `app` — every ad on this Page points to `apps.apple.com/...`, `play.google.com/...`, OR a known app-install deep-link redirector (see below).
- `w2w` — every ad points to a non-store, non-deep-link URL (a real web destination).
- `both` — at least one ad of each kind exists on the Page.

Edge: if a Page has zero ads in the scraped window, ad type is `uncertain`.

### Deep-link redirector hosts — always classified as `app`

These hosts redirect to the App Store / Play Store with attribution. They are commonly used in FB ads instead of direct store URLs. **They are not funnels.** Treat them the same as `apps.apple.com` for destination_kind:

| Host pattern | Vendor |
|---|---|
| `*.onelink.me`, `app.appsflyer.com` | AppsFlyer OneLink |
| `*.app.link`, `*.applink.com.bnc.lt` | Branch |
| `*.go.link` | Branch (newer hostname) |
| `*.adj.st`, `app.adjust.com` | Adjust |
| `*.smart.link` | Singular |
| `*.bttn.io` | Button |

Any of these appearing as an ad destination = `destination_kind: app`. Do NOT classify as `w2w` and do NOT treat the redirector host as a funnel domain. If you observe one, optionally record it in the `notes` column for that ad (e.g., "AppsFlyer attribution wrapper") but the row's classification is `app`.

## What never goes into status

- Whether the funnel "looks good" or "is well-designed".
- Whether the ads "performed well."
- Whether you think the campaign is "important."

Status is a mechanical function of dates and active flags. That's the whole point.
