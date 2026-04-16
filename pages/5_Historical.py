"""
pages/5_Historical.py — All-time global Spotify chart data since 2014,
filterable by year with era comparisons and top song rankings.
"""

import streamlit as st
import plotly.graph_objects as go

from utils.data import load_totals

st.set_page_config(page_title="Historical · Spotify Charts", page_icon="📅", layout="wide")

st.markdown("""
<style>
  .stApp { background-color: #0d0d0d; color: #FFFFFF; }
  [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #1a1a1a; }
  [data-testid="stSidebar"] * { color: #FFFFFF !important; }
  #MainMenu, footer, header { visibility: hidden; }
  [data-testid="stSidebarNav"] a { color: #6b6b6b !important; font-size: 0.85rem; padding: 6px 12px; border-radius: 6px; }
  [data-testid="stSidebarNav"] a:hover { color: #FFFFFF !important; background: #1a1a1a; }
  [data-testid="stSidebarNav"] a[aria-current="page"] { color: #1DB954 !important; background: #0d2b18; font-weight: 600; }
  [data-testid="metric-container"] { background: #141414; border: 1px solid #1f1f1f; border-radius: 10px; padding: 18px 20px; }
  [data-testid="metric-container"] label { color: #6b6b6b !important; font-size: 0.72rem !important; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }
  [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.65rem !important; font-weight: 700; }
  h1 { font-size: 1.8rem !important; font-weight: 800 !important; letter-spacing: -0.03em; }
  h2 { font-size: 1.1rem !important; font-weight: 700 !important; }
  hr { border-color: #1a1a1a; }
  [data-testid="stDataFrame"] th { background: #141414 !important; color: #6b6b6b !important; font-size: 0.72rem !important; text-transform: uppercase; }
  [data-testid="stTabs"] [role="tab"] { color: #6b6b6b; font-weight: 600; font-size: 0.85rem; padding: 8px 16px; }
  [data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: #1DB954; border-bottom: 2px solid #1DB954; }
  .track-row { display:flex;align-items:center;gap:12px;padding:10px 4px;border-bottom:1px solid #1a1a1a; }
  .track-rank { color:#3d3d3d;font-size:0.85rem;width:28px;text-align:right;flex-shrink:0; }
  .track-info { flex:1;min-width:0; }
  .track-title { color:#FFFFFF;font-size:0.88rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
  .track-artist { color:#6b6b6b;font-size:0.76rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
  .track-nums { text-align:right;flex-shrink:0;min-width:110px; }
  .track-streams { color:#FFFFFF;font-size:0.82rem;font-weight:600; }
  .track-sub { color:#6b6b6b;font-size:0.72rem; }
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
df = load_totals()

if df is None:
    st.title("📅 Historical")
    st.info(
        "Historical data hasn't been scraped yet. Run this locally first:\n\n"
        "```bash\n"
        "python fetch/scrape_kworb_totals.py\n"
        "python fetch/upload_supabase.py\n"
        "```"
    )
    st.stop()

# ── Year range ────────────────────────────────────────────────────────────────
min_year = int(df["first_year"].min()) if "first_year" in df.columns else 2014
max_year = int(df["first_year"].max()) if "first_year" in df.columns else 2026

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")

    year_range = st.slider(
        "First charted between",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1,
    )

    sort_options = {
        "All-time streams (highest)": ("streams_total", False),
        "Days on chart (longest)":    ("days",          False),
        "Days in top 10 (most)":      ("days_top10",    False),
        "Peak streams (highest)":     ("peak_streams",  False),
        "Peak position (best)":       ("peak_pos",      True),
    }
    sort_label = st.selectbox("Sort by", list(sort_options.keys()), index=0)
    sort_col, sort_asc = sort_options[sort_label]

    top_n = st.slider("Songs to show", 10, 100, 25, 5)

# ── Filter ────────────────────────────────────────────────────────────────────
filtered = df[
    (df["first_year"] >= year_range[0]) &
    (df["first_year"] <= year_range[1])
].copy()

if sort_col in filtered.columns:
    filtered = filtered.sort_values(sort_col, ascending=sort_asc)

# ── Header ────────────────────────────────────────────────────────────────────
year_label = (
    str(year_range[0]) if year_range[0] == year_range[1]
    else f"{year_range[0]}–{year_range[1]}"
)

st.markdown(f"""
<div style="margin-bottom:24px;">
  <p style="color:#1DB954;font-size:0.72rem;font-weight:700;letter-spacing:0.12em;
            text-transform:uppercase;margin-bottom:6px;">
    Global · {year_label}
  </p>
  <h1>Historical Charts</h1>
  <p style="color:#6b6b6b;font-size:0.9rem;margin-top:6px;">
    Every song that ever charted globally on Spotify, sorted by all-time streams.
    First charted year is estimated from days on chart.
  </p>
</div>
""", unsafe_allow_html=True)

# ── KPI cards ──────────────────────────────────────────────────────────────────
total_streams  = filtered["streams_total"].sum()
unique_artists = filtered["artist"].nunique()
total_songs    = len(filtered)
avg_days       = filtered["days"].mean()
top_row        = filtered.iloc[0] if len(filtered) else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Songs in Selection",   f"{total_songs:,}")
c2.metric("Unique Artists",       f"{unique_artists:,}")
c3.metric("Combined Streams",     f"{total_streams/1_000_000_000:.2f}B")
c4.metric("Avg Days on Chart",    f"{avg_days:.0f}")

st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_tracks, tab_chart, tab_years = st.tabs(["🎵 Top Tracks", "📊 Bar Chart", "📈 By Year"])

# ── Top tracks tab ─────────────────────────────────────────────────────────────
with tab_tracks:
    top = filtered.head(top_n).reset_index(drop=True)
    has_art = "album_art_url" in top.columns and top["album_art_url"].ne("").any()

    if has_art:
        rows_html = ""
        for i, (_, row) in enumerate(top.iterrows(), 1):
            art    = row.get("album_art_url", "")
            sp     = row.get("spotify_url", "")
            title  = str(row["title"])
            artist = str(row["artist"])
            total  = int(row["streams_total"]) if row["streams_total"] else 0
            days   = int(row["days"]) if row["days"] else 0
            peak   = int(row["peak_pos"]) if row["peak_pos"] else "—"
            year   = int(row["first_year"]) if row["first_year"] else "—"

            img_tag = (
                f'<img src="{art}" width="44" height="44" '
                f'style="border-radius:5px;object-fit:cover;flex-shrink:0;">'
                if art else
                '<div style="width:44px;height:44px;background:#1f1f1f;'
                'border-radius:5px;flex-shrink:0;"></div>'
            )
            title_tag = (
                f'<a href="{sp}" target="_blank" style="color:#FFFFFF;text-decoration:none;">{title}</a>'
                if sp else title
            )

            rows_html += f"""
            <div class="track-row">
              <div class="track-rank">{i}</div>
              {img_tag}
              <div class="track-info">
                <div class="track-title">{title_tag}</div>
                <div class="track-artist">{artist}</div>
              </div>
              <div class="track-nums">
                <div class="track-streams">{total/1_000_000_000:.2f}B</div>
                <div class="track-sub">Peak #{peak} · {days}d · {year}</div>
              </div>
            </div>"""

        st.markdown(f'<div style="max-height:600px;overflow-y:auto;">{rows_html}</div>',
                    unsafe_allow_html=True)
    else:
        # Plain table fallback
        display = top[["artist", "title", "streams_total", "days",
                        "days_top10", "peak_pos", "first_year"]].copy()
        display.columns = ["Artist", "Title", "All-Time Streams",
                           "Days", "Days Top 10", "Peak", "First Charted"]
        display["All-Time Streams"] = display["All-Time Streams"].apply(
            lambda x: f"{int(x):,}" if x else "—"
        )
        st.dataframe(display, use_container_width=True, hide_index=True)

# ── Bar chart tab ──────────────────────────────────────────────────────────────
with tab_chart:
    top_bar = filtered.head(min(top_n, 30)).reset_index(drop=True)
    top_bar["_label"] = top_bar["title"].str[:28]
    top_bar["_hover"] = (
        top_bar["artist"] + " — " + top_bar["title"] + "<br>"
        + "Streams: " + top_bar["streams_total"].apply(
            lambda x: f"{x/1_000_000_000:.2f}B" if x else "—"
        ) + "<br>"
        + "Days on chart: " + top_bar["days"].astype(str) + "<br>"
        + "First charted: " + top_bar["first_year"].astype(str)
    )

    n = len(top_bar)
    colors = [
        f"rgba(29,185,84,{0.4 + 0.6 * i / max(n - 1, 1):.2f})"
        for i in range(n)
    ]

    fig = go.Figure(go.Bar(
        x=top_bar["streams_total"],
        y=top_bar["_label"],
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=top_bar["streams_total"].apply(
            lambda x: f"{x/1_000_000_000:.2f}B" if x else ""
        ),
        textposition="outside",
        textfont=dict(color="#6b6b6b", size=10),
        hovertext=top_bar["_hover"],
        hovertemplate="%{hovertext}<extra></extra>",
    ))

    fig.update_layout(
        paper_bgcolor="#0d0d0d",
        plot_bgcolor="#0d0d0d",
        font=dict(color="#FFFFFF", family="Inter, Helvetica, Arial"),
        xaxis=dict(
            tickfont=dict(color="#3d3d3d", size=10),
            gridcolor="#161616",
            showgrid=True,
            tickformat=".2s",
            title=None,
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(color="#FFFFFF", size=12),
        ),
        height=max(400, n * 36),
        margin=dict(l=10, r=80, t=10, b=20),
        bargap=0.28,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── By year tab ────────────────────────────────────────────────────────────────
with tab_years:
    st.markdown(
        "<p style='color:#6b6b6b;font-size:0.85rem;margin-bottom:12px;'>"
        "Total streams accumulated by songs that first charted each year.</p>",
        unsafe_allow_html=True,
    )

    yearly = (
        df.groupby("first_year", as_index=False)["streams_total"]
        .agg(total_streams="sum", song_count="count")
        .dropna(subset=["first_year"])
        .sort_values("first_year")
    )
    yearly["first_year"] = yearly["first_year"].astype(int)

    fig_y = go.Figure()
    fig_y.add_trace(go.Bar(
        x=yearly["first_year"],
        y=yearly["total_streams"],
        marker=dict(
            color=yearly["total_streams"],
            colorscale=[[0, "#0d3a1c"], [0.5, "#1DB954"], [1.0, "#1ed760"]],
            line=dict(width=0),
        ),
        text=yearly["total_streams"].apply(lambda x: f"{x/1_000_000_000:.1f}B"),
        textposition="outside",
        textfont=dict(color="#6b6b6b", size=10),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Total streams: %{y:,.0f}<br>"
            "Songs: %{customdata:,}"
            "<extra></extra>"
        ),
        customdata=yearly["song_count"],
    ))

    fig_y.update_layout(
        paper_bgcolor="#0d0d0d",
        plot_bgcolor="#0d0d0d",
        font=dict(color="#FFFFFF", family="Inter, Helvetica, Arial"),
        xaxis=dict(
            tickfont=dict(color="#b3b3b3", size=11),
            gridcolor="#161616",
            dtick=1,
        ),
        yaxis=dict(
            tickfont=dict(color="#3d3d3d", size=10),
            gridcolor="#161616",
            tickformat=".2s",
        ),
        height=380,
        margin=dict(l=20, r=20, t=20, b=20),
        bargap=0.2,
        showlegend=False,
    )
    st.plotly_chart(fig_y, use_container_width=True)

    # Top song per year
    st.markdown("---")
    st.subheader("Biggest song per year")
    top_per_year = (
        df.dropna(subset=["first_year", "streams_total"])
        .sort_values("streams_total", ascending=False)
        .drop_duplicates(subset=["first_year"])
        .sort_values("first_year", ascending=False)
        [["first_year", "artist", "title", "streams_total", "peak_pos", "days"]]
    )
    top_per_year.columns = ["Year", "Artist", "Title", "Streams", "Peak", "Days"]
    top_per_year["Streams"] = top_per_year["Streams"].apply(lambda x: f"{x/1_000_000_000:.2f}B")
    top_per_year["Year"]    = top_per_year["Year"].astype(int)
    st.dataframe(top_per_year, use_container_width=True, hide_index=True)