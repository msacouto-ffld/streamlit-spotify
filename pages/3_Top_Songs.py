"""
pages/3_Top_Songs.py — Full chart table with search, filters, pagination.
"""

import pandas as pd
import streamlit as st

from utils.data import (
    load_data, get_all_markets,
    COL_MARKET, COL_MARKET_NAME, COL_POS, COL_POS_CHANGE,
    COL_ARTIST, COL_TITLE, COL_STREAMS, COL_STREAMS_DELTA,
    COL_STREAMS_7DAY, COL_STREAMS_TOTAL, COL_DAYS, COL_PEAK,
)

st.set_page_config(page_title="Top Songs · Spotify Charts", page_icon="🎶", layout="wide")

st.markdown("""
<style>
  .stApp { background-color: #0d0d0d; color: #FFFFFF; }
  [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #1a1a1a; }
  [data-testid="stSidebar"] * { color: #FFFFFF !important; }
  #MainMenu, footer, header { visibility: hidden; }
  [data-testid="stSidebarNav"] a { color: #6b6b6b !important; font-size: 0.85rem; padding: 6px 12px; border-radius: 6px; }
  [data-testid="stSidebarNav"] a:hover { color: #FFFFFF !important; background: #1a1a1a; }
  [data-testid="stSidebarNav"] a[aria-current="page"] { color: #1DB954 !important; background: #0d2b18; font-weight: 600; }
  [data-baseweb="select"] > div { background: #141414 !important; border-color: #2a2a2a !important; color: #FFFFFF !important; border-radius: 8px !important; }
  [data-testid="stTextInput"] input { background: #141414 !important; color: #FFFFFF !important; border-color: #2a2a2a !important; border-radius: 8px !important; }
  h1 { font-size: 1.8rem !important; font-weight: 800 !important; letter-spacing: -0.03em; }
  h2 { font-size: 1.1rem !important; font-weight: 700 !important; }
  hr { border-color: #1a1a1a; }
  [data-testid="stDataFrame"] th { background: #141414 !important; color: #6b6b6b !important; font-size: 0.72rem !important; text-transform: uppercase; }
  [data-testid="stDownloadButton"] > button { background: transparent; color: #1DB954 !important; border: 1px solid #1DB954 !important; border-radius: 500px; font-weight: 600; font-size: 0.82rem; }
  [data-testid="stDownloadButton"] > button:hover { background: #0d2b18 !important; }
</style>
""", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────
df = load_data()
all_markets   = get_all_markets(df)
market_labels = {name: code for code, name in all_markets}
chart_date    = df["chart_date"].max()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")

    selected_name   = st.selectbox("Market", list(market_labels.keys()), index=0)
    selected_market = market_labels[selected_name]

    sort_options = {
        "Chart position (1 → 200)":   (COL_POS,           True),
        "Daily streams (high → low)":  (COL_STREAMS,       False),
        "7-Day streams (high → low)":  (COL_STREAMS_7DAY,  False),
        "All-time total (high → low)": (COL_STREAMS_TOTAL, False),
        "Days on chart (longest)":     (COL_DAYS,          False),
        "Peak position (best first)":  (COL_PEAK,          True),
    }
    sort_label     = st.selectbox("Sort by", list(sort_options.keys()), index=0)
    sort_col, sort_asc = sort_options[sort_label]

    page_size = st.select_slider("Rows per page", [10, 25, 50, 100, 200], value=25)

# ── Search ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:24px;">
  <p style="color:#1DB954;font-size:0.72rem;font-weight:700;letter-spacing:0.12em;
            text-transform:uppercase;margin-bottom:6px;">
    {selected_name} · {chart_date.strftime("%B %d, %Y")}
  </p>
  <h1>Top Songs</h1>
</div>
""", unsafe_allow_html=True)

search = st.text_input("", placeholder="🔍  Search by title or artist…")

# ── Filter ────────────────────────────────────────────────────────────────────
filtered = df[df[COL_MARKET] == selected_market].copy()

if search.strip():
    q    = search.strip().lower()
    mask = (
        filtered[COL_TITLE].str.lower().str.contains(q, na=False) |
        filtered[COL_ARTIST].str.lower().str.contains(q, na=False)
    )
    filtered = filtered[mask]

if sort_col in filtered.columns:
    filtered = filtered.sort_values(sort_col, ascending=sort_asc)

total_rows  = len(filtered)
total_pages = max(1, (total_rows + page_size - 1) // page_size)

# ── Pagination controls ────────────────────────────────────────────────────────
info_col, page_col, dl_col = st.columns([3, 1, 1])
with info_col:
    st.markdown(
        f"<span style='color:#6b6b6b;font-size:0.85rem;'>"
        f"<b style='color:#FFFFFF;'>{total_rows:,}</b> songs"
        f"{'  ·  filtered' if search else ''}"
        f"</span>",
        unsafe_allow_html=True,
    )
with page_col:
    page_num = st.number_input(
        f"of {total_pages}", min_value=1, max_value=total_pages,
        value=1, step=1, label_visibility="visible",
    )
with dl_col:
    csv = filtered[
        [COL_POS, COL_POS_CHANGE, COL_TITLE, COL_ARTIST,
         COL_STREAMS, COL_STREAMS_DELTA, COL_STREAMS_7DAY,
         COL_STREAMS_TOTAL, COL_DAYS, COL_PEAK]
    ].to_csv(index=False)
    st.download_button(
        "⬇ Export CSV", csv,
        file_name=f"spotify_{selected_market}_{chart_date}.csv",
        mime="text/csv",
    )

st.markdown("---")

# ── Page slice ────────────────────────────────────────────────────────────────
start   = (page_num - 1) * page_size
page_df = filtered.iloc[start : start + page_size].reset_index(drop=True)

# ── Track list with album art (if available) or plain table ───────────────────
has_art = "album_art_url" in page_df.columns and page_df["album_art_url"].ne("").any()

if has_art:
    st.markdown("""
    <style>
      .track-row { display:flex;align-items:center;gap:12px;padding:10px 4px;
                   border-bottom:1px solid #1a1a1a; }
      .track-rank { color:#3d3d3d;font-size:0.85rem;width:28px;text-align:right;flex-shrink:0; }
      .track-chg  { font-size:0.75rem;width:32px;text-align:center;flex-shrink:0; }
      .track-info { flex:1;min-width:0; }
      .track-title { color:#FFFFFF;font-size:0.88rem;font-weight:600;
                     white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
      .track-artist { color:#6b6b6b;font-size:0.76rem;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
      .track-nums { text-align:right;flex-shrink:0;min-width:100px; }
      .track-streams { color:#FFFFFF;font-size:0.82rem;font-weight:600; }
      .track-sub { color:#6b6b6b;font-size:0.72rem; }
    </style>
    """, unsafe_allow_html=True)

    rows_html = ""
    for _, row in page_df.iterrows():
        art    = row.get("album_art_url", "")
        sp     = row.get("spotify_url", "")
        title  = str(row[COL_TITLE])
        artist = str(row[COL_ARTIST])
        pos    = int(row[COL_POS])
        chg    = str(row[COL_POS_CHANGE])
        strms  = f"{int(row[COL_STREAMS]):,}"
        delta  = int(row[COL_STREAMS_DELTA])
        days   = int(row[COL_DAYS])
        total  = int(row[COL_STREAMS_TOTAL])

        delta_str = f"{delta:+,}" if delta != 0 else "NEW"
        delta_col = "#1DB954" if delta >= 0 else "#e84c4c"
        chg_col   = "#1DB954" if chg.startswith("+") else ("#e84c4c" if chg.startswith("-") else "#6b6b6b")

        img_tag = (
            f'<img src="{art}" width="44" height="44" '
            f'style="border-radius:5px;object-fit:cover;flex-shrink:0;">'
            if art else
            '<div style="width:44px;height:44px;background:#1f1f1f;'
            'border-radius:5px;flex-shrink:0;"></div>'
        )
        title_tag = (
            f'<a href="{sp}" target="_blank" style="color:#FFFFFF;'
            f'text-decoration:none;">{title}</a>'
            if sp else title
        )

        rows_html += f"""
        <div class="track-row">
          <div class="track-rank">{pos}</div>
          <div class="track-chg" style="color:{chg_col};">{chg}</div>
          {img_tag}
          <div class="track-info">
            <div class="track-title">{title_tag}</div>
            <div class="track-artist">{artist}</div>
          </div>
          <div class="track-nums">
            <div class="track-streams">{strms}</div>
            <div style="color:{delta_col};font-size:0.72rem;">{delta_str}</div>
            <div class="track-sub">{days}d · {total/1_000_000:.1f}M total</div>
          </div>
        </div>"""

    st.markdown(rows_html, unsafe_allow_html=True)

else:
    # Plain table fallback when enrichment hasn't been run yet
    display = page_df[[
        COL_POS, COL_POS_CHANGE, COL_TITLE, COL_ARTIST,
        COL_STREAMS, COL_STREAMS_DELTA, COL_STREAMS_7DAY,
        COL_STREAMS_TOTAL, COL_DAYS, COL_PEAK,
    ]].copy()
    display.columns = [
        "#", "Chg", "Title", "Artist",
        "Streams", "vs Yesterday", "7-Day",
        "All-Time Total", "Days", "Peak",
    ]
    display["Streams"]        = display["Streams"].apply(lambda x: f"{int(x):,}")
    display["vs Yesterday"]   = display["vs Yesterday"].apply(
        lambda x: f"{int(x):+,}" if x != 0 else "NEW"
    )
    display["7-Day"]          = display["7-Day"].apply(lambda x: f"{int(x):,}")
    display["All-Time Total"] = display["All-Time Total"].apply(lambda x: f"{int(x):,}")
    st.dataframe(display, use_container_width=True, hide_index=True)

# ── Footer note ────────────────────────────────────────────────────────────────
st.markdown(
    f"<p style='color:#3d3d3d;font-size:0.75rem;margin-top:8px;'>"
    f"Page {page_num} of {total_pages}  ·  "
    f"{total_rows} results  ·  Data from Kworb.net</p>",
    unsafe_allow_html=True,
)