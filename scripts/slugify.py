#!/usr/bin/env python3
"""
Produce a filesystem-safe kebab-case slug for filenames.

Usage:
  python slugify.py "Calm — Sleep & Meditation"
  -> calm-sleep-meditation

Edge handling:
- Strips accents (NFKD normalize, drop combining marks).
- Lowercases.
- Replaces any non-alphanumeric run with a single `-`.
- Trims leading/trailing `-`.
- Collapses repeated `-`.
- Caps total length at 60 chars (avoiding mid-word cuts when possible).
- Returns "untitled" if the result is empty.

Output: prints the slug to stdout, no newline if --no-newline.
"""

import argparse
import re
import sys
import unicodedata


def slugify(text, max_len=60):
    if not text:
        return "untitled"
    # Normalize accents away.
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    # Replace any non-[a-z0-9] run with a single dash.
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    text = re.sub(r"-{2,}", "-", text)
    if not text:
        return "untitled"
    if len(text) <= max_len:
        return text
    # Try to cut at a word boundary.
    cut = text[:max_len]
    last_dash = cut.rfind("-")
    if last_dash >= max_len // 2:
        cut = cut[:last_dash]
    return cut.strip("-") or text[:max_len]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("text", help="The string to slugify")
    ap.add_argument("--max-len", type=int, default=60)
    ap.add_argument("--no-newline", action="store_true")
    args = ap.parse_args()

    slug = slugify(args.text, args.max_len)
    sys.stdout.write(slug)
    if not args.no_newline:
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
