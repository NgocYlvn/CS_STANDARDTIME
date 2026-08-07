import os
import html
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="CS Workload & Capacity Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CONSTANTS
# ============================================================
NAVY = "#083B82"
BLUE = "#0B63CE"
ORANGE = "#ED6B21"
GREEN = "#169B62"
AMBER = "#F59E0B"
RED = "#DC2626"
LIGHT_BG = "#F7F9FC"
TEXT = "#17324D"
MUTED = "#6B7C93"
BORDER = "#D9E2EC"

MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
SEGMENT_ORDER = ["AE", "AI", "OE", "OI", "CC", "TR", "WH"]
MODE_COLS = ["AI", "AE", "OILCL", "OIFCL", "OELCL", "OEFCL", "DI", "DE", "DM", "CE", "CI", "HE", "HI", "RE", "RI", "RD"]

# ============================================================
# CSS
# ============================================================
st.markdown(
    f"""
    <style>
        :root {{
            --navy: {NAVY};
            --blue: {BLUE};
            --orange: {ORANGE};
            --green: {GREEN};
            --amber: {AMBER};
            --red: {RED};
            --text: #172033;
            --muted: #667085;
            --line: #DCE5F0;
            --panel: #FFFFFF;
            --page: #FFFFFF;
        }}

        html, body, [class*="css"] {{font-family: Arial, "Segoe UI", sans-serif;}}
        .stApp {{background:#FFFFFF; color:var(--text);}}
        [data-testid="stHeader"] {{height:2.45rem; background:#FFFFFF;}}
        [data-testid="stToolbar"] {{top:.20rem;}}
        .block-container {{max-width:1700px; padding-top:.45rem; padding-bottom:1.2rem; padding-left:2rem; padding-right:2rem;}}

        /* SIDEBAR */
        [data-testid="stSidebar"] {{
            background:linear-gradient(180deg,#073472 0%,#0B4D9B 100%);
            border-right:none;
        }}
        [data-testid="stSidebar"] > div:first-child {{padding-top:.6rem;}}
        [data-testid="stSidebar"] * {{color:#FFFFFF;}}
        [data-testid="stSidebar"] div[role="radiogroup"] {{gap:.35rem;}}
        [data-testid="stSidebar"] label[data-baseweb="radio"] {{
            padding:.68rem .7rem; border-radius:0; margin:0; width:100%;
        }}
        [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {{
            background:rgba(11,99,206,.55); border-left:4px solid #ED6B21;
        }}
        [data-testid="stSidebar"] .stRadio label {{font-weight:700; font-size:.92rem;}}
        .side-brand {{padding:.35rem .2rem .5rem .2rem;}}
        .side-brand-title {{font-size:1.05rem;font-weight:800;line-height:1.2;color:white;}}
        .side-brand-sub {{font-size:.76rem;color:#D8E5F8;margin-top:.25rem;}}
        .side-footer {{position:relative;margin-top:12rem;color:#D8E5F8;font-size:.72rem;line-height:1.65;}}

        /* COMPACT HEADER */
        .dashboard-title {{
            font-size:1.62rem; line-height:1.05; font-weight:850; color:{NAVY} !important;
            margin:0 0 .18rem 0; letter-spacing:-.02em;
        }}
        .dashboard-subtitle {{
            color:#667085 !important; font-size:.78rem; line-height:1.15; margin:0 0 .22rem 0;
        }}
        .dashboard-filter {{
            color:#667085; font-size:.74rem; line-height:1.15; margin:0 0 .48rem 0;
        }}
        .orange-rule {{height:3px;background:#ED6B21;margin:0 -2rem .65rem -2rem;}}

        /* FILTER BAR */
        .filter-label {{font-size:.74rem;color:#667085;font-weight:600;margin-bottom:.1rem;}}
        div[data-baseweb="select"] > div {{min-height:38px !important; border-color:#D7E0EA !important;}}
        .stButton > button {{
            border:1px solid #ED6B21; color:#ED6B21; background:#FFFFFF;
            border-radius:8px; font-weight:700; min-height:38px;
        }}
        .stButton > button:hover {{border-color:#ED6B21;color:#ED6B21;background:#FFF7F0;}}
        .filter-divider {{height:1px;background:#E7ECF2;margin:.45rem -2rem 1rem -2rem;}}

        /* KPI */
        .kpi-card {{
            background:#FFFFFF; border:1px solid #E1E7EF; border-radius:12px;
            height:140px; min-height:140px; max-height:140px; display:flex;
            flex-direction:column; justify-content:space-between; align-items:center;
            box-sizing:border-box; overflow:hidden; box-shadow:0 2px 10px rgba(28,54,89,.08);
            padding:1.05rem .75rem .9rem .75rem;
        }}
        .kpi-label {{
            color:var(--navy); font-size:.79rem; font-weight:800; text-align:center;
            line-height:1.22; min-height:2.1rem; display:flex; align-items:center; justify-content:center;
        }}
        .kpi-value {{
            font-size:2.0rem; font-weight:850; line-height:1; color:var(--navy);
            text-align:center; margin:.15rem 0;
        }}
        .kpi-note {{
            color:#667085; font-size:.69rem; line-height:1.2; text-align:center; min-height:1rem;
        }}
        .accent-orange .kpi-value {{color:var(--orange);}}
        .accent-green .kpi-value {{color:var(--green);}}
        .accent-amber .kpi-value {{color:var(--amber);}}
        .accent-red .kpi-value {{color:var(--red);}}

        /* PANELS */
        .section-title {{
            background:transparent; color:var(--navy); padding:0; border-radius:0;
            font-size:.82rem; font-weight:850; margin:.1rem 0 .3rem 0; letter-spacing:.01em;
        }}
        [data-testid="stVerticalBlockBorderWrapper"] {{border-color:#E1E7EF !important;border-radius:12px !important;box-shadow:0 2px 10px rgba(28,54,89,.06);}}
        div[data-testid="stDataFrame"] {{border:1px solid var(--line); border-radius:10px; overflow:hidden;}}
        h1,h2,h3 {{color:var(--navy);}}
        .small-note {{font-size:.68rem;color:#667085;margin-top:.2rem;}}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# HELPERS & DATA LOADING (OPTIMIZED WITH CACHE)
# ============================================================
def fmt_num(v, decimals=0):
    if pd.isna(v):
        return "-"
    if decimals == 0:
        return f"{v:,.0f}"
    return f"{v:,.{decimals}f}"


def kpi_card(label, value, note="", accent=""):
    note_html = (
        f'<div class="kpi-note">{html.escape(str(note))}</div>'
        if note else ""
    )
    st.markdown(
        f"""
        <div class="kpi-card {accent}">
            <div class="kpi-label">{html.escape(str(label))}</div>
            <div class="kpi-value">{html.escape(str(value))}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def clean_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def month_sort_key(series):
    return series.map({m: i for i, m in enumerate(MONTH_ORDER)})


@st.cache_data(ttl=600)  # Tối ưu hiệu năng: Cache dữ liệu trong 10 phút
def load_hc(xls_path):
    raw = pd.read_excel(xls_path, sheet_name="HC", header=None)
    df = raw.iloc[3:, :13].copy()
    df.columns = [
        "Office", "Month", "Approved_MNG", "Approved_PIC", "Approved_Total",
        "Actual_MNG", "Actual_PIC", "Actual_Total",
        "Required_MNG", "Required_PIC", "Required_Total",
        "Capacity", "Status"
    ]
    df = df[df["Office"].notna() & df["Month"].notna()].copy()
    df["Office"] = df["Office"].astype(str).str.strip()
    df["Month"] = df["Month"].astype(str).str.strip()
    
    numeric_cols = [c for c in df.columns if c not in ["Office", "Month", "Status"]]
    df = clean_numeric(df, numeric_cols)
    df["Status"] = df["Status"].fillna("").astype(str).str.strip()
    return df


@st.cache_data(ttl=600)  # Tối ưu hiệu năng: Cache dữ liệu volume
def load_shipment(xls_path):
    raw = pd.read_excel(xls_path, sheet_name="Shipment volume", header=None)
    df = raw.iloc[3:, :20].copy()
    df.columns = ["Office", "Month", "Active_Customer"] + MODE_COLS + ["TOTAL"]
    df = df[df["Office"].notna() & df["Month"].notna()].copy()
    df["Office"] = df["Office"].astype(str).str.strip()
    df["Month"] = df["Month"].astype(str).str.strip()
    
    numeric_cols = ["Active_Customer"] + MODE_COLS + ["TOTAL"]
    df = clean_numeric(df, numeric_cols)
    return df

# ============================================================
# SIDEBAR NAVIGATION & FILE INPUT
# ============================================================
with st.sidebar:
    st.markdown(
        f"""
        <div class="side-brand">
            <div class="side-brand-title">📊 CS WORKLOAD &<br>CAPACITY</div>
            <div class="side-brand-sub">Executive Insights Dashboard</div>
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.markdown("---")
    
    # Nơi nạp dữ liệu đầu vào
    data_file = st.file_uploader("Nạp dữ liệu báo cáo (Excel):", type=["xlsx"])
    
    st.markdown("---")
    # Menu điều hướng phong cách tối giản
    view_option = st.radio(
        "XEM BÁO CÁO THEO:",
        options=["Tổng Quan Toàn Quốc", "Chi Tiết Theo Văn Phòng"]
    )
    
    st.markdown(
        """
        <div class="side-footer">
            Developed for Management Board<br>
            © 2026 Operations Analytics
        </div>
        """, 
        unsafe_allow_html=True
    )

# ============================================================
# MAIN CONTENT EXECUTIVE DASHBOARD
# ============================================================
# Tiêu đề báo cáo
st.markdown('<div class="dashboard-title">CS WORKLOAD & CAPACITY PERFORMANCE</div>', unsafe_allow_html=True)
