"""
pages/6_Artist.py — Artist deep-dive page.
Search for any artist and see their global footprint: total streams,
markets charting, top song, streams by market, and full song table.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.supabase_loader import download_if_needed
from utils.data import load_data

st.set_page_config(page_title="Artist · Spotify World", page_icon="🎤", layout="wide")

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .metric-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
  }
  .metric-label {
    color: #888;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
  }
  .metric-value {
    color: #1DB954;
    font-size: 28px;
    font-weight: 700;
  }
  .metric-sub {
    color: #aaa;
    font-size: 13px;
    margin-top: 4px;
  }
  .artist-header {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 24px 0 8px 0;
  }
  .artist-name {
    font-size: 42px;
    font-weight: 800;
    color: #fff;
    line-height: 1;
  }
  .top-song-card {
    background: linear-gradient(135deg, #1a1a1a 0%, #111 100%);
    border: 1px solid #1DB954;
    border-radius: 12px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
download_if_needed()

@st.cache_data(ttl=3600)
def get_data():
    return load_data()

df = get_data()

# ── Sidebar: artist search ────────────────────────────────────────────────────
st.sidebar.header("🎤 Artist Search")

all_artists = sorted(df["artist"].dropna().unique())
selected_artist = st.sidebar.selectbox(
    "Choose an artist",
    options=all_artists,
    index=0,
    placeholder="Type to search...",
)

# ── Filter to artist ──────────────────────────────────────────────────────────
adf = df[df["artist"] == selected_artist].copy()

if adf.empty:
    st.warning("No data found for this artist.")
    st.stop()

# ── Key metrics ───────────────────────────────────────────────────────────────
total_streams   = adf["streams"].sum()
total_7day      = adf["streams_7day"].sum()
markets_count   = adf["market_name"].nunique()
songs_count     = adf["title"].nunique()
best_pos        = adf["pos"].min()
best_pos_market = adf.loc[adf["pos"].idxmin(), "market_name"]

# Top song by streams
top_song_row = adf.sort_values("streams", ascending=False).iloc[0]

# ── Header ────────────────────────────────────────────────────────────────────
col_img, col_title = st.columns([1, 6])
with col_img:
    if pd.notna(top_song_row.get("album_art_url")) and top_song_row["album_art_url"]:
        st.image(top_song_row["album_art_url"], width=90)
with col_title:
    st.markdown(f'<div class="artist-name">{selected_artist}</div>', unsafe_allow_html=True)
    st.caption(f"Chart data as of {adf['chart_date'].iloc[0]}")

st.divider()

# ── Metric cards ──────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

def metric_card(col, label, value, sub=""):
    col.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{value}</div>
      {'<div class="metric-sub">' + sub + '</div>' if sub else ''}
    </div>
    """, unsafe_allow_html=True)

metric_card(c1, "Daily Streams",   f"{total_streams:,.0f}")
metric_card(c2, "7-Day Streams",   f"{total_7day:,.0f}")
metric_card(c3, "Markets Charting", str(markets_count))
metric_card(c4, "Songs Charting",  str(songs_count))
metric_card(c5, "Best Position",   f"#{best_pos}", best_pos_market)

st.markdown("<br>", unsafe_allow_html=True)

# ── Top song spotlight ────────────────────────────────────────────────────────
st.subheader("🏆 Top Song Today")

tc1, tc2 = st.columns([1, 5])
with tc1:
    if pd.notna(top_song_row.get("album_art_url")) and top_song_row["album_art_url"]:
        st.image(top_song_row["album_art_url"], width=120)
with tc2:
    song_link = top_song_row.get("spotify_url", "")
    if song_link:
        st.markdown(f"### [{top_song_row['title']}]({song_link})")
    else:
        st.markdown(f"### {top_song_row['title']}")
    st.markdown(
        f"**#{int(top_song_row['pos'])}** in {top_song_row['market_name']}  ·  "
        f"**{int(top_song_row['streams']):,}** daily streams  ·  "
        f"**{int(top_song_row['days_on_chart'])}** days on chart  ·  "
        f"Peak **#{int(top_song_row['peak_pos'])}**"
    )

st.divider()

# ── Streams by market ─────────────────────────────────────────────────────────
st.subheader("🌍 Streams by Market")

# Aggregate per market (sum across songs)
market_agg = (
    adf.groupby("market_name", as_index=False)
       .agg(streams=("streams", "sum"), songs=("title", "nunique"))
       .sort_values("streams", ascending=True)
)

fig_market = px.bar(
    market_agg,
    x="streams",
    y="market_name",
    orientation="h",
    color="streams",
    color_continuous_scale=[[0, "#0d4a20"], [1, "#1DB954"]],
    labels={"streams": "Daily Streams", "market_name": "Market"},
    custom_data=["songs"],
)
fig_market.update_traces(
    hovertemplate="<b>%{y}</b><br>%{x:,.0f} streams<br>%{customdata[0]} song(s) charting<extra></extra>"
)
fig_market.update_layout(
    plot_bgcolor="#0e0e0e",
    paper_bgcolor="#0e0e0e",
    font_color="#ccc",
    coloraxis_showscale=False,
    margin=dict(l=0, r=20, t=10, b=10),
    height=max(300, len(market_agg) * 28),
    xaxis=dict(gridcolor="#222"),
    yaxis=dict(gridcolor="#222"),
)
st.plotly_chart(fig_market, use_container_width=True)

# ── Per-song breakdown ────────────────────────────────────────────────────────
st.subheader("🎵 All Charting Songs")

song_agg = (
    adf.groupby("title", as_index=False)
       .agg(
           markets=("market_name", "nunique"),
           total_streams=("streams", "sum"),
           best_pos=("pos", "min"),
           peak_pos=("peak_pos", "min"),
           days_on_chart=("days_on_chart", "max"),
           album_art_url=("album_art_url", "first"),
           spotify_url=("spotify_url", "first"),
       )
       .sort_values("total_streams", ascending=False)
)

for _, row in song_agg.iterrows():
    sc1, sc2, sc3, sc4, sc5, sc6 = st.columns([1, 4, 2, 2, 2, 2])
    with sc1:
        if pd.notna(row.get("album_art_url")) and row["album_art_url"]:
            st.image(row["album_art_url"], width=48)
    with sc2:
        if row.get("spotify_url"):
            st.markdown(f"**[{row['title']}]({row['spotify_url']})**")
        else:
            st.markdown(f"**{row['title']}**")
    with sc3:
        st.metric("Streams", f"{int(row['total_streams']):,}")
    with sc4:
        st.metric("Markets", int(row["markets"]))
    with sc5:
        st.metric("Best Pos", f"#{int(row['best_pos'])}")
    with sc6:
        st.metric("Peak", f"#{int(row['peak_pos'])}")
    st.divider()