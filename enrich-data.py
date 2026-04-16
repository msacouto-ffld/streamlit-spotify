import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import os
import pandas as pd
import glob
import time

load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
))

DATA_DIR = "data/"
OUTPUT_DIR = "data/enriched/"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_track_id(uri):
    return uri.replace("spotify:track:", "").strip()


def get_track_details(track_ids):
    results = []
    for i in range(0, len(track_ids), 50):
        batch = track_ids[i:i+50]
        try:
            response = sp.tracks(batch)
            for track in response["tracks"]:
                if track:
                    results.append({
                        "track_id": track["id"],
                        "popularity": track["popularity"],
                        "album_name": track["album"]["name"],
                        "album_image": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
                        "release_date": track["album"]["release_date"],
                        "duration_ms": track["duration_ms"],
                        "explicit": track["explicit"]
                    })
        except Exception as e:
            print("  Warning: could not fetch batch - " + str(e))
        time.sleep(0.2)
    return results


def get_artist_genre(artist_name):
    try:
        result = sp.search(q="artist:" + artist_name, type="artist", limit=1)
        items = result["artists"]["items"]
        if items and items[0]["genres"]:
            return items[0]["genres"][0]
        return "unknown"
    except Exception:
        return "unknown"


csv_files = glob.glob(DATA_DIR + "*.csv")
print("Found " + str(len(csv_files)) + " CSV files\n")

for filepath in csv_files:
    filename = os.path.basename(filepath)
    print("Processing " + filename + "...")

    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    df["track_id"] = df["uri"].apply(extract_track_id)
    df["streams"] = pd.to_numeric(
        df["streams"].astype(str).str.replace(",", ""), errors="coerce"
    )

    parts = filename.split("-")
    country_code = parts[1].upper()
    df["country"] = country_code

    print("  Fetching track details for " + str(len(df)) + " tracks...")
    details = get_track_details(df["track_id"].tolist())
    details_df = pd.DataFrame(details)
    if not details_df.empty:
        df = df.merge(details_df, on="track_id", how="left")

    print("  Fetching genres for top 20 unique artists...")
    unique_artists = df["artist_names"].head(20).tolist()
    genre_map = {}
    for artist in unique_artists:
        primary = artist.split(",")[0].strip()
        if primary not in genre_map:
            genre_map[primary] = get_artist_genre(primary)
            time.sleep(0.15)

    def assign_genre(artist_names):
        primary = str(artist_names).split(",")[0].strip()
        return genre_map.get(primary, "unknown")

    df["genre"] = df["artist_names"].apply(assign_genre)

    out_path = OUTPUT_DIR + filename.replace(".csv", ".parquet")
    df.to_parquet(out_path, index=False)
    print("  Saved to " + out_path + "\n")

print("All done! Enriched files saved to data/enriched/")
print("\nColumns in output:")
sample = pd.read_parquet(out_path)
print(list(sample.columns))