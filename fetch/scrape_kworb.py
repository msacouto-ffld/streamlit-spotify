"""
scrape_kworb.py — Scrapes Spotify daily chart data from kworb.net for all
available markets and saves one Parquet file per country to data/.

Usage:
    python fetch/scrape_kworb.py               # all countries
    python fetch/scrape_kworb.py --markets us gb jp  # specific countries
    python fetch/scrape_kworb.py --dry-run     # list markets, don't fetch

Output schema (one row per chart position per country):
    market          str     ISO-2 country code, e.g. "us"  (lowercase)
    market_name     str     "United States"
    chart_date      date    Date of the chart snapshot
    pos             int     Chart position (1–200)
    pos_change      str     "NEW", "=", "+3", "-1", etc.
    artist          str     Artist name(s)
    title           str     Track title
    days_on_chart   int     Consecutive days on this country's chart
    peak_pos        int     All-time peak position on this chart
    peak_times      int     Number of times at peak (from "(xN)" column)
    streams         int     Daily streams
    streams_delta   int     Daily stream change vs prior day (signed)
    streams_7day    int     Rolling 7-day stream total
    streams_7day_delta int  7-day stream change (signed)
    streams_total   int     All-time total streams while on this chart
    artist_url      str     kworb artist page URL (relative)
    track_url       str     kworb track page URL (relative)
"""

import argparse
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_URL    = "https://kworb.net/spotify/country"
OUTPUT_DIR  = Path(__file__).parent.parent / "data"
DELAY_SEC   = 1.2      # polite crawl delay between requests
TIMEOUT_SEC = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SpotifyDashboardBot/1.0; "
        "+https://github.com/your-project)"
    )
}

# Full market list scraped from kworb.net/spotify/ index page
# Format: (iso2_lowercase, display_name)
ALL_MARKETS = [
    ("global", "Global"),
    ("us",     "United States"),
    ("gb",     "United Kingdom"),
    ("ad",     "Andorra"),
    ("ar",     "Argentina"),
    ("au",     "Australia"),
    ("at",     "Austria"),
    ("by",     "Belarus"),
    ("be",     "Belgium"),
    ("bo",     "Bolivia"),
    ("br",     "Brazil"),
    ("bg",     "Bulgaria"),
    ("ca",     "Canada"),
    ("cl",     "Chile"),
    ("co",     "Colombia"),
    ("cr",     "Costa Rica"),
    ("cy",     "Cyprus"),
    ("cz",     "Czech Republic"),
    ("dk",     "Denmark"),
    ("do",     "Dominican Republic"),
    ("ec",     "Ecuador"),
    ("eg",     "Egypt"),
    ("sv",     "El Salvador"),
    ("ee",     "Estonia"),
    ("fi",     "Finland"),
    ("fr",     "France"),
    ("de",     "Germany"),
    ("gr",     "Greece"),
    ("gt",     "Guatemala"),
    ("hn",     "Honduras"),
    ("hk",     "Hong Kong"),
    ("hu",     "Hungary"),
    ("is",     "Iceland"),
    ("in",     "India"),
    ("id",     "Indonesia"),
    ("ie",     "Ireland"),
    ("il",     "Israel"),
    ("it",     "Italy"),
    ("jp",     "Japan"),
    ("kz",     "Kazakhstan"),
    ("lv",     "Latvia"),
    ("lt",     "Lithuania"),
    ("lu",     "Luxembourg"),
    ("my",     "Malaysia"),
    ("mx",     "Mexico"),
    ("nl",     "Netherlands"),
    ("nz",     "New Zealand"),
    ("ni",     "Nicaragua"),
    ("ng",     "Nigeria"),
    ("no",     "Norway"),
    ("pk",     "Pakistan"),
    ("pa",     "Panama"),
    ("py",     "Paraguay"),
    ("pe",     "Peru"),
    ("ph",     "Philippines"),
    ("pl",     "Poland"),
    ("pt",     "Portugal"),
    ("ro",     "Romania"),
    ("sa",     "Saudi Arabia"),
    ("sg",     "Singapore"),
    ("sk",     "Slovakia"),
    ("za",     "South Africa"),
    ("kr",     "South Korea"),
    ("es",     "Spain"),
    ("se",     "Sweden"),
    ("ch",     "Switzerland"),
    ("th",     "Thailand"),
    ("tw",     "Taiwan"),
    ("tr",     "Turkey"),
    ("ua",     "Ukraine"),
    ("ae",     "United Arab Emirates"),
    ("uy",     "Uruguay"),
    ("vn",     "Vietnam"),
]

