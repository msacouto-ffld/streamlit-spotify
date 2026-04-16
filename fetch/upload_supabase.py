"""
fetch/upload_supabase.py — Uploads fresh Parquet files to Supabase Storage.

Called by the GitHub Actions workflow after scraping + enriching.

Requires in .env (or GitHub Actions secrets):
    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY=eyJ...   (use service_role key, not anon key)
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL     = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY     = os.getenv("SUPABASE_SERVICE_KEY", "")
BUCKET           = "spotify-charts"          # create this bucket in Supabase dashboard
DATA_DIR         = Path(__file__).parent.parent / "data"

FILES_TO_UPLOAD = [
    "enriched.parquet",
    "all_markets.parquet",
]


def upload_file(local_path: Path, remote_name: str) -> bool:
    """Uploads a file to Supabase Storage, overwriting if it exists."""
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{remote_name}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/octet-stream",
        "x-upsert": "true",    # overwrite existing file
    }
    with open(local_path, "rb") as f:
        resp = requests.put(url, headers=headers, data=f, timeout=60)

    if resp.status_code in (200, 201):
        print(f"  ✓ {remote_name}")
        return True
    else:
        print(f"  ✗ {remote_name}: {resp.status_code} {resp.text[:120]}")
        return False


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    print(f"Uploading to Supabase bucket '{BUCKET}'...\n")
    ok, fail = 0, 0
    for filename in FILES_TO_UPLOAD:
        path = DATA_DIR / filename
        if not path.exists():
            print(f"  — {filename} not found, skipping")
            continue
        if upload_file(path, filename):
            ok += 1
        else:
            fail += 1

    print(f"\nDone. {ok} uploaded, {fail} failed.")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()