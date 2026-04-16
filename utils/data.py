"""
utils/data.py — Central data loader for the Spotify Global Charts Dashboard.
Built for the Kworb scraper schema.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

# ── Path resolution ───────────────────────────────────────────────────────────
_HERE    = Path(__file__).parent
DATA_DIR = _HERE.parent / "data"

# ── Column constants ──────────────────────────────────────────────────────────
COL_MARKET        = "market"
COL_MARKET_NAME   = "market_name"
COL_DATE          = "chart_date"
COL_POS           = "pos"
COL_POS_CHANGE    = "pos_change"
COL_ARTIST        = "artist"
COL_TITLE         = "title"
COL_DAYS          = "days_on_chart"
COL_PEAK          = "peak_pos"
COL_PEAK_TIMES    = "peak_times"
COL_STREAMS       = "streams"
COL_STREAMS_DELTA = "streams_delta"
COL_STREAMS_7DAY  = "streams_7day"
COL_STREAMS_7D_DT = "streams_7day_delta"
COL_STREAMS_TOTAL = "streams_total"

# Markets that are aggregates, not plottable countries
NON_COUNTRY_MARKETS = {"global"}


# ── Loader ────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading chart data…")
def load_data() -> pd.DataFrame:
    # Prefer enriched (has album art + Spotify links) → combined → individual files
    enriched = DATA_DIR / "enriched.parquet"
    combined = DATA_DIR / "all_markets.parquet"

    # If no local files exist, try downloading from Supabase first
    if not enriched.exists() and not combined.exists():
        try:
            from utils.supabase_loader import download_if_needed
            download_if_needed(force=False)
        except Exception as e:
            st.warning(f"Supabase download attempted but failed: {e}")

    if enriched.exists():
        df = pd.read_parquet(enriched)
    elif combined.exists():
        df = pd.read_parquet(combined)
    else:
        files = sorted(DATA_DIR.glob("*_daily.parquet"))
        if not files:
            st.error(
                f"No Parquet files found in `{DATA_DIR}`. "
                "Run `python fetch/scrape_kworb.py` first."
            )
            st.stop()
        df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

    # Ensure enrichment columns always exist
    for col in ("album_art_url", "spotify_url"):
        if col not in df.columns:
            df[col] = ""

    # Normalise numeric types
    for col in [COL_STREAMS, COL_STREAMS_DELTA, COL_STREAMS_7DAY,
                COL_STREAMS_7D_DT, COL_STREAMS_TOTAL]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # peak_times null = peaked once
    df[COL_PEAK_TIMES] = (
        pd.to_numeric(df[COL_PEAK_TIMES], errors="coerce").fillna(1).astype(int)
    )
    # streams_delta null = NEW entry, treat as 0
    df[COL_STREAMS_DELTA] = df[COL_STREAMS_DELTA].fillna(0)

    return df


# ── Market helpers ────────────────────────────────────────────────────────────
def get_country_markets(df: pd.DataFrame) -> list[tuple[str, str]]:
    """[(iso2, display_name), ...] excluding non-country rows, sorted by name."""
    seen = (
        df[~df[COL_MARKET].isin(NON_COUNTRY_MARKETS)]
        [[COL_MARKET, COL_MARKET_NAME]]
        .drop_duplicates()
        .sort_values(COL_MARKET_NAME)
    )
    return list(zip(seen[COL_MARKET], seen[COL_MARKET_NAME]))


def get_all_markets(df: pd.DataFrame) -> list[tuple[str, str]]:
    """[(iso2, display_name), ...] with Global first."""
    rows = (
        df[[COL_MARKET, COL_MARKET_NAME]]
        .drop_duplicates()
        .sort_values(COL_MARKET_NAME)
    )
    result       = list(zip(rows[COL_MARKET], rows[COL_MARKET_NAME]))
    global_entry = [(c, n) for c, n in result if c == "global"]
    others       = [(c, n) for c, n in result if c != "global"]
    return global_entry + others


# ── Aggregations ──────────────────────────────────────────────────────────────
def streams_by_country(df: pd.DataFrame) -> pd.DataFrame:
    """One row per country with summed daily streams. Excludes global."""
    country_df = df[~df[COL_MARKET].isin(NON_COUNTRY_MARKETS)]
    return (
        country_df
        .groupby([COL_MARKET, COL_MARKET_NAME], as_index=False)[COL_STREAMS]
        .sum()
        .rename(columns={COL_STREAMS: "total_streams"})
        .sort_values("total_streams", ascending=False)
    )


def top_songs_global(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N from the global chart sorted by streams."""
    return (
        df[df[COL_MARKET] == "global"]
        .sort_values(COL_STREAMS, ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def top_songs_for_market(
    df: pd.DataFrame,
    market: str,
    n: int = 200,
    sort_by: str = COL_POS,
    ascending: bool = True,
) -> pd.DataFrame:
    filtered = df[df[COL_MARKET] == market].copy()
    if sort_by in filtered.columns:
        filtered = filtered.sort_values(sort_by, ascending=ascending)
    return filtered.head(n).reset_index(drop=True)


def momentum_songs(df: pd.DataFrame, market: str = "global", n: int = 50) -> pd.DataFrame:
    """
    Songs with the highest 7-day stream delta — what's surging right now.
    Excludes NEW entries to avoid first-day distortion.
    """
    filtered = df[
        (df[COL_MARKET] == market) &
        (df[COL_POS_CHANGE] != "NEW")
    ].copy()
    filtered["delta_pct"] = (
        filtered[COL_STREAMS_7D_DT]
        / filtered[COL_STREAMS_7DAY].replace(0, pd.NA)
    ) * 100
    return (
        filtered.sort_values(COL_STREAMS_7D_DT, ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner="Loading historical data…")
def load_totals() -> pd.DataFrame | None:
    """
    Loads the global all-time totals Parquet (scraped from Kworb totals page).
    Returns None if the file hasn't been scraped yet.
    """
    path = DATA_DIR / "global_totals.parquet"

    # Try downloading from Supabase if not local
    if not path.exists():
        try:
            from utils.supabase_loader import download_file
            download_file("global_totals.parquet")
        except Exception:
            pass

    if not path.exists():
        return None

    df = pd.read_parquet(path)

    for col in ("days", "days_top10", "peak_pos", "peak_times", "peak_streams", "streams_total"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "first_year" in df.columns:
        df["first_year"] = pd.to_numeric(df["first_year"], errors="coerce").astype("Int64")

    # Merge album art from enriched data if available
    enriched_path = DATA_DIR / "enriched.parquet"
    if enriched_path.exists():
        art = (
            pd.read_parquet(enriched_path)[["artist", "title", "album_art_url", "spotify_url"]]
            .drop_duplicates(subset=["artist", "title"])
        )
        df = df.merge(art, on=["artist", "title"], how="left")
        df["album_art_url"] = df["album_art_url"].fillna("")
        df["spotify_url"]   = df["spotify_url"].fillna("")
    else:
        df["album_art_url"] = ""
        df["spotify_url"]   = ""

    return df