"""
utils/supabase_loader.py — Downloads fresh Parquet from Supabase Storage
into the local data/ directory before the dashboard loads.

Called once at app startup if SUPABASE_URL is set.
"""

import os
from pathlib import Path

import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")   # anon key is fine for public bucket reads
BUCKET       = "spotify-charts"
DATA_DIR     = Path(__file__).parent.parent / "data"

FILES = ["enriched.parquet", "all_markets.parquet"]


def download_if_needed(force: bool = False) -> bool:
    """
    Downloads Parquet files from Supabase if they don't exist locally
    or if force=True. Returns True if any file was downloaded.
    """
    if not SUPABASE_URL:
        return False   # running locally without Supabase — use local files

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = False

    for filename in FILES:
        local_path = DATA_DIR / filename
        if local_path.exists() and not force:
            continue

        url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{filename}"
        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                local_path.write_bytes(resp.content)
                print(f"  Downloaded {filename} from Supabase ({len(resp.content)//1024}KB)")
                downloaded = True
            else:
                print(f"  Warning: could not fetch {filename}: {resp.status_code}")
        except Exception as e:
            print(f"  Warning: Supabase download failed for {filename}: {e}")

    return downloaded