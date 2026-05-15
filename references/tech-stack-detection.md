# Tech-Stack Detection Reference

This is the lookup table the bundled `scripts/detect_tech_stack.py` uses. It also tells you what to look for if a funnel needs manual inspection.

Detection is **HTML grep + response headers** — no JS execution, no Playwright. Run via `curl` or `WebFetch`.

## Categories tracked

Per-funnel record stored in `state.phase_3.tech_stack` (and rendered in the report's per-stack tables — no separate CSV is produced):

- `builder` — single value (Funnelish, Funnelfox, Web2Wave, ClickFunnels 1.0, ClickFunnels 2.0, Webflow, Framer, Unbounce, custom, uncertain)
- `analytics` — list (GA4, Meta Pixel, TikTok Pixel, Snap Pixel)
- `payments` — list (Stripe.js, Paddle, RevenueCat Web, Lemon Squeezy)
- `ab_testing` — list (Optimizely, VWO, GrowthBook, Statsig)
- `email_capture` — list (Klaviyo, Mailchimp, ConvertKit)
- `tag_manager` — single value (GTM container ID like `GTM-XXXXXXX`, or empty)
- `hosting_cdn` — list (Cloudflare, Vercel, Netlify, AWS CloudFront, Fastly)
- `other_notable_scripts` — free-text list (anything observed that doesn't fit above)
- `notes` — free-text caveats / uncertainty

## Detection signatures

| Tool | Category | Signature(s) | Method |
|---|---|---|---|
| Funnelish | Builder | `assets.funnelish.com/`, `cdn.funnelish.com/` in script/asset src; `<meta name="generator" content="Funnelish">` (when present). **Distinct from Funnelfox below** — do NOT conflate. | HTML grep |
| **Funnelfox** | Builder | `cdn.fnlfx.com`, `assets.fnlfx.com`, any `.fnlfx.com` host; `<meta name="generator" content="Funnelfox">` (when present); the literal word `funnelfox` in inline scripts/comments. Popular **mobile-W2W** funnel builder — frequently seen behind brain-training, fasting, weight-loss app funnels. | HTML grep |
| **Web2Wave** | Builder | `cdn.web2wave.com`, `assets.web2wave.com`, `web2wave.com/embed`; `data-w2w-*` attributes on elements; `window.web2wave` JS object; `<meta name="generator" content="Web2Wave">`. Also popular **mobile-W2W** funnel builder. Verified detection: BrainGain's `quiz.brain-gain.app` funnels are Funnelfox-built. Web2Wave was identified as the funnel-builder pattern on `quiz.cognitivegrowth.net` (iter-2 eval-2 funnel-URL-harder-resolve). | HTML grep + DOM attrs |
| ClickFunnels 1.0 | Builder | host is `*.clickfunnels.com`; `assets.clickfunnels.com/`; classes like `elFunnelWrapper`, `elPageWrapper`, `elHeadlineWrapper`; `_etison_` cookies | HTML grep + cookies |
| ClickFunnels 2.0 | Builder | host is `*.myclickfunnels.com`; `cdn.myclickfunnels.com/` script src; `cf2-` prefixed classes | HTML grep |
| Webflow | Builder | `<html data-wf-page="..." data-wf-site="...">`; `<meta name="generator" content="Webflow">`; `assets.website-files.com/`, `uploads-ssl.webflow.com/`; `webflow.js`; `Server: Webflow` header | HTML grep + header |
| Framer | Builder | script src on `framer.com`, `framerstatic.com`, `framerusercontent.com`, `framercdn.com`; `<meta name="generator" content="Framer">`; `data-framer-*` attributes | HTML grep |
| Unbounce | Builder | host is `*.unbouncepages.com`; script src `d3pkntwtp2ukl5.cloudfront.net/`; `window.lp` / `window.ub` (runtime-only — best-effort) | HTML grep |
| GA4 | Analytics | `googletagmanager.com/gtag/js?id=G-XXXXXXXX`; inline `gtag('config','G-...')` | HTML grep |
| Meta Pixel | Analytics | `connect.facebook.net/en_US/fbevents.js`; inline `fbq('init','<numeric>')`; `<noscript>` `facebook.com/tr?id=...` | HTML grep |
| TikTok Pixel | Analytics | `analytics.tiktok.com/i18n/pixel/events.js`; inline `ttq.load('<id>')` | HTML grep |
| Snap Pixel | Analytics | `sc-static.net/scevent.min.js`; inline `snaptr('init','<id>')` | HTML grep |
| Stripe.js | Payments | `js.stripe.com/v3/` or `js.stripe.com/basil/stripe.js`; `window.Stripe` | HTML grep |
| Paddle | Payments | `cdn.paddle.com/paddle/v2/paddle.js` (Billing) or `cdn.paddle.com/paddle/paddle.js` (Classic); inline `Paddle.Setup`/`Paddle.Initialize` | HTML grep |
| RevenueCat Web | Payments | `purchases.js` from `cdn.revenuecat.com/` or `js.revenuecat.com/`; redirects to `pay.rev.cat/...`; `window.Purchases` | HTML grep |
| Lemon Squeezy | Payments | `app.lemonsqueezy.com/js/lemon.js`; inline `LemonSqueezy.Setup`; `data-lemonsqueezy-` attrs | HTML grep |
| Optimizely | A/B | `cdn.optimizely.com/js/<projectId>.js`; `window.optimizely` | HTML grep |
| VWO | A/B | `dev.visualwebsiteoptimizer.com/lib/<accountId>.js`; `window._vwo_code` / `window.VWO` | HTML grep |
| GrowthBook | A/B | `cdn.jsdelivr.net/npm/@growthbook/growthbook` or `cdn.growthbook.io/`; `data-client-key` on script; `window.growthbook` | HTML grep |
| Statsig | A/B | `cdn.jsdelivr.net/npm/statsig-js` or `api.statsig.com`; `window.statsig` | HTML grep |
| Klaviyo | Email | `static.klaviyo.com/onsite/js/<KEY>/klaviyo.js`; `window._klOnsite` / `window.klaviyo` | HTML grep |
| Mailchimp | Email | `chimpstatic.com/mcjs-connected/`; form actions on `*.list-manage.com` | HTML grep |
| ConvertKit (Kit) | Email | `f.convertkit.com/ckjs/`; form action `app.convertkit.com/forms/<id>/subscriptions`; `data-uid` on script | HTML grep |
| GTM | Tag manager | `googletagmanager.com/gtm.js?id=GTM-XXXXXXX`; `<noscript>` iframe `googletagmanager.com/ns.html?id=GTM-...` | HTML grep |
| Cloudflare | Hosting/CDN | `cf-ray` header; `Server: cloudflare`; `cf-cache-status` | Header |
| Vercel | Hosting/CDN | `x-vercel-id`, `x-vercel-cache`, `Server: Vercel` | Header |
| Netlify | Hosting/CDN | `x-nf-request-id`, `Server: Netlify` | Header |
| AWS CloudFront | Hosting/CDN | `x-amz-cf-id`, `x-amz-cf-pop`, `Via: ... CloudFront` | Header |
| Fastly | Hosting/CDN | `x-served-by: cache-<POP>-<id>`, `x-cache: HIT/MISS`, `x-timer` | Header |

## Method notes

- **HTML grep** = the detection script runs `curl -L -A '<UA>' <url>`, captures HTML, then greps for the patterns above. Case-insensitive grep is fine.
- **Header** = the script reads the response headers (`curl -sIL`). Multiple-redirect chains: prefer the FINAL response's headers, but also note any header set by an earlier hop if it indicates a different CDN.
- **Runtime-only** signatures (`window.<global>`) cannot be detected via HTML grep — they exist only after JS execution. For these, the script falls back to inline-script grep (the code that ASSIGNS to `window.X` is usually visible in HTML).

## Uncertainty handling

When the script can't find a positive signature for a category:

- `builder` defaults to `custom` if no builder signature matches **and** the page is reachable.
- Lists (`analytics`, `payments`, `ab_testing`, `email_capture`, `hosting_cdn`) stay empty `[]` when nothing is detected — that's correct, not uncertain. Many funnels legitimately don't have a pixel of every type.
- `tag_manager` stays `null` when no GTM container ID is found.
- If the fetch itself FAILS (DNS, 5xx, timeout, blocked by Cloudflare challenge), every column is `uncertain` and `notes` records the error. Do not invent values.

## How the script is used

```
python scripts/detect_tech_stack.py https://example.com/get
```

Returns JSON to stdout, e.g.:

```json
{
  "funnel_url": "https://example.com/get",
  "fetched_at": "2026-05-13T12:34:56Z",
  "http_status": 200,
  "final_url": "https://example.com/get/?utm=fb",
  "builder": "Funnelish",
  "analytics": ["GA4", "Meta Pixel"],
  "payments": ["Stripe.js"],
  "ab_testing": [],
  "email_capture": ["Klaviyo"],
  "tag_manager": "GTM-XXXXXXX",
  "hosting_cdn": ["Cloudflare"],
  "other_notable_scripts": [],
  "notes": null,
  "error": null
}
```

Parse the JSON; do not try to re-extract from logs.

## When to manually inspect

If a funnel returns `builder: custom` but you suspect it's something unusual (e.g., a known SaaS with custom branding), open the page in Playwright and look at `Network` tab + `document.scripts`. Write findings into `other_notable_scripts` / `notes` manually. Don't override what the script returned — extend it.
