#!/usr/bin/env python3
"""
Detect a funnel page's tech stack from HTML + response headers.

Usage:
  python detect_tech_stack.py https://example.com/get

Output (JSON to stdout):
{
  "funnel_url": "...",
  "fetched_at": "<ISO>",
  "http_status": 200,
  "final_url": "...",
  "builder": "Funnelish | ClickFunnels 1.0 | ClickFunnels 2.0 | Webflow | Framer | Unbounce | custom | uncertain",
  "analytics": ["GA4", "Meta Pixel", "TikTok Pixel", "Snap Pixel"],
  "payments": ["Stripe.js", "Paddle", "RevenueCat Web", "Lemon Squeezy"],
  "ab_testing": ["Optimizely", "VWO", "GrowthBook", "Statsig"],
  "email_capture": ["Klaviyo", "Mailchimp", "ConvertKit"],
  "tag_manager": "GTM-XXXXXXX | null",
  "hosting_cdn": ["Cloudflare", "Vercel", "Netlify", "AWS CloudFront", "Fastly"],
  "other_notable_scripts": [],
  "notes": null,
  "error": null
}

Exit code: 0 on success (even if detection is partial). 1 only on a fundamental error (URL parse, network).
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
import urllib.parse

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)
TIMEOUT = 20


def _fetch(url):
    """Fetch via curl. Returns dict with status, final_url, body, headers (lowercased keys, list values)."""
    # Fetch body + final URL together; capture headers separately.
    proc_body = subprocess.run(
        ["curl", "-sSL", "-A", USER_AGENT, "--max-time", str(TIMEOUT),
         "-o", "-", "-w", "\n__META__\n%{http_code}\n%{url_effective}\n", url],
        capture_output=True, text=True, check=False,
    )
    if proc_body.returncode != 0:
        raise RuntimeError(f"curl failed (rc={proc_body.returncode}): {proc_body.stderr.strip()[:200]}")
    parts = proc_body.stdout.rsplit("\n__META__\n", 1)
    body = parts[0] if len(parts) == 2 else proc_body.stdout
    meta_lines = (parts[1] if len(parts) == 2 else "").strip().splitlines()
    status = int(meta_lines[0]) if meta_lines and meta_lines[0].isdigit() else None
    final_url = meta_lines[1] if len(meta_lines) > 1 else url

    # Headers from a separate -I HEAD-like call (but use GET via -sIL --range 0-0 fallback isn't reliable).
    # Use curl -sSL -D - -o /dev/null for the SAME url to get the final-hop response headers.
    proc_hdrs = subprocess.run(
        ["curl", "-sSL", "-A", USER_AGENT, "--max-time", str(TIMEOUT),
         "-D", "-", "-o", "/dev/null", url],
        capture_output=True, text=True, check=False,
    )
    headers = {}
    if proc_hdrs.returncode == 0:
        # Output contains all redirect-hop headers separated by blank lines. Keep the FINAL block.
        blocks = [b for b in proc_hdrs.stdout.split("\r\n\r\n") if b.strip()]
        if not blocks:
            blocks = [b for b in proc_hdrs.stdout.split("\n\n") if b.strip()]
        last = blocks[-1] if blocks else ""
        for line in last.splitlines():
            if ":" in line and not line.startswith("HTTP/"):
                k, _, v = line.partition(":")
                headers.setdefault(k.strip().lower(), []).append(v.strip())

    return {
        "status": status,
        "final_url": final_url,
        "body": body,
        "headers": headers,
    }


def _has(html, *needles):
    return any(n.lower() in html for n in needles)


def _re(html, pattern, flags=re.IGNORECASE):
    m = re.search(pattern, html, flags)
    return m.group(0) if m else None


def _detect_builder(html, headers, final_url):
    host = urllib.parse.urlparse(final_url).hostname or ""
    server = "".join(headers.get("server", [])).lower()

    # ClickFunnels 1.0
    if host.endswith(".clickfunnels.com") or _has(html, "assets.clickfunnels.com/", "_etison_",
                                                   "elfunnelwrapper", "elpagewrapper", "elheadlinewrapper"):
        return "ClickFunnels 1.0"
    # ClickFunnels 2.0
    if host.endswith(".myclickfunnels.com") or _has(html, "cdn.myclickfunnels.com/") \
            or _re(html, r'class="[^"]*\bcf2-[a-z0-9-]+'):
        return "ClickFunnels 2.0"
    # Funnelish (distinct from Funnelfox below). funnelish.com is the original product.
    if (_has(html, "assets.funnelish.com/", "cdn.funnelish.com/")
            or _re(html, r'<meta[^>]+content="Funnelish"')):
        return "Funnelish"
    # Funnelfox — popular mobile-W2W funnel builder. Uses fnlfx.com CDN.
    # NOTE: Despite the URL similarity, this is a different product from Funnelish.
    if (_has(html, "cdn.fnlfx.com", "assets.fnlfx.com", ".fnlfx.com")
            or _re(html, r'<meta[^>]+content="Funnelfox"')
            or _re(html, r'\bfunnelfox\b', re.IGNORECASE)):
        return "Funnelfox"
    # Web2Wave — another popular mobile-W2W funnel builder.
    if (_has(html, "cdn.web2wave.com", "assets.web2wave.com", "web2wave.com/embed", "web2wave-")
            or _re(html, r'\bdata-w2w(?:-[a-z]+)?=')
            or _re(html, r'\bwindow\.web2wave\b')
            or _re(html, r'<meta[^>]+content="Web2Wave"')
            or (_has(html, "web2wave") and _re(html, r'web2wave\.com'))):
        return "Web2Wave"
    # Webflow
    if _re(html, r'<html[^>]+data-wf-(page|site)=') or _has(html, "webflow.js") \
            or _has(html, "assets.website-files.com/", "uploads-ssl.webflow.com/") \
            or "webflow" in server:
        return "Webflow"
    # Framer
    if _has(html, "framerusercontent.com", "framercdn.com", "framerstatic.com") \
            or _re(html, r'<meta[^>]+content="Framer"') \
            or _re(html, r'\sdata-framer-[a-z-]+='):
        return "Framer"
    # Unbounce
    if host.endswith(".unbouncepages.com") or _has(html, "d3pkntwtp2ukl5.cloudfront.net/") \
            or _re(html, r'\bwindow\.(lp|ub)\b'):
        return "Unbounce"
    return "custom"


def _detect_analytics(html):
    found = []
    if _re(html, r'googletagmanager\.com/gtag/js\?id=G-[A-Z0-9]+') \
            or _re(html, r'gtag\([\"\']config[\"\']\s*,\s*[\"\']G-[A-Z0-9]+'):
        found.append("GA4")
    if _has(html, "connect.facebook.net/en_us/fbevents.js", "connect.facebook.net/en_US/fbevents.js") \
            or _re(html, r'fbq\([\"\']init[\"\']') \
            or _re(html, r'facebook\.com/tr\?id='):
        found.append("Meta Pixel")
    if _has(html, "analytics.tiktok.com/i18n/pixel/events.js") \
            or _re(html, r'ttq\.load\([\"\'][A-Z0-9]+'):
        found.append("TikTok Pixel")
    if _has(html, "sc-static.net/scevent.min.js") \
            or _re(html, r'snaptr\([\"\']init[\"\']'):
        found.append("Snap Pixel")
    return found


def _detect_payments(html):
    found = []
    if _has(html, "js.stripe.com/v3", "js.stripe.com/basil/stripe.js"):
        found.append("Stripe.js")
    if _has(html, "cdn.paddle.com/paddle/v2/paddle.js", "cdn.paddle.com/paddle/paddle.js") \
            or _re(html, r'Paddle\.(Setup|Initialize)\b'):
        found.append("Paddle")
    if _has(html, "cdn.revenuecat.com/", "js.revenuecat.com/", "pay.rev.cat") \
            or _re(html, r'\bwindow\.Purchases\b'):
        found.append("RevenueCat Web")
    if _has(html, "app.lemonsqueezy.com/js/lemon.js") \
            or _re(html, r'LemonSqueezy\.Setup\b') \
            or _re(html, r'\sdata-lemonsqueezy-'):
        found.append("Lemon Squeezy")
    return found


def _detect_ab(html):
    found = []
    if _re(html, r'cdn\.optimizely\.com/js/\d+\.js') or _re(html, r'\bwindow\.optimizely\b'):
        found.append("Optimizely")
    if _has(html, "dev.visualwebsiteoptimizer.com/lib/") \
            or _re(html, r'\bwindow\._vwo_code\b|\bwindow\.VWO\b'):
        found.append("VWO")
    if _has(html, "cdn.jsdelivr.net/npm/@growthbook/growthbook", "cdn.growthbook.io/") \
            or _re(html, r'\sdata-client-key="') \
            or _re(html, r'\bwindow\.growthbook\b'):
        found.append("GrowthBook")
    if _has(html, "cdn.jsdelivr.net/npm/statsig-js", "api.statsig.com") \
            or _re(html, r'\bwindow\.statsig\b'):
        found.append("Statsig")
    return found


def _detect_email(html):
    found = []
    if _re(html, r'static\.klaviyo\.com/onsite/js/[A-Za-z0-9]+/klaviyo\.js') \
            or _re(html, r'\bwindow\.(_klOnsite|klaviyo)\b'):
        found.append("Klaviyo")
    if _has(html, "chimpstatic.com/mcjs-connected/") or _re(html, r'\.list-manage\.com/'):
        found.append("Mailchimp")
    if _has(html, "f.convertkit.com/ckjs/") \
            or _re(html, r'app\.convertkit\.com/forms/\d+/subscriptions'):
        found.append("ConvertKit")
    return found


def _detect_tag_manager(html):
    m = re.search(r'googletagmanager\.com/gtm\.js\?id=(GTM-[A-Z0-9]+)', html, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m = re.search(r'googletagmanager\.com/ns\.html\?id=(GTM-[A-Z0-9]+)', html, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def _detect_hosting(headers):
    found = []
    h = {k: " ".join(v).lower() for k, v in headers.items()}
    if "cf-ray" in h or h.get("server", "").startswith("cloudflare") or "cf-cache-status" in h:
        found.append("Cloudflare")
    if "x-vercel-id" in h or "x-vercel-cache" in h or h.get("server", "").startswith("vercel"):
        found.append("Vercel")
    if "x-nf-request-id" in h or h.get("server", "").startswith("netlify"):
        found.append("Netlify")
    if "x-amz-cf-id" in h or "x-amz-cf-pop" in h or "cloudfront" in h.get("via", ""):
        found.append("AWS CloudFront")
    if "x-served-by" in h or h.get("x-cache") or "x-timer" in h:
        # x-served-by + x-cache + x-timer together = Fastly. Single header is suggestive.
        if "x-served-by" in h and ("cache-" in h["x-served-by"]):
            found.append("Fastly")
    return found


def _detect_other(html):
    """Catch-all: identify recognizable scripts that aren't in our specific categories."""
    candidates = {
        "Hotjar": "static.hotjar.com",
        "Fullstory": "edge.fullstory.com",
        "Microsoft Clarity": "clarity.ms",
        "LinkedIn Insight": "snap.licdn.com/li.lms-analytics",
        "Pinterest Tag": "ct.pinterest.com",
        "Intercom": "widget.intercom.io",
        "Drift": "js.driftt.com",
        "Crisp Chat": "client.crisp.chat",
        "Segment": "cdn.segment.com",
        "Amplitude": "cdn.amplitude.com",
        "Mixpanel": "cdn.mxpnl.com",
        "PostHog": "app.posthog.com",
        "Sentry": "browser.sentry-cdn.com",
        "Cloudflare Web Analytics": "static.cloudflareinsights.com",
    }
    found = []
    lower = html.lower()
    for label, needle in candidates.items():
        if needle.lower() in lower:
            found.append(label)
    return found


