"""
pages/1_Overview.py — Global KPI summary + top-N bar chart + album art.
"""

import streamlit as st
import plotly.graph_objects as go

from utils.data import (
    load_data, get_all_markets, top_songs_for_market,
    COL_TITLE, COL_ARTIST, COL_STREAMS, COL_STREAMS_DELTA,
    COL_STREAMS_7DAY, COL_POS, COL_POS_CHANGE, COL_DAYS,
    COL_PEAK, COL_MARKET, COL_MARKET_NAME,
)

st.set_page_config(page_title="Overview · Spotify Charts", page_icon="📊", layout="wide")

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
  [data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 0.8rem !important; }
  h1 { font-size: 1.8rem !important; font-weight: 800 !important; letter-spacing: -0.03em; }
  h2 { font-size: 1.1rem !important; font-weight: 700 !important; }
  hr { border-color: #1a1a1a; }
  [data-testid="stExpander"] { background: #141414; border: 1px solid #1f1f1f; border-radius: 10px; }
  [data-testid="stDataFrame"] th { background: #141414 !important; color: #6b6b6b !important; font-size: 0.72rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
  .track-row { display:flex; align-items:center; gap:12px; padding:8px 0; border-bottom:1px solid #1a1a1a; }
  .track-rank { color:#3d3d3d; font-size:0.85rem; width:24px; text-align:right; flex-shrink:0; }
  .track-info { flex:1; min-width:0; }
  .track-title { color:#FFFFFF; font-size:0.9rem; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .track-artist { color:#6b6b6b; font-size:0.78rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .track-streams { color:#1DB954; font-size:0.82rem; font-weight:600; flex-shrink:0; }
</style>
""", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────
df = load_data()
all_markets = get_all_markets(df)
market_labels = {name: code for code, name in all_markets}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    selected_name   = st.selectbox("Market", list(market_labels.keys()), index=0)
    selected_market = market_labels[selected_name]
    top_n = st.slider("Songs to show", 5, 50, 10, 5)

# ── Filtered data ──────────────────────────────────────────────────────────────
chart_df   = top_songs_for_market(df, selected_market, sort_by=COL_POS, ascending=True)
chart_date = df["chart_date"].max()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:24px;">
  <p style="color:#1DB954;font-size:0.72rem;font-weight:700;letter-spacing:0.12em;
            text-transform:uppercase;margin-bottom:6px;">
    {selected_name} · {chart_date.strftime("%B %d, %Y")}
  </p>
  <h1>Overview</h1>
</div>
""", unsafe_allow_html=True)

# ── KPI cards ─────────────────────────────────────────────────────────────────
total_streams  = int(chart_df[COL_STREAMS].sum())
unique_artists = chart_df[COL_ARTIST].nunique()
avg_days       = chart_df[COL_DAYS].mean()
total_delta    = int(chart_df[COL_STREAMS_DELTA].sum())
top_row        = chart_df.iloc[0] if len(chart_df) else None
top_song       = top_row[COL_TITLE] if top_row is not None else "—"
top_artist     = top_row[COL_ARTIST] if top_row is not None else "—"
top_art        = top_row["album_art_url"] if top_row is not None and "album_art_url" in chart_df.columns else ""

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Daily Streams",     f"{total_streams/1_000_000:.1f}M",
          delta=f"{total_delta/1_000_000:+.1f}M vs yesterday")
c2.metric("Songs Charting",    f"{len(chart_df)}")
c3.metric("Unique Artists",    f"{unique_artists}")
c4.metric("Avg Days on Chart", f"{avg_days:.0f}")

# #1 card: show album art if available
with c5:
    if top_art:
        st.markdown(f"""
        <div style="background:#141414;border:1px solid #1f1f1f;border-radius:10px;
                    padding:14px 16px;display:flex;align-items:center;gap:12px;">
          <img src="{top_art}" width="52" height="52"
               style="border-radius:6px;object-fit:cover;flex-shrink:0;">
          <div style="min-width:0;">
            <div style="color:#6b6b6b;font-size:0.68rem;text-transform:uppercase;
                        letter-spacing:0.1em;font-weight:600;margin-bottom:4px;">#1 Song</div>
            <div style="color:#FFFFFF;font-weight:700;font-size:0.9rem;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
              {top_song[:24]}{"…" if len(top_song) > 24 else ""}
            </div>
            <div style="color:#6b6b6b;font-size:0.78rem;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
              {top_artist}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.metric("#1 Song",
                  top_song[:22] + ("…" if len(top_song) > 22 else ""),
                  delta=top_artist)

st.markdown("---")

# ── Top-N bar chart ────────────────────────────────────────────────────────────
top = chart_df.head(top_n).copy()
top["_label"]     = top[COL_TITLE].str[:32]
top["_hover"]     = top[COL_ARTIST] + " — " + top[COL_TITLE]
top["_delta_str"] = top[COL_STREAMS_DELTA].apply(
    lambda x: f"{x/1000:+.0f}K" if abs(x) >= 1000 else f"{x:+.0f}"
)

bar_colors = []
for _, row in top.iterrows():
    if row[COL_POS_CHANGE] == "NEW":
        bar_colors.append("#1DB954")
    else:
        ratio = 1 - (row[COL_POS] - 1) / max(top_n - 1, 1)
        g = int(80 + ratio * 100)
        bar_colors.append(f"rgb(0, {g}, 50)")

fig = go.Figure(go.Bar(
    x=top[COL_STREAMS],
    y=top["_label"],
    orientation="h",
    marker=dict(color=bar_colors, line=dict(width=0)),
    text=top[COL_STREAMS].apply(lambda x: f"{x/1_000_000:.2f}M"),
    textposition="outside",
    textfont=dict(color="#6b6b6b", size=11),
    customdata=top[["_hover", "_delta_str", COL_POS_CHANGE, COL_DAYS]].values,
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "Streams: %{x:,.0f}<br>"
        "vs Yesterday: %{customdata[1]}<br>"
        "Position change: %{customdata[2]}<br>"
        "Days on chart: %{customdata[3]}"
        "<extra></extra>"
    ),
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
    height=max(380, top_n * 44),
    margin=dict(l=10, r=80, t=10, b=20),
    bargap=0.3,
)

st.subheader(f"Top {top_n} · {selected_name}")
st.plotly_chart(fig, use_container_width=True)

st.markdown("""
<div style="display:flex;gap:20px;margin-top:-8px;margin-bottom:16px;">
  <span style="color:#1DB954;font-size:0.75rem;font-weight:600;">■ NEW entry</span>
  <span style="color:#6b6b6b;font-size:0.75rem;">■ Returning / holding</span>
</div>
""", unsafe_allow_html=True)

# ── Track list with album art ──────────────────────────────────────────────────
with st.expander("View full list with artwork", expanded=False):
    has_art = "album_art_url" in top.columns and top["album_art_url"].ne("").any()
    if has_art:
        rows_html = ""
        for _, row in top.iterrows():
            art   = row.get("album_art_url", "")
            sp    = row.get("spotify_url", "")
            title = row[COL_TITLE]
            artist= row[COL_ARTIST]
            strms = f"{int(row[COL_STREAMS]):,}"
            delta = int(row[COL_STREAMS_DELTA])
            delta_str = f"{delta:+,}" if delta != 0 else "NEW"
            delta_col = "#1DB954" if delta >= 0 else "#e84c4c"

            img_tag = (
                f'<img src="{art}" width="44" height="44" '
                f'style="border-radius:4px;object-fit:cover;flex-shrink:0;">'
                if art else
                '<div style="width:44px;height:44px;background:#282828;border-radius:4px;flex-shrink:0;"></div>'
            )
            title_tag = (
                f'<a href="{sp}" target="_blank" style="color:#FFFFFF;text-decoration:none;">{title}</a>'
                if sp else title
            )
            rows_html += f"""
            <div class="track-row">
              <div class="track-rank">{int(row[COL_POS])}</div>
              {img_tag}
              <div class="track-info">
                <div class="track-title">{title_tag}</div>
                <div class="track-artist">{artist}</div>
              </div>
              <div style="text-align:right;flex-shrink:0;">
                <div class="track-streams">{strms}</div>
                <div style="color:{delta_col};font-size:0.72rem;">{delta_str}</div>
              </div>
            </div>"""

        st.markdown(f'<div style="max-height:520px;overflow-y:auto;">{rows_html}</div>',
                    unsafe_allow_html=True)
    else:
        # Fallback plain table if no art yet
        display = top[[COL_POS, COL_POS_CHANGE, COL_TITLE, COL_ARTIST,
                       COL_STREAMS, COL_STREAMS_DELTA, COL_STREAMS_7DAY,
                       COL_DAYS, COL_PEAK]].copy()
        display.columns = ["#", "Chg", "Title", "Artist", "Streams",
                           "vs Yesterday", "7-Day", "Days", "Peak"]
        display["Streams"]      = display["Streams"].apply(lambda x: f"{int(x):,}")
        display["vs Yesterday"] = display["vs Yesterday"].apply(
            lambda x: f"{int(x):+,}" if x != 0 else "NEW"
        )
        display["7-Day"]        = display["7-Day"].apply(lambda x: f"{int(x):,}")
        st.dataframe(display, use_container_width=True, hide_index=True)