MARKET_LOOKUP = {code: name for code, name in ALL_MARKETS}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_int(text: str) -> int | None:
    """'7,738,921' → 7738921. Returns None if unparseable."""
    if not text:
        return None
    cleaned = re.sub(r"[,\s]", "", text.strip())
    # Handle signed values like '+467,235' or '-2,003,514'
    cleaned = cleaned.replace("+", "")
    try:
        return int(cleaned)
    except ValueError:
        return None


def _parse_pos_change(text: str) -> str:
    """Normalises the P+ column: '= ', '+2 ', 'NEW', '-1 ' → clean string."""
    text = text.strip()
    if not text:
        return "="
    return text


def _extract_peak_times(text: str) -> int | None:
    """'(x18)' → 18. Returns None if absent."""
    m = re.search(r"\(x(\d+)\)", text)
    return int(m.group(1)) if m else None


def fetch_chart(market_code: str) -> pd.DataFrame | None:
    """
    Fetches and parses the daily chart for a single market.
    Returns a DataFrame or None on failure.
    """
    url = f"{BASE_URL}/{market_code}_daily.html"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SEC)
        resp.raise_for_status()
        resp.encoding = "utf-8" 
    except requests.RequestException as e:
        print(f"  ✗ {market_code}: request failed — {e}")
        return None

    soup = BeautifulSoup(resp.content, "html.parser", from_encoding="utf-8")

    # ── Extract chart date from heading ──────────────────────────────────────
    chart_date = None
    heading = soup.find("div", id="page")
    for tag in soup.find_all(["h2", "strong", "b", "p"]):
        m = re.search(r"(\d{4}/\d{2}/\d{2})", tag.get_text())
        if m:
            chart_date = datetime.strptime(m.group(1), "%Y/%m/%d").date()
            break
    if chart_date is None:
        # Try the whole page text
        m = re.search(r"(\d{4}/\d{2}/\d{2})", soup.get_text())
        chart_date = (
            datetime.strptime(m.group(1), "%Y/%m/%d").date() if m else date.today()
        )

    # ── Find the chart table ──────────────────────────────────────────────────
    tables = soup.find_all("table")
    if not tables:
        print(f"  ✗ {market_code}: no table found")
        return None

    # Pick the largest table (the chart; ignore any nav tables)
    table = max(tables, key=lambda t: len(t.find_all("tr")))
    rows = table.find_all("tr")

    records = []
    for row in rows[1:]:   # skip header
        cells = row.find_all("td")
        if len(cells) < 9:
            continue

        # ── Pos ──────────────────────────────────────────────────────────────
        pos_text = cells[0].get_text(strip=True)
        try:
            pos = int(pos_text)
        except ValueError:
            continue   # skip malformed rows

        # ── P+ (position change) ─────────────────────────────────────────────
        pos_change = _parse_pos_change(cells[1].get_text(strip=True))

        # ── Artist & Title with URLs ──────────────────────────────────────────
        artist_title_cell = cells[2]
        links = artist_title_cell.find_all("a")
        if len(links) >= 2:
            artist      = links[0].get_text(strip=True)
            title       = links[1].get_text(strip=True)
            artist_url  = links[0].get("href", "")
            track_url   = links[1].get("href", "")
        elif len(links) == 1:
            # Sometimes formatted differently
            full_text   = artist_title_cell.get_text(" - ", strip=True)
            parts       = full_text.split(" - ", 1)
            artist      = parts[0] if len(parts) > 1 else full_text
            title       = parts[1] if len(parts) > 1 else ""
            artist_url  = links[0].get("href", "")
            track_url   = ""
        else:
            full_text = artist_title_cell.get_text(" - ", strip=True)
            parts     = full_text.split(" - ", 1)
            artist    = parts[0] if len(parts) > 1 else full_text
            title     = parts[1] if len(parts) > 1 else ""
            artist_url = track_url = ""

        # ── Numeric columns ───────────────────────────────────────────────────
        days_text       = cells[3].get_text(strip=True)
        peak_text       = cells[4].get_text(strip=True)
        peak_times_text = cells[5].get_text(strip=True)
        streams_text    = cells[6].get_text(strip=True)
        streams_d_text  = cells[7].get_text(strip=True)
        s7day_text      = cells[8].get_text(strip=True)
        s7day_d_text    = cells[9].get_text(strip=True) if len(cells) > 9 else ""
        total_text      = cells[10].get_text(strip=True) if len(cells) > 10 else ""

        records.append({
            "market":             market_code,
            "market_name":        MARKET_LOOKUP.get(market_code, market_code.upper()),
            "chart_date":         chart_date,
            "pos":                pos,
            "pos_change":         pos_change,
            "artist":             artist,
            "title":              title,
            "days_on_chart":      _clean_int(days_text),
            "peak_pos":           _clean_int(peak_text),
            "peak_times":         _extract_peak_times(peak_times_text),
            "streams":            _clean_int(streams_text),
            "streams_delta":      _clean_int(streams_d_text),
            "streams_7day":       _clean_int(s7day_text),
            "streams_7day_delta": _clean_int(s7day_d_text),
            "streams_total":      _clean_int(total_text),
            "artist_url":         artist_url,
            "track_url":          track_url,
        })

    if not records:
        print(f"  ✗ {market_code}: parsed 0 rows")
        return None

    return pd.DataFrame(records)


