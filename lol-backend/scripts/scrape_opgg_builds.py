#!/usr/bin/env python3
"""
OP.GG Ahri build scraper - returns top 3 builds by win rate.

Usage:
    python scripts/scrape_opgg_builds.py

Output format (JSON array to stdout):
    ["Build Name 1", "Build Name 2", "Build Name 3"]

Exit codes:
    0 - success
    1 - request/parse failure

Requirements:
    pip install requests beautifulsoup4 lxml
"""

import sys
import json
import re
import requests

URL = "https://www.op.gg/champions/ahri/build"
TIMEOUT = 15  # total timeout <= 15s (connect + read)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def parse_core_builds(html: str) -> list[tuple[str, float]]:
    """
    Parse the Core Builds table from OP.GG page.
    Each row has: [item1, item2, item3] + pick_rate% + games + win_rate%
    The win rate is the 2nd percentage in the text content of the row.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    builds = []

    # Find the table with "Core Builds" as first row text
    core_table = None
    for t in soup.select("table"):
        first_row = t.select_one("tr")
        if first_row and "Core Builds" in first_row.get_text():
            core_table = t
            break

    if not core_table:
        raise OPGGParseError("Core Builds table not found - page structure may have changed")

    rows = core_table.select("tr")
    for row in rows[1:]:  # skip header row
        imgs = row.select("img")
        item_names = [img.get("alt") for img in imgs if img.get("alt")]
        if not item_names:
            continue

        text = row.get_text()
        # Row text contains two % values: pick_rate% then win_rate%
        # e.g. "16.6%25,849 Games54.34%" -> pick_rate=16.6, win_rate=54.34
        percentages = re.findall(r"([\d.]+%)", text)
        if len(percentages) < 2:
            continue

        win_rate = float(percentages[1].rstrip("%"))
        build_name = " + ".join(item_names)
        builds.append((build_name, win_rate))

    return builds


class OPGGParseError(Exception):
    pass


def main():
    print(f"Fetching {URL}", file=sys.stderr)

    try:
        response = requests.get(URL, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as e:
        print(f"ERROR: Request failed: {e}", file=sys.stderr)
        sys.exit(1)

    if response.status_code != 200:
        print(f"ERROR: HTTP {response.status_code}", file=sys.stderr)
        sys.exit(1)

    print("HTTP 200 received, parsing Core Builds table...", file=sys.stderr)

    try:
        builds = parse_core_builds(response.text)
    except OPGGParseError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Parse failed: {e}", file=sys.stderr)
        sys.exit(1)

    if not builds:
        print("ERROR: No builds found - page structure may have changed", file=sys.stderr)
        sys.exit(1)

    # Sort by win_rate descending
    builds.sort(key=lambda x: x[1], reverse=True)

    print(f"Found {len(builds)} builds", file=sys.stderr)
    for name, wr in builds:
        print(f"  {wr:.2f}% - {name}", file=sys.stderr)

    top3 = [name for name, _ in builds[:3]]
    print(json.dumps(top3, ensure_ascii=False))

    if len(top3) < 3:
        print(f"WARNING: only {len(top3)} builds found (expected 3)", file=sys.stderr)


if __name__ == "__main__":
    main()