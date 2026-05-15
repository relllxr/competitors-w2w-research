#!/usr/bin/env python3
"""
iTunes Search API lookup for the competitors-w2w-research skill.

Usage:
  python lookup_app.py --id 1234567890                    # lookup by trackId
  python lookup_app.py --bundleId com.example.app         # lookup by bundleId
  python lookup_app.py --artistId 987654321               # all apps by developer (artistId)
  python lookup_app.py --search "fasting tracker"         # keyword search
  python lookup_app.py --developer "Calm.com, Inc."       # search by developer name

Optional:
  --country US        ISO 3166-1 alpha-2 (default: us)
  --entity software   software | iPadSoftware | macSoftware (default: software)
  --limit 25          max results for search (default: 25, cap 200)
  --json              already the default; included for explicitness

Output: JSON to stdout. On error, exits 1 with {"error": "..."} on stdout.
"""

import argparse
import json
import subprocess
import sys
import urllib.parse

BASE = "https://itunes.apple.com"
USER_AGENT = "competitors-w2w-research/1 (+https://github.com/anthropics/claude-code)"


def _http_get(url):
    """Fetch via curl (uses system trust store; available on macOS/Linux)."""
    try:
        proc = subprocess.run(
            ["curl", "-sSL", "-A", USER_AGENT, "--max-time", "15", url],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return None, "curl not found on PATH"
    if proc.returncode != 0:
        return None, f"curl failed (rc={proc.returncode}): {proc.stderr.strip()[:200]}"
    try:
        return json.loads(proc.stdout), None
    except json.JSONDecodeError as e:
        return None, f"JSON decode error: {e}"


def _build_lookup_url(*, track_id=None, bundle_id=None, artist_id=None,
                     country="us", entity="software", limit=200):
    params = {"country": country, "entity": entity, "limit": str(limit)}
    if track_id:
        params["id"] = str(track_id)
    elif bundle_id:
        params["bundleId"] = bundle_id
    elif artist_id:
        params["id"] = str(artist_id)
    return f"{BASE}/lookup?" + urllib.parse.urlencode(params)


def _build_search_url(*, term, country="us", entity="software", limit=25, media="software"):
    params = {
        "term": term,
        "country": country,
        "entity": entity,
        "limit": str(min(limit, 200)),
        "media": media,
    }
    return f"{BASE}/search?" + urllib.parse.urlencode(params)


def _trim(result):
    """Keep the fields the skill actually uses."""
    keep = [
        "trackId", "trackName", "trackCensoredName", "bundleId",
        "sellerName", "sellerUrl", "description", "releaseNotes",
        "primaryGenreName", "primaryGenreId", "genres",
        "languageCodesISO2A", "screenshotUrls", "artworkUrl512",
        "artistId", "artistName", "artistViewUrl", "trackViewUrl",
        "price", "formattedPrice", "currency",
        "currentVersionReleaseDate", "releaseDate", "version",
        "minimumOsVersion", "averageUserRating", "userRatingCount",
        "contentAdvisoryRating",
    ]
    return {k: result.get(k) for k in keep if k in result}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--id", dest="track_id", help="App trackId (numeric)")
    g.add_argument("--bundleId", dest="bundle_id", help="Bundle ID like com.example.app")
    g.add_argument("--artistId", dest="artist_id", help="Developer artistId (numeric)")
    g.add_argument("--search", dest="search", help="General keyword search")
    g.add_argument("--developer", dest="developer", help="Search by developer name (term-based)")
    ap.add_argument("--country", default="us")
    ap.add_argument("--entity", default="software", choices=["software", "iPadSoftware", "macSoftware"])
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()

    if args.track_id:
        url = _build_lookup_url(track_id=args.track_id, country=args.country, entity=args.entity)
    elif args.bundle_id:
        url = _build_lookup_url(bundle_id=args.bundle_id, country=args.country, entity=args.entity)
    elif args.artist_id:
        url = _build_lookup_url(artist_id=args.artist_id, country=args.country,
                                entity=args.entity, limit=args.limit)
    elif args.search:
        url = _build_search_url(term=args.search, country=args.country,
                                entity=args.entity, limit=args.limit)
    else:
        url = _build_search_url(term=args.developer, country=args.country,
                                entity=args.entity, limit=args.limit)

    data, err = _http_get(url)
    if err:
        json.dump({"error": err, "url": url}, sys.stdout)
        sys.exit(1)

    results = data.get("results", [])
    trimmed = [_trim(r) for r in results]

    out = {
        "query_url": url,
        "result_count": data.get("resultCount", len(results)),
        "results": trimmed,
    }
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
