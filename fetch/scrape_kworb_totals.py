"""
fetch/scrape_kworb_totals.py — Scrapes the Kworb all-time totals page for
the global Spotify chart and saves it to data/global_totals.parquet.

The totals page covers every song that ever charted globally since 2014,
with cumulative stream counts, days on chart, peak position, and more.

Usage:
    python fetch/scrape_kworb_totals.py

Output schema:
    artist          str     Artist name(s)
    title           str     Track title
    days            int     Total days on this chart
    days_top10      int     Days spent in the top 10
    peak_pos        int     All-time peak position
    peak_times      int     Number of times at peak
    peak_streams    int     Streams on peak day
    streams_total   int     All-time cumulative streams
    first_charted   date    Estimated date song first appeared (chart_date - days)
    first_year      int     Year derived from first_charted
    artist_url      str     kworb artist page URL
    track_url       str     kworb track page URL
"""

import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL  = "https://kworb.net/spotify/country"
DATA_DIR  = Path(__file__).parent.parent / "data"
DELAY_SEC = 1.2

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SpotifyDashboardBot/1.0)"
    )
}

MARKETS = [
    ("global", "Global"),
]


def _clean_int(text: str) -> int | None:
    if not text:
        return None
    cleaned = re.sub(r"[,\s+]", "", text.strip())
    try:
        return int(cleaned)
    except ValueError:
        return None


def _extract_peak_times(text: str) -> int:
    m = re.search(r"\(x(\d+)\)", text)
    return int(m.group(1)) if m else 1


def fetch_totals(market_code: str) -> pd.DataFrame | None:
    url = f"{BASE_URL}/{market_code}_daily_totals.html"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  ✗ {market_code} totals: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract the date range from the page header
    # "Covers charts from 2014/08/10 to 2026/03/17"
    chart_end_date = date.today()
    date_match = re.search(r"to (\d{4}/\d{2}/\d{2})", soup.get_text())
    if date_match:
        chart_end_date = datetime.strptime(date_match.group(1), "%Y/%m/%d").date()

    tables = soup.find_all("table")
    if not tables:
        print(f"  ✗ {market_code} totals: no table found")
        return None

    table = max(tables, key=lambda t: len(t.find_all("tr")))
    rows  = table.find_all("tr")

    records = []
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 6:
            continue

        # Artist & Title
        artist_title_cell = cells[0]
        links = artist_title_cell.find_all("a")
        if len(links) >= 2:
            artist    = links[0].get_text(strip=True)
            title     = links[1].get_text(strip=True)
            artist_url= links[0].get("href", "")
            track_url = links[1].get("href", "")
        else:
            full = artist_title_cell.get_text(" - ", strip=True)
            parts = full.split(" - ", 1)
            artist = parts[0] if len(parts) > 1 else full
            title  = parts[1] if len(parts) > 1 else ""
            artist_url = track_url = ""

        days         = _clean_int(cells[1].get_text(strip=True))
        days_top10   = _clean_int(cells[2].get_text(strip=True))
        peak_pos     = _clean_int(cells[3].get_text(strip=True))
        peak_times   = _extract_peak_times(cells[4].get_text(strip=True))
        peak_streams = _clean_int(cells[5].get_text(strip=True))
        total        = _clean_int(cells[6].get_text(strip=True)) if len(cells) > 6 else None

        # Estimate first charted date: end_date - days_on_chart
        first_charted = None
        first_year    = None
        if days is not None:
            first_charted = chart_end_date - timedelta(days=days)
            first_year    = first_charted.year

        records.append({
            "market":        market_code,
            "market_name":   "Global" if market_code == "global" else market_code.upper(),
            "artist":        artist,
            "title":         title,
            "days":          days,
            "days_top10":    days_top10,
            "peak_pos":      peak_pos,
            "peak_times":    peak_times,
            "peak_streams":  peak_streams,
            "streams_total": total,
            "first_charted": first_charted,
            "first_year":    first_year,
            "artist_url":    artist_url,
            "track_url":     track_url,
        })

    if not records:
        print(f"  ✗ {market_code} totals: 0 rows parsed")
        return None

    return pd.DataFrame(records)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Fetching totals for {len(MARKETS)} market(s)...\n")

    for i, (code, name) in enumerate(MARKETS):
        print(f"  {name}...", end=" ", flush=True)
        df = fetch_totals(code)
        if df is not None:
            out = DATA_DIR / f"{code}_totals.parquet"
            df.to_parquet(out, index=False)
            print(f"✓  {len(df):,} rows → {out.name}")
        if i < len(MARKETS) - 1:
            time.sleep(DELAY_SEC)

    print(f"\nDone.")


if __name__ == "__main__":
    main()