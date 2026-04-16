"""
pages/2_World_Map.py — Choropleth of daily Spotify streams across 72 markets.
"""

import streamlit as st
import plotly.graph_objects as go

from utils.data import (
    load_data, streams_by_country, top_songs_for_market,
    COL_MARKET, COL_MARKET_NAME, COL_STREAMS,
    COL_TITLE, COL_ARTIST, COL_POS,
)

st.set_page_config(page_title="World Map · Spotify Charts", page_icon="🌍", layout="wide")

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
  h1 { font-size: 1.8rem !important; font-weight: 800 !important; letter-spacing: -0.03em; }
  h2 { font-size: 1.1rem !important; font-weight: 700 !important; }
  hr { border-color: #1a1a1a; }
  [data-testid="stDataFrame"] th { background: #141414 !important; color: #6b6b6b !important; font-size: 0.72rem !important; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────
df     = load_data()
agg    = streams_by_country(df)
chart_date = df["chart_date"].max()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Options")
    projection = st.selectbox(
        "Map projection",
        ["natural earth", "equirectangular", "orthographic", "robinson"],
        index=0,
    )
    show_table = st.checkbox("Show country rankings below map", value=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:24px;">
  <p style="color:#1DB954;font-size:0.72rem;font-weight:700;letter-spacing:0.12em;
            text-transform:uppercase;margin-bottom:6px;">
    72 Markets · {chart_date.strftime("%B %d, %Y")}
  </p>
  <h1>World Map</h1>
  <p style="color:#6b6b6b;font-size:0.9rem;margin-top:6px;">
    Total daily Spotify streams by country. Hover any market for its #1 song.
  </p>
</div>
""", unsafe_allow_html=True)

# ── Enrich with #1 song per country ───────────────────────────────────────────
top1 = (
    df[df["pos"] == 1]
    .groupby(COL_MARKET)
    .first()
    .reset_index()
    [[COL_MARKET, COL_TITLE, COL_ARTIST]]
    .rename(columns={COL_TITLE: "top_title", COL_ARTIST: "top_artist"})
)
agg = agg.merge(top1, on=COL_MARKET, how="left")
agg["hover_text"] = (
    "<b>" + agg[COL_MARKET_NAME] + "</b><br>"
    + agg["total_streams"].apply(lambda x: f"Streams: {x:,.0f}") + "<br>"
    + "#1: " + agg["top_title"].fillna("—")
    + " · " + agg["top_artist"].fillna("—")
)

# ── ISO-2 → ISO-3 conversion (Plotly requires ISO-3) ─────────────────────────
ISO2_TO_ISO3 = {
    "ae":"ARE","ar":"ARG","at":"AUT","au":"AUS","be":"BEL","bg":"BGR",
    "bo":"BOL","br":"BRA","by":"BLR","ca":"CAN","ch":"CHE","cl":"CHL",
    "co":"COL","cr":"CRI","cy":"CYP","cz":"CZE","de":"DEU","dk":"DNK",
    "do":"DOM","ec":"ECU","ee":"EST","eg":"EGY","es":"ESP","fi":"FIN",
    "fr":"FRA","gb":"GBR","gr":"GRC","gt":"GTM","hk":"HKG","hn":"HND",
    "hu":"HUN","id":"IDN","ie":"IRL","il":"ISR","in":"IND","is":"ISL",
    "it":"ITA","jp":"JPN","kr":"KOR","kz":"KAZ","lt":"LTU","lu":"LUX",
    "lv":"LVA","mx":"MEX","my":"MYS","ng":"NGA","ni":"NIC","nl":"NLD",
    "no":"NOR","nz":"NZL","pa":"PAN","pe":"PER","ph":"PHL","pk":"PAK",
    "pl":"POL","pt":"PRT","py":"PRY","ro":"ROU","sa":"SAU","se":"SWE",
    "sg":"SGP","sk":"SVK","sv":"SLV","th":"THA","tr":"TUR","tw":"TWN",
    "ua":"UKR","us":"USA","uy":"URY","vn":"VNM","za":"ZAF",
}
agg["iso3"] = agg[COL_MARKET].map(ISO2_TO_ISO3)
agg = agg.dropna(subset=["iso3"])

# ── Choropleth ─────────────────────────────────────────────────────────────────
fig = go.Figure(go.Choropleth(
    locations=agg["iso3"],
    locationmode="ISO-3",
    z=agg["total_streams"],
    text=agg["hover_text"],
    hovertemplate="%{text}<extra></extra>",
    colorscale=[
        [0.0,  "#0a1f10"],
        [0.15, "#0d3a1c"],
        [0.4,  "#117a3a"],
        [0.7,  "#1DB954"],
        [1.0,  "#1ed760"],
    ],
    marker_line_color="#0d0d0d",
    marker_line_width=0.6,
    colorbar=dict(
        title=dict(text="Daily Streams", font=dict(color="#6b6b6b", size=11)),
        tickfont=dict(color="#6b6b6b", size=10),
        bgcolor="#141414",
        bordercolor="#1f1f1f",
        borderwidth=1,
        tickformat=".2s",
        len=0.7,
        thickness=12,
    ),
    zmin=agg["total_streams"].quantile(0.05),   # compress outliers
    zmax=agg["total_streams"].quantile(0.98),
))

fig.update_layout(
    paper_bgcolor="#0d0d0d",
    geo=dict(
        bgcolor="#0d0d0d",
        showframe=False,
        showcoastlines=True,
        coastlinecolor="#1a1a1a",
        showland=True,
        landcolor="#141414",
        showocean=True,
        oceancolor="#0a0a0a",
        showlakes=False,
        showcountries=True,
        countrycolor="#1a1a1a",
        countrywidth=0.4,
        projection_type=projection,
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    height=540,
    font=dict(color="#FFFFFF", family="Inter, Helvetica, Arial"),
)

st.plotly_chart(fig, use_container_width=True)

# ── KPI strip ─────────────────────────────────────────────────────────────────
total = agg["total_streams"].sum()
top_country = agg.iloc[0]

st.markdown("---")
c1, c2, c3 = st.columns(3)
c1.metric("Total Streams Across All Markets", f"{total/1_000_000_000:.2f}B")
c2.metric("Highest-Streaming Country", top_country[COL_MARKET_NAME],
          delta=f"{top_country['total_streams']/1_000_000:.1f}M streams")
c3.metric("Markets Tracked", f"{len(agg)}")

# ── Country table ──────────────────────────────────────────────────────────────
if show_table:
    st.markdown("---")
    st.subheader("Country Rankings")

    display = agg[[COL_MARKET_NAME, "total_streams", "top_title", "top_artist"]].copy()
    display.insert(0, "Rank", range(1, len(display) + 1))
    display.columns = ["Rank", "Country", "Daily Streams", "#1 Song", "#1 Artist"]
    display["Daily Streams"] = display["Daily Streams"].apply(lambda x: f"{int(x):,}")

    st.dataframe(display, use_container_width=True, hide_index=True)