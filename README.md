# Spotify Global Charts Dashboard

An interactive dashboard tracking real-time Spotify streaming data across 72 markets worldwide. Built with Streamlit and Plotly, powered by daily-refreshed data from Kworb and enriched with album art via the Spotify Web API.

## What it does

Four pages give different views into what the world is listening to:

- **Overview** — KPI summary cards and a top-N bar chart for any market, with daily stream deltas and album art for the #1 song
- **World Map** — Choropleth of total daily streams across all 72 tracked countries, with each country's #1 song on hover
- **Top Songs** — Full paginated chart table with search, multi-column sorting, and CSV export
- **Momentum** — Songs ranked by 7-day stream growth, with rising/falling tabs and a scatter plot of volume vs acceleration

Data refreshes automatically every morning via a GitHub Actions workflow.

## Data sources

**[Kworb.net](https://kworb.net/spotify/)** — The primary data source. Kworb aggregates Spotify's official daily and weekly chart data and publishes it for all available markets. For each country it provides chart position, daily streams, 7-day streams, stream deltas, days on chart, peak position, and all-time totals. Updated daily.

**[Spotify Web API](https://developer.spotify.com/documentation/web-api)** — Used for enrichment only (not chart data). The `search` endpoint is queried once per unique track to retrieve album art URLs and direct Spotify links. Results are cached locally so the API is not called on every refresh.

## Tech stack

| Layer | Tools |
|---|---|
| Dashboard | Streamlit, Plotly |
| Data processing | Pandas, PyArrow |
| Scraping | Requests, BeautifulSoup4 |
| Storage | Supabase Storage |
| Automation | GitHub Actions |
| Language | Python 3.11 |

## Project structure

```
├── app.py                        # Landing page and global CSS
├── pages/
│   ├── 1_Overview.py
│   ├── 2_World_Map.py
│   ├── 3_Top_Songs.py
│   └── 4_Momentum.py
├── utils/
│   ├── data.py                   # Central data loader and aggregations
│   └── supabase_loader.py        # Downloads fresh Parquet from Supabase on startup
├── fetch/
│   ├── scrape_kworb.py           # Scrapes all 72 markets from Kworb
│   ├── enrich_spotify.py         # Adds album art via Spotify API (run locally)
│   └── upload_supabase.py        # Uploads Parquet files to Supabase Storage
├── .github/
│   └── workflows/
│       └── daily_refresh.yml     # Scheduled GitHub Actions pipeline
└── .streamlit/
    └── config.toml               # Dark theme configuration
```

## Setup

### Prerequisites

- Python 3.10+
- A [Spotify Developer](https://developer.spotify.com) app (free) for album art enrichment
- A [Supabase](https://supabase.com) project (free tier) for cloud storage
- A [GitHub](https://github.com) account for automated daily refresh

### Local setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/YOUR_USERNAME/streamlit-spotify.git
   cd streamlit-spotify
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** in the project root:
   ```
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your_service_role_key
   SUPABASE_ANON_KEY=your_anon_key
   ```

4. **Fetch chart data**
   ```bash
   python fetch/scrape_kworb.py
   ```

5. **Enrich with album art** (takes ~20 min on first run, cached after that)
   ```bash
   python fetch/enrich_spotify.py
   ```

6. **Run the app**
   ```bash
   streamlit run app.py
   ```

### Supabase setup

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **Storage → New bucket**, name it `spotify-charts`, set to Public
3. Copy your Project URL and API keys from **Settings → API** into your `.env`
4. Upload your data:
   ```bash
   python fetch/upload_supabase.py
   ```

### GitHub Actions (automated daily refresh)

Add the following secrets to your GitHub repo under **Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service_role key (for uploads) |

The workflow runs every day at 7am UTC. You can also trigger it manually from the Actions tab.

> **Note:** Spotify API credentials are not needed in GitHub Actions — album art is cached locally and committed to the repo. Only re-run `enrich_spotify.py` locally when you want to pick up art for newly charting songs.

### Deploying to Streamlit Community Cloud

1. Push your repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **New app**, select your repo, branch `main`, main file `app.py`
4. Open **Advanced settings** and add your secrets:
   ```toml
   SUPABASE_URL = "https://your-project.supabase.co"
   SUPABASE_ANON_KEY = "your_anon_key"
   ```
5. Click **Deploy**
