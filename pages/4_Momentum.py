"""
pages/4_Momentum.py — Songs ranked by 7-day stream growth (rising vs falling).
"""

import streamlit as st
import plotly.graph_objects as go

from utils.data import (
    load_data, get_all_markets, momentum_songs,
    COL_TITLE, COL_ARTIST, COL_STREAMS, COL_STREAMS_7DAY,
    COL_STREAMS_7D_DT, COL_POS, COL_DAYS, COL_PEAK,
)

st.set_page_config(page_title="Momentum · Spotify Charts", page_icon="🚀", layout="wide")

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
  [data-testid="stTabs"] [role="tab"] { color: #6b6b6b; font-weight: 600; font-size: 0.85rem; padding: 8px 16px; }
  [data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: #1DB954; border-bottom: 2px solid #1DB954; }
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
    top_n = st.slider("Songs to show", 10, 50, 20, 5)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:24px;">
  <p style="color:#1DB954;font-size:0.72rem;font-weight:700;letter-spacing:0.12em;
            text-transform:uppercase;margin-bottom:6px;">
    {selected_name} · {chart_date.strftime("%B %d, %Y")}
  </p>
  <h1>Momentum</h1>
  <p style="color:#6b6b6b;font-size:0.9rem;margin-top:6px;">
    Ranked by 7-day stream growth. New entries excluded — these are songs
    already on the chart that are accelerating or decelerating.
  </p>
</div>
""", unsafe_allow_html=True)

# ── Compute ───────────────────────────────────────────────────────────────────
rising  = momentum_songs(df, market=selected_market, n=top_n)
falling = (
    df[
        (df["market"] == selected_market) &
        (df["pos_change"] != "NEW")
    ]
    .sort_values(COL_STREAMS_7D_DT, ascending=True)
    .head(top_n)
    .reset_index(drop=True)
)

tab_rise, tab_fall, tab_scatter = st.tabs(["📈 Rising", "📉 Falling", "🔵 Scatter"])

# ── Helper: horizontal bar chart ─────────────────────────────────────────────
def momentum_bar(data, color_positive: bool = True) -> go.Figure:
    data = data.copy()
    data["_label"] = data[COL_TITLE].str[:30]
    data["_hover"] = (
        data[COL_ARTIST] + " — " + data[COL_TITLE] + "<br>"
        + "7-Day Δ: " + data[COL_STREAMS_7D_DT].apply(lambda x: f"{x/1_000_000:+.2f}M") + "<br>"
        + "7-Day Total: " + data[COL_STREAMS_7DAY].apply(lambda x: f"{x/1_000_000:.2f}M") + "<br>"
        + "Chart pos: #" + data[COL_POS].astype(str)
    )

    vals  = data[COL_STREAMS_7D_DT]
    abs_max = vals.abs().max() or 1
    colors = []
    for v in vals:
        intensity = abs(v) / abs_max
        if color_positive:
            g = int(100 + intensity * 100)
            colors.append(f"rgb(0,{g},60)")
        else:
            r = int(100 + intensity * 100)
            colors.append(f"rgb({r},30,30)")

    fig = go.Figure(go.Bar(
        x=vals,
        y=data["_label"],
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=vals.apply(lambda x: f"{x/1_000_000:+.2f}M"),
        textposition="outside",
        textfont=dict(color="#6b6b6b", size=10),
        hovertext=data["_hover"],
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
            title=dict(text="7-Day Stream Delta", font=dict(color="#6b6b6b", size=11)),
            zeroline=True,
            zerolinecolor="#2a2a2a",
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(color="#FFFFFF", size=12),
        ),
        height=max(380, top_n * 44),
        margin=dict(l=10, r=90, t=10, b=20),
        bargap=0.3,
    )
    return fig

# ── Rising tab ────────────────────────────────────────────────────────────────
with tab_rise:
    if rising.empty:
        st.info("No momentum data for this market.")
    else:
        st.plotly_chart(momentum_bar(rising, color_positive=True),
                        use_container_width=True)
        with st.expander("View as table"):
            tbl = rising[[COL_POS, COL_TITLE, COL_ARTIST,
                          COL_STREAMS_7D_DT, COL_STREAMS_7DAY, COL_DAYS]].copy()
            tbl.columns = ["#", "Title", "Artist", "7-Day Δ", "7-Day Total", "Days"]
            tbl["7-Day Δ"]     = tbl["7-Day Δ"].apply(lambda x: f"{int(x):+,}")
            tbl["7-Day Total"] = tbl["7-Day Total"].apply(lambda x: f"{int(x):,}")
            st.dataframe(tbl, use_container_width=True, hide_index=True)

# ── Falling tab ────────────────────────────────────────────────────────────────
with tab_fall:
    if falling.empty:
        st.info("No data for this market.")
    else:
        st.plotly_chart(momentum_bar(falling, color_positive=False),
                        use_container_width=True)
        with st.expander("View as table"):
            tbl = falling[[COL_POS, COL_TITLE, COL_ARTIST,
                           COL_STREAMS_7D_DT, COL_STREAMS_7DAY, COL_DAYS]].copy()
            tbl.columns = ["#", "Title", "Artist", "7-Day Δ", "7-Day Total", "Days"]
            tbl["7-Day Δ"]     = tbl["7-Day Δ"].apply(lambda x: f"{int(x):+,}")
            tbl["7-Day Total"] = tbl["7-Day Total"].apply(lambda x: f"{int(x):,}")
            st.dataframe(tbl, use_container_width=True, hide_index=True)

# ── Scatter tab ────────────────────────────────────────────────────────────────
with tab_scatter:
    st.markdown(
        "<p style='color:#6b6b6b;font-size:0.85rem;margin-bottom:12px;'>"
        "Daily streams vs 7-day growth delta. Upper-right = high volume + accelerating."
        "</p>",
        unsafe_allow_html=True,
    )

    scatter_df = df[
        (df["market"] == selected_market) &
        (df["pos_change"] != "NEW")
    ].copy()

    if scatter_df.empty:
        st.info("No data.")
    else:
        scatter_df["_label"] = scatter_df[COL_ARTIST] + " — " + scatter_df[COL_TITLE]
        scatter_df["_color"] = scatter_df[COL_STREAMS_7D_DT].apply(
            lambda x: "#1DB954" if x >= 0 else "#e84c4c"
        )

        fig_s = go.Figure(go.Scatter(
            x=scatter_df[COL_STREAMS],
            y=scatter_df[COL_STREAMS_7D_DT],
            mode="markers",
            marker=dict(
                color=scatter_df["_color"],
                size=8,
                opacity=0.75,
                line=dict(width=0),
            ),
            text=scatter_df["_label"],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Daily streams: %{x:,.0f}<br>"
                "7-day Δ: %{y:,.0f}"
                "<extra></extra>"
            ),
        ))

        fig_s.add_hline(
            y=0, line_color="#2a2a2a", line_width=1,
            annotation_text="Flat", annotation_font_color="#3d3d3d",
            annotation_position="bottom right",
        )

        fig_s.update_layout(
            paper_bgcolor="#0d0d0d",
            plot_bgcolor="#0d0d0d",
            font=dict(color="#FFFFFF", family="Inter, Helvetica, Arial"),
            xaxis=dict(
                title=dict(text="Daily Streams", font=dict(color="#6b6b6b", size=11)),
                tickformat=".2s",
                gridcolor="#161616",
                tickfont=dict(color="#3d3d3d"),
            ),
            yaxis=dict(
                title=dict(text="7-Day Stream Delta", font=dict(color="#6b6b6b", size=11)),
                tickformat=".2s",
                gridcolor="#161616",
                tickfont=dict(color="#3d3d3d"),
                zeroline=False,
            ),
            height=480,
            margin=dict(l=20, r=20, t=20, b=20),
        )

        st.plotly_chart(fig_s, use_container_width=True)
        st.markdown("""
        <div style="display:flex;gap:20px;margin-top:-8px;">
          <span style="color:#1DB954;font-size:0.75rem;">● Growing</span>
          <span style="color:#e84c4c;font-size:0.75rem;">● Declining</span>
        </div>
        """, unsafe_allow_html=True)