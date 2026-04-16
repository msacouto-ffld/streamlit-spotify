"""
app.py — Spotify Global Charts Dashboard
Run: streamlit run app.py
"""

import streamlit as st
from utils.supabase_loader import download_if_needed

# Download fresh data from Supabase if running in cloud
download_if_needed()

st.set_page_config(
    page_title="Spotify Global Charts",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Base */
  .stApp { background-color: #0d0d0d; color: #FFFFFF; }
  [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #1a1a1a; }
  [data-testid="stSidebar"] * { color: #FFFFFF !important; }

  /* Hide default Streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }

  /* Sidebar nav */
  [data-testid="stSidebarNav"] a {
    color: #6b6b6b !important;
    font-size: 0.85rem;
    padding: 6px 12px;
    border-radius: 6px;
    transition: all 0.15s;
  }
  [data-testid="stSidebarNav"] a:hover {
    color: #FFFFFF !important;
    background: #1a1a1a;
  }
  [data-testid="stSidebarNav"] a[aria-current="page"] {
    color: #1DB954 !important;
    background: #0d2b18;
    font-weight: 600;
  }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: #141414;
    border: 1px solid #1f1f1f;
    border-radius: 10px;
    padding: 18px 20px;
  }
  [data-testid="metric-container"] label {
    color: #6b6b6b !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
  }
  [data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-size: 1.65rem !important;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  [data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
  }

  /* Inputs */
  [data-baseweb="select"] > div {
    background: #141414 !important;
    border-color: #2a2a2a !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
  }
  [data-testid="stTextInput"] input {
    background: #141414 !important;
    color: #FFFFFF !important;
    border-color: #2a2a2a !important;
    border-radius: 8px !important;
  }

  /* Buttons */
  .stButton > button {
    background: #1DB954;
    color: #000000;
    border: none;
    border-radius: 500px;
    font-weight: 700;
    font-size: 0.85rem;
    padding: 8px 20px;
    transition: background 0.15s;
  }
  .stButton > button:hover { background: #1ed760; }

  /* Download button */
  [data-testid="stDownloadButton"] > button {
    background: transparent;
    color: #1DB954 !important;
    border: 1px solid #1DB954 !important;
    border-radius: 500px;
    font-weight: 600;
    font-size: 0.82rem;
  }
  [data-testid="stDownloadButton"] > button:hover {
    background: #0d2b18 !important;
  }

  /* Tabs */
  [data-testid="stTabs"] [role="tab"] {
    color: #6b6b6b;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 8px 16px;
  }
  [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #1DB954;
    border-bottom: 2px solid #1DB954;
  }

  /* Dataframe */
  [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
  [data-testid="stDataFrame"] th {
    background: #141414 !important;
    color: #6b6b6b !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  /* Headings */
  h1 { font-size: 1.8rem !important; font-weight: 800 !important; letter-spacing: -0.03em; }
  h2 { font-size: 1.2rem !important; font-weight: 700 !important; color: #FFFFFF; }
  h3 { font-size: 1rem !important; font-weight: 600 !important; color: #b3b3b3; }

  /* Dividers */
  hr { border-color: #1a1a1a; margin: 1.5rem 0; }

  /* Expander */
  [data-testid="stExpander"] {
    background: #141414;
    border: 1px solid #1f1f1f;
    border-radius: 10px;
  }
</style>
""", unsafe_allow_html=True)

# ── Sidebar brand ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 4px 20px 4px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
        <svg width="28" height="28" viewBox="0 0 168 168">
          <circle cx="84" cy="84" r="84" fill="#1DB954"/>
          <path d="M120.6 110.4c-1.6 2.6-5 3.4-7.6 1.8-20.8-12.7-47-15.6-77.8-8.5
                   -2.9.7-5.9-1.1-6.6-4-.7-2.9 1.1-5.9 4-6.6 33.7-7.7 62.6-4.4
                   85.9 9.7 2.6 1.6 3.4 5 1.8 7.6z
                   M131.5 87.4c-2 3.3-6.3 4.3-9.6 2.3-23.8-14.6-60.1-18.9-88.3-10.3
                   -3.7 1.1-7.5-1-8.6-4.7-1.1-3.7 1-7.5 4.7-8.6 32.2-9.8 72.3-5
                   99.4 11.7 3.3 2 4.3 6.3 2.3 9.6z
                   M133.2 63.6c-28.5-16.9-75.5-18.5-102.7-10.2-4.4 1.3-9-1.2-10.3-5.6
                   -1.3-4.4 1.2-9 5.6-10.3 31.2-9.5 83.1-7.6 115.8 11.8 4 2.4 5.3
                   7.6 2.9 11.6-2.3 4-7.5 5.2-11.4 2.8z" fill="white"/>
        </svg>
        <span style="font-size:1rem;font-weight:800;letter-spacing:-0.02em;color:#FFFFFF;">
          Global Charts
        </span>
      </div>
      <p style="color:#3d3d3d;font-size:0.72rem;margin:0;letter-spacing:0.05em;text-transform:uppercase;">
        Powered by Kworb · Spotify Data
      </p>
    </div>
    """, unsafe_allow_html=True)

# ── Landing ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding: 40px 0 20px 0;">
  <p style="color:#1DB954;font-size:0.8rem;font-weight:700;letter-spacing:0.12em;
            text-transform:uppercase;margin-bottom:12px;">
    Spotify Streaming Intelligence
  </p>
  <h1 style="font-size:2.6rem;font-weight:900;letter-spacing:-0.04em;
             line-height:1.1;margin-bottom:16px;">
    Global Charts<br/>Dashboard
  </h1>
  <p style="color:#6b6b6b;font-size:1rem;max-width:520px;line-height:1.6;">
    Real Spotify streaming data across 72 markets, sourced fresh from
    Kworb. Explore what the world is listening to right now.
  </p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div style="padding:20px;background:#141414;border-radius:10px;
                border:1px solid #1f1f1f;height:130px;">
      <div style="font-size:1.4rem;margin-bottom:8px;">📊</div>
      <div style="font-weight:700;font-size:0.95rem;margin-bottom:4px;">Overview</div>
      <div style="color:#6b6b6b;font-size:0.8rem;line-height:1.4;">
        Global top 10 with live stream counts and daily movement
      </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="padding:20px;background:#141414;border-radius:10px;
                border:1px solid #1f1f1f;height:130px;">
      <div style="font-size:1.4rem;margin-bottom:8px;">🌍</div>
      <div style="font-weight:700;font-size:0.95rem;margin-bottom:4px;">World Map</div>
      <div style="color:#6b6b6b;font-size:0.8rem;line-height:1.4;">
        72-country choropleth of daily streams across every market
      </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="padding:20px;background:#141414;border-radius:10px;
                border:1px solid #1f1f1f;height:130px;">
      <div style="font-size:1.4rem;margin-bottom:8px;">🎶</div>
      <div style="font-weight:700;font-size:0.95rem;margin-bottom:4px;">Top Songs</div>
      <div style="color:#6b6b6b;font-size:0.8rem;line-height:1.4;">
        Full chart tables with search, filters, and CSV export
      </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div style="padding:20px;background:#141414;border-radius:10px;
                border:1px solid #1f1f1f;height:130px;">
      <div style="font-size:1.4rem;margin-bottom:8px;">🚀</div>
      <div style="font-weight:700;font-size:0.95rem;margin-bottom:4px;">Momentum</div>
      <div style="color:#6b6b6b;font-size:0.8rem;line-height:1.4;">
        What's surging right now — ranked by 7-day stream growth
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div style="margin-top:32px;padding:16px 20px;background:#0d2b18;
            border-radius:8px;border-left:3px solid #1DB954;">
  <span style="color:#6b6b6b;font-size:0.8rem;">👈 </span>
  <span style="color:#b3b3b3;font-size:0.8rem;">
    Select a page from the sidebar to get started
  </span>
</div>
""", unsafe_allow_html=True)