def save_parquet(df: pd.DataFrame, market_code: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{market_code}_daily.parquet"
    df.to_parquet(path, index=False)
    return path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scrape Kworb Spotify charts")
    parser.add_argument(
        "--markets", nargs="+", metavar="CODE",
        help="ISO-2 market codes to fetch (default: all). Use 'global' for the global chart.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List markets that would be fetched without making any requests.",
    )
    parser.add_argument(
        "--delay", type=float, default=DELAY_SEC, metavar="SECONDS",
        help=f"Delay between requests in seconds (default: {DELAY_SEC})",
    )
    args = parser.parse_args()

    # Resolve market list
    if args.markets:
        requested = [m.lower() for m in args.markets]
        invalid   = [m for m in requested if m not in MARKET_LOOKUP]
        if invalid:
            print(f"Unknown market codes: {invalid}")
            print(f"Valid codes: {[c for c, _ in ALL_MARKETS]}")
            sys.exit(1)
        markets = [(c, MARKET_LOOKUP[c]) for c in requested]
    else:
        markets = ALL_MARKETS

    if args.dry_run:
        print(f"Would fetch {len(markets)} markets:")
        for code, name in markets:
            print(f"  {code:6s}  {name}")
        return

    print(f"Fetching {len(markets)} markets → {OUTPUT_DIR}/\n")

    success, failed = [], []

    for i, (code, name) in enumerate(markets, 1):
        print(f"[{i:3d}/{len(markets)}] {code:6s}  {name} ...", end=" ", flush=True)
        df = fetch_chart(code)
        if df is not None:
            path = save_parquet(df, code)
            print(f"✓  {len(df)} rows → {path.name}")
            success.append(code)
        else:
            failed.append(code)

        if i < len(markets):
            time.sleep(args.delay)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'─'*50}")
    print(f"Done.  ✓ {len(success)} succeeded   ✗ {len(failed)} failed")
    if failed:
        print(f"Failed markets: {failed}")

    # ── Optionally merge into one combined Parquet ────────────────────────────
    if success:
        combined_path = OUTPUT_DIR / "all_markets.parquet"
        files = [OUTPUT_DIR / f"{c}_daily.parquet" for c in success]
        combined = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        combined.to_parquet(combined_path, index=False)
        print(f"\nCombined file: {combined_path}  ({len(combined):,} rows total)")


if __name__ == "__main__":
    main()