def detect(url):
    try:
        result = _fetch(url)
    except Exception as e:
        return {
            "funnel_url": url,
            "fetched_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "http_status": None,
            "final_url": None,
            "builder": "uncertain",
            "analytics": [],
            "payments": [],
            "ab_testing": [],
            "email_capture": [],
            "tag_manager": None,
            "hosting_cdn": [],
            "other_notable_scripts": [],
            "notes": "uncertain — fetch failed",
            "error": str(e),
        }

    html_lower = result["body"].lower()
    status = result["status"]
    body_ok = status is not None and 200 <= status < 400

    notes = None
    if not body_ok:
        notes = (
            f"HTTP {status} on final URL — body may be a CDN challenge/error page; "
            "builder and body-derived signatures are unreliable. Headers (CDN) are still trusted."
        )

    return {
        "funnel_url": url,
        "fetched_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "http_status": status,
        "final_url": result["final_url"],
        "builder": _detect_builder(html_lower, result["headers"], result["final_url"]) if body_ok else "uncertain",
        "analytics": _detect_analytics(html_lower) if body_ok else [],
        "payments": _detect_payments(html_lower) if body_ok else [],
        "ab_testing": _detect_ab(html_lower) if body_ok else [],
        "email_capture": _detect_email(html_lower) if body_ok else [],
        "tag_manager": _detect_tag_manager(result["body"]) if body_ok else None,
        "hosting_cdn": _detect_hosting(result["headers"]),
        "other_notable_scripts": _detect_other(result["body"]) if body_ok else [],
        "notes": notes,
        "error": None,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("url", help="Funnel URL to inspect")
    args = ap.parse_args()

    parsed = urllib.parse.urlparse(args.url)
    if not parsed.scheme or not parsed.netloc:
        json.dump({"error": "invalid URL", "input": args.url}, sys.stdout)
        sys.exit(1)

    result = detect(args.url)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
