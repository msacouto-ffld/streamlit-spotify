"""
fetch/enrich_spotify.py — Enriches the Kworb Parquet data with album art URLs
and Spotify track links using the Spotify Web API search endpoint.

Reads:  data/all_markets.parquet
Writes: data/enriched.parquet  (same rows + album_art_url, spotify_url columns)

Usage:
    python fetch/enrich_spotify.py

Requires in .env:
    SPOTIFY_CLIENT_ID=...
    SPOTIFY_CLIENT_SECRET=...
"""

import os
import time
import base64
from pathlib import Path

import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR    = Path(__file__).parent.parent / "data"
INPUT_FILE  = DATA_DIR / "all_markets.parquet"
OUTPUT_FILE = DATA_DIR / "enriched.parquet"
CACHE_FILE  = DATA_DIR / "_enrich_cache.parquet"   # avoid re-fetching

CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

DELAY_SEC   = 0.15    # ~6 req/s — well within 100 req/s rate limit
BATCH_SIZE  = 50      # print progress every N tracks


# ── Auth ──────────────────────────────────────────────────────────────────────
def get_token() -> str:
    creds  = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    resp   = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {creds}"},
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


# ── Search a single track ─────────────────────────────────────────────────────
def search_track(artist: str, title: str, token: str) -> dict:
    """Returns {album_art_url, spotify_url} or empty strings on failure."""
    query = f'track:"{title}" artist:"{artist}"'
    try:
        resp = requests.get(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": "track", "limit": 1},
            timeout=10,
        )
        if resp.status_code == 401:
            return None   # signal caller to refresh token
        resp.raise_for_status()
        items = resp.json().get("tracks", {}).get("items", [])
        if not items:
            # Fallback: looser search without field operators
            resp2 = requests.get(
                "https://api.spotify.com/v1/search",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": f"{artist} {title}", "type": "track", "limit": 1},
                timeout=10,
            )
            resp2.raise_for_status()
            items = resp2.json().get("tracks", {}).get("items", [])
        if not items:
            return {"album_art_url": "", "spotify_url": ""}
        track   = items[0]
        images  = track.get("album", {}).get("images", [])
        # Pick 300×300 (index 1) if available, else largest
        art_url = images[1]["url"] if len(images) > 1 else (images[0]["url"] if images else "")
        sp_url  = track.get("external_urls", {}).get("spotify", "")
        return {"album_art_url": art_url, "spotify_url": sp_url}
    except Exception:
        return {"album_art_url": "", "spotify_url": ""}


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env")
        return

    print(f"Reading {INPUT_FILE}...")
    df = pd.read_parquet(INPUT_FILE)

    # Deduplicate: one lookup per unique (artist, title) pair
    unique_tracks = (
        df[["artist", "title"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    print(f"Unique tracks to enrich: {len(unique_tracks):,}")

    # Load cache to skip already-fetched tracks
    cache = {}
    if CACHE_FILE.exists():
        cached_df = pd.read_parquet(CACHE_FILE)
        for _, row in cached_df.iterrows():
            cache[(row["artist"], row["title"])] = {
                "album_art_url": row["album_art_url"],
                "spotify_url":   row["spotify_url"],
            }
        print(f"Cache hit: {len(cache):,} tracks already fetched")

    to_fetch = unique_tracks[
        ~unique_tracks.apply(lambda r: (r["artist"], r["title"]) in cache, axis=1)
    ]
    print(f"Fetching {len(to_fetch):,} new tracks...\n")

    token    = get_token()
    results  = dict(cache)   # start with cached values

    for i, (_, row) in enumerate(to_fetch.iterrows(), 1):
        key = (row["artist"], row["title"])
        result = search_track(row["artist"], row["title"], token)

        if result is None:
            # Token expired — refresh and retry
            print("  Token expired, refreshing...")
            token  = get_token()
            result = search_track(row["artist"], row["title"], token)

        results[key] = result or {"album_art_url": "", "spotify_url": ""}

        if i % BATCH_SIZE == 0 or i == len(to_fetch):
            found = sum(1 for v in results.values() if v["album_art_url"])
            print(f"  [{i:4d}/{len(to_fetch)}]  art found: {found:,}")

        time.sleep(DELAY_SEC)

    # ── Save cache ────────────────────────────────────────────────────────────
    cache_rows = [
        {"artist": k[0], "title": k[1], **v}
        for k, v in results.items()
    ]
    pd.DataFrame(cache_rows).to_parquet(CACHE_FILE, index=False)

    # ── Merge back into full dataset ──────────────────────────────────────────
    lookup = pd.DataFrame(cache_rows)
    enriched = df.merge(lookup, on=["artist", "title"], how="left")
    enriched["album_art_url"] = enriched["album_art_url"].fillna("")
    enriched["spotify_url"]   = enriched["spotify_url"].fillna("")

    enriched.to_parquet(OUTPUT_FILE, index=False)

    found_pct = (enriched["album_art_url"] != "").mean() * 100
    print(f"\nDone. Enriched file: {OUTPUT_FILE}")
    print(f"Album art found for {found_pct:.1f}% of rows")


if __name__ == "__main__":
    main()