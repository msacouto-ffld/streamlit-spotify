"""
utils/supabase_loader.py — Downloads fresh Parquet from Supabase Storage
into the local data/ directory before the dashboard loads.

Works in both environments:
  - Local: reads from .env via os.getenv()
  - Streamlit Cloud: reads from st.secrets
"""

import os
from pathlib import Path

import requests

BUCKET   = "spotify-charts"
DATA_DIR = Path(__file__).parent.parent / "data"
FILES    = ["enriched.parquet", "all_markets.parquet"]


def _get_secret(key: str) -> str:
    """Reads from st.secrets (Streamlit Cloud) or os.getenv (local)."""
    try:
        import streamlit as st
        return st.secrets.get(key, os.getenv(key, ""))
    except Exception:
        return os.getenv(key, "")


def download_if_needed(force: bool = False) -> bool:
    supabase_url = _get_secret("SUPABASE_URL").rstrip("/")

    if not supabase_url:
        return False   # local run without Supabase — use local files

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = False

    for filename in FILES:
        local_path = DATA_DIR / filename
        if local_path.exists() and not force:
            continue

        url = f"{supabase_url}/storage/v1/object/public/{BUCKET}/{filename}"
        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                local_path.write_bytes(resp.content)
                print(f"  Downloaded {filename} ({len(resp.content)//1024}KB)")
                downloaded = True
            else:
                print(f"  Warning: could not fetch {filename}: {resp.status_code}")
        except Exception as e:
            print(f"  Warning: Supabase download failed for {filename}: {e}")

    return downloaded