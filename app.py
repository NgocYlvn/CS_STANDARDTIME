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
            height:190px; min-height:190px; max-height:190px; display:flex;
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
# HELPERS
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
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def month_sort_key(series):
    return series.map({m: i for i, m in enumerate(MONTH_ORDER)})


def load_hc(xls):
    raw = pd.read_excel(xls, sheet_name="HC", header=None)
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
    df = clean_numeric(df, [c for c in df.columns if c not in ["Office", "Month", "Status"]])
    df["Status"] = df["Status"].fillna("").astype(str).str.strip()
    return df


def load_shipment(xls):
    raw = pd.read_excel(xls, sheet_name="Shipment volume", header=None)
    df = raw.iloc[3:, :20].copy()
    df.columns = ["Office", "Month", "Active_Customer"] + MODE_COLS + ["TOTAL"]
    df = df[df["Office"].notna() & df["Month"].notna()].copy()
    df["Office"] = df["Office"].astype(str).str.strip()
    df["Month"] = df["Month"].astype(str).str.strip()
    df = clean_numeric(df, ["Active_Customer"] + MODE_COLS + ["TOTAL"])
    return df


def load_bu(xls):
    raw = pd.read_excel(xls, sheet_name="BU allocation", header=None)
    df = raw.iloc[3:, :13].copy()
    df.columns = [
        "Office", "Month", "Segment",
        "Core_Volume", "Core_Time",
        "Ancillary_Volume", "Ancillary_Time",
        "Supporting_Volume", "Supporting_Time",
        "Exception_Volume", "Exception_Time",
        "Total_Workload", "Network_Share"
    ]
    df = df[df["Office"].notna() & df["Month"].notna() & df["Segment"].notna()].copy()
    for c in ["Office", "Month", "Segment"]:
        df[c] = df[c].astype(str).str.strip()
    df = clean_numeric(df, [c for c in df.columns if c not in ["Office", "Month", "Segment"]])
    return df


def load_customer_ns(xls):
    raw = pd.read_excel(xls, sheet_name="N-S Customer list", header=None)
    month_headers = raw.iloc[1, 3:15].tolist()
    cols = ["No", "Office", "Customer"] + [str(x) for x in month_headers] + ["Total"]
    df = raw.iloc[2:, :16].copy()
    df.columns = cols
    df = df[df["Customer"].notna()].copy()
    df["Office"] = df["Office"].ffill().astype(str).str.strip()
    df["Customer"] = df["Customer"].astype(str).str.strip()
    for c in cols[3:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def discover_default_excel():
    candidates = []
    for root in [Path.cwd(), Path("/mnt/data")]:
        if root.exists():
            candidates.extend(root.glob("*.xlsx"))
            candidates.extend(root.glob("*.xlsm"))
    candidates = [p for p in candidates if not p.name.startswith("~$")]
    if not candidates:
        return None
    # Prefer a workbook containing the expected sheets.
    for p in candidates:
        try:
            xl = pd.ExcelFile(p)
            required = {"HC", "Shipment volume", "BU allocation", "N-S Customer list"}
            if required.issubset(set(xl.sheet_names)):
                return str(p)
        except Exception:
            pass
    return str(candidates[0])


@st.cache_data(show_spinner=False)
def load_data(path_or_buffer):
    xls = pd.ExcelFile(path_or_buffer)
    required = {"HC", "Shipment volume", "BU allocation", "N-S Customer list"}
    missing = required - set(xls.sheet_names)
    if missing:
        raise ValueError(f"Missing required sheet(s): {', '.join(sorted(missing))}")
    return load_hc(xls), load_shipment(xls), load_bu(xls), load_customer_ns(xls)


def filtered(df, office, month):
    out = df.copy()
    if office != "All Offices" and "Office" in out.columns:
        out = out[out["Office"] == office]
    if month != "All Months" and "Month" in out.columns:
        out = out[out["Month"] == month]
    return out


def plot_config():
    return {"displayModeBar": False, "responsive": True}


def style_fig(fig, height=350, legend=True):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=45, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color=TEXT, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0) if legend else None,
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDER)
    fig.update_yaxes(gridcolor="#E9EFF5", zeroline=False)
    return fig


# ============================================================
# SIDEBAR / DATA SOURCE
# ============================================================
with st.sidebar:
    st.markdown(
        """
        <div class="side-brand">
            <div class="side-brand-title">📊 CS WORKLOAD</div>
            <div class="side-brand-sub">CAPACITY DASHBOARD</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='border:none;border-top:3px solid #ED6B21;margin:.35rem -1rem .6rem -1rem;'>", unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        ["Overview", "HC Capacity", "Shipment Volume", "Workload Allocation", "Customer Volume"],
        label_visibility="collapsed",
    )
    with st.expander("Data Source", expanded=False):
        uploaded = st.file_uploader("Upload updated Excel", type=["xlsx", "xlsm"], label_visibility="collapsed")
    st.markdown(
        """
        <div class="side-footer">
            CS WORKLOAD<br>
            DASHBOARD<br><br>
            © 2026 CS HAD<br>
            Internal Use Only<br>
            v1.0
        </div>
        """,
        unsafe_allow_html=True,
    )

try:
    source = uploaded if uploaded is not None else discover_default_excel()
    if source is None:
        st.error("No Excel workbook found. Please upload the workload workbook from the sidebar.")
        st.stop()
    hc, ship, bu, cust = load_data(source)

    # ------------------------------------------------------------
    # REMOVE SHIPMENT MONTHS WITH NO ACTUAL DATA
    # Blank / None / NaN / all-zero shipment rows are excluded.
    # Applied here so empty months disappear from filters, charts,
    # KPIs, and Shipment Detail.
    # ------------------------------------------------------------
    shipment_value_cols = [
        "Active_Customer", "AI", "AE", "OILCL", "OIFCL",
        "OELCL", "OEFCL", "DI", "DE", "DM", "CE", "CI",
        "HE", "HI", "RE", "RI", "RD"
    ]

    shipment_value_cols = [
        col for col in shipment_value_cols
        if col in ship.columns
    ]

    if shipment_value_cols:
        for col in shipment_value_cols:
            ship[col] = pd.to_numeric(ship[col], errors="coerce")

        ship = ship[
            ship[shipment_value_cols]
            .fillna(0)
            .sum(axis=1)
            .ne(0)
        ].copy()

        existing_mode_cols = [col for col in MODE_COLS if col in ship.columns]
        if existing_mode_cols:
            ship["TOTAL"] = (
                ship[existing_mode_cols]
                .fillna(0)
                .sum(axis=1)
            )

except Exception as e:
    st.error(f"Cannot read workbook: {e}")
    st.stop()

if uploaded is not None:
    data_date = "Uploaded file"
else:
    try:
        data_date = pd.Timestamp(Path(source).stat().st_mtime, unit="s").strftime("%d %b %Y")
    except Exception:
        data_date = "Not available"

all_offices = sorted(set(hc["Office"].dropna()) | set(ship["Office"].dropna()) | set(bu["Office"].dropna()))

# ============================================================
# HEADER + FILTER BAR
# ============================================================
st.markdown('<div class="dashboard-title">CS WORKLOAD & CAPACITY DASHBOARD</div>', unsafe_allow_html=True)
st.markdown(f'<div class="dashboard-subtitle">🗓️ Last Updated: {data_date}</div>', unsafe_allow_html=True)

# Session-state driven filters allow a Reset button in the main header.
if "office_filter" not in st.session_state:
    st.session_state.office_filter = "All Offices"
if "month_filter" not in st.session_state:
    st.session_state.month_filter = "All Months"

# IMPORTANT: reset widget values via callback.
# Streamlit executes callbacks before widgets are recreated on the next rerun,
# avoiding StreamlitAPIException from modifying a widget key after instantiation.
def reset_filters():
    st.session_state["office_filter"] = "All Offices"
    st.session_state["month_filter"] = "All Months"

meta_office = st.session_state.office_filter
meta_month = st.session_state.month_filter
st.markdown(
    f'<div class="dashboard-filter">FY2026 &nbsp; • &nbsp; Office: {meta_office} &nbsp; • &nbsp; Month: {meta_month}</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="orange-rule"></div>', unsafe_allow_html=True)

fc1, fc2, spacer, fc3 = st.columns([1.05, 1.05, 1.05, .48], gap="medium")
with fc1:
    office = st.selectbox("Office", ["All Offices"] + all_offices, key="office_filter")

available_months = []
for m in MONTH_ORDER:
    office_mask_hc = (hc["Office"] == office) if office != "All Offices" else pd.Series(True, index=hc.index)
    office_mask_ship = (ship["Office"] == office) if office != "All Offices" else pd.Series(True, index=ship.index)
    office_mask_bu = (bu["Office"] == office) if office != "All Offices" else pd.Series(True, index=bu.index)
    exists = (
        ((hc["Month"] == m) & office_mask_hc).any()
        or ((ship["Month"] == m) & office_mask_ship).any()
        or ((bu["Month"] == m) & office_mask_bu).any()
    )
    if exists:
        available_months.append(m)

if st.session_state.month_filter not in ["All Months"] + available_months:
    st.session_state.month_filter = "All Months"

with fc2:
    month = st.selectbox("Month", ["All Months"] + available_months, key="month_filter")
with fc3:
    st.markdown("<div style='height:1.72rem'></div>", unsafe_allow_html=True)
    st.button(
        "↻  Reset Filters",
        use_container_width=True,
        on_click=reset_filters,
        key="reset_filters_button",
    )

st.markdown('<div class="filter-divider"></div>', unsafe_allow_html=True)

hc_f = filtered(hc, office, month)
ship_f = filtered(ship, office, month)
bu_f = filtered(bu, office, month)

# ============================================================
# OVERVIEW
# ============================================================
if page == "Overview":
    latest_hc = hc_f.dropna(subset=["Required_Total", "Actual_Total"]).copy()
    if month == "All Months" and not latest_hc.empty:
        latest_hc["_m"] = month_sort_key(latest_hc["Month"])
        latest_hc = latest_hc.sort_values(["Office", "_m"]).groupby("Office", as_index=False).tail(1)

    actual_hc = latest_hc["Actual_Total"].sum(min_count=1)
    required_hc = latest_hc["Required_Total"].sum(min_count=1)
    total_ship = ship_f["TOTAL"].sum(min_count=1)
    total_workload = bu_f["Total_Workload"].sum(min_count=1)

    # Capacity is expressed as required HC / actual HC in the source workbook.
    utilization = (required_hc / actual_hc) if pd.notna(actual_hc) and actual_hc else np.nan
    exception_shipments = bu_f["Exception_Volume"].sum(min_count=1)

    # Estimated monthly labor capacity in hours using 8h × 95% × 22 days.
    capacity_hours = actual_hc * 8 * 0.95 * 22 if pd.notna(actual_hc) else np.nan

    k1, k2, k3, k4, k5, k6 = st.columns(6, gap="small")
    with k1:
        kpi_card("TOTAL HC (FTE)", fmt_num(actual_hc, 1), "Actual headcount")
    with k2:
        kpi_card("TOTAL CAPACITY (HOURS)", fmt_num(capacity_hours), "8h × 95% × 22 days")
    with k3:
        kpi_card("TOTAL SHIPMENTS", fmt_num(total_ship), "Selected scope")
    with k4:
        kpi_card("TOTAL WORKLOAD (HOURS)", fmt_num(total_workload), "Recorded workload")
    with k5:
        kpi_card("CAPACITY UTILIZATION", f"{utilization:.1%}" if pd.notna(utilization) else "-", "Required HC / Actual HC", accent="accent-orange")
    with k6:
        kpi_card("EXCEPTION SHIPMENTS", fmt_num(exception_shipments), "Exception volume", accent="accent-green")

    st.markdown('<div class="small-note">pp = percentage points</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:.45rem'></div>", unsafe_allow_html=True)

    p1, p2, p3 = st.columns([1.12, 1, 1.1], gap="medium")

    with p1:
        with st.container(border=True):
            st.markdown('<div class="section-title">📈 &nbsp; WORKLOAD VS CAPACITY (HOURS)</div>', unsafe_allow_html=True)
            monthly_hc = hc_f.dropna(subset=["Actual_Total"]).copy()
            if not monthly_hc.empty:
                monthly_hc["Capacity_Hours"] = monthly_hc["Actual_Total"] * 8 * .95 * 22
                cap_trend = monthly_hc.groupby("Month", as_index=False)["Capacity_Hours"].sum()
                work_trend = bu_f.groupby("Month", as_index=False)["Total_Workload"].sum()
                trend = cap_trend.merge(work_trend, on="Month", how="outer")
                trend["_m"] = month_sort_key(trend["Month"])
                trend = trend.sort_values("_m")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=trend["Month"], y=trend["Capacity_Hours"], mode="lines+markers+text", name="Capacity (Hours)", text=[fmt_num(v) for v in trend["Capacity_Hours"]], textposition="top center", line=dict(color=NAVY, width=2.5), marker=dict(size=7)))
                fig.add_trace(go.Scatter(x=trend["Month"], y=trend["Total_Workload"], mode="lines+markers+text", name="Workload (Hours)", text=[fmt_num(v) for v in trend["Total_Workload"]], textposition="bottom center", line=dict(color=ORANGE, width=2.5), marker=dict(size=7)))
                fig = style_fig(fig, 330, legend=True)
                fig.update_layout(margin=dict(l=0,r=0,t=38,b=5))
                fig.update_yaxes(title="")
                fig.update_xaxes(title="")
                st.plotly_chart(fig, use_container_width=True, config=plot_config())
            else:
                st.info("No HC data available for the selected filters.")

    with p2:
        with st.container(border=True):
            st.markdown('<div class="section-title">📈 &nbsp; CAPACITY UTILIZATION (%)</div>', unsafe_allow_html=True)
            util_pct = float(utilization * 100) if pd.notna(utilization) else 0
            util_pct = max(0, min(util_pct, 100))
            fig = go.Figure(go.Pie(
                values=[util_pct, max(100-util_pct, 0)],
                labels=[f"Utilized ({util_pct:.1f}%)", f"Remaining ({100-util_pct:.1f}%)"],
                hole=.64,
                marker=dict(colors=[ORANGE, "#D8D8D8"]),
                textinfo="none",
                sort=False,
            ))
            fig.add_annotation(text=f"<b>{util_pct:.1f}%</b><br><span style='font-size:12px'>Utilization</span>", x=.5, y=.5, showarrow=False, font=dict(size=24, color=ORANGE))
            fig.update_layout(height=330, margin=dict(l=5,r=5,t=15,b=10), showlegend=True, legend=dict(orientation="h", y=-.03, x=.5, xanchor="center"), paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())

    with p3:
        with st.container(border=True):
            st.markdown('<div class="section-title">📊 &nbsp; TOP 5 OFFICES BY UTILIZATION</div>', unsafe_allow_html=True)
            office_hc = hc_f.groupby("Office", as_index=False).agg(Actual_HC=("Actual_Total","sum"), Required_HC=("Required_Total","sum"))
            office_hc["Utilization"] = np.where(office_hc["Actual_HC"]>0, office_hc["Required_HC"] / office_hc["Actual_HC"] * 100, np.nan)
            office_hc = office_hc.dropna(subset=["Utilization"]).nlargest(5, "Utilization").sort_values("Utilization")
            if not office_hc.empty:
                fig = px.bar(office_hc, x="Utilization", y="Office", orientation="h", text="Utilization")
                fig.update_traces(marker_color=ORANGE, texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
                fig = style_fig(fig, 330, legend=False)
                fig.update_layout(margin=dict(l=0,r=22,t=18,b=5))
                fig.update_xaxes(range=[0, max(100, float(office_hc["Utilization"].max())*1.12)], ticksuffix="%", title="Utilization (%)")
                fig.update_yaxes(title="")
                st.plotly_chart(fig, use_container_width=True, config=plot_config())
            else:
                st.info("No office utilization data available.")

# ============================================================
# HC CAPACITY
# ============================================================
elif page == "HC Capacity":
    data = hc_f.copy()
    valid = data.dropna(subset=["Actual_Total", "Required_Total"])
    actual = valid["Actual_Total"].sum(min_count=1)
    required = valid["Required_Total"].sum(min_count=1)
    gap = actual - required if pd.notna(actual) and pd.notna(required) else np.nan
    avg_cap = valid["Capacity"].mean() if not valid.empty else np.nan

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Approved HC", fmt_num(data["Approved_Total"].sum(min_count=1)), "Approved headcount")
    with c2: kpi_card("Actual HC", fmt_num(actual), "Actual headcount")
    with c3: kpi_card("Required HC", fmt_num(required, 1), "Workload-based requirement")
    with c4: kpi_card("Average Capacity", f"{avg_cap:.1%}" if pd.notna(avg_cap) else "-", f"HC gap: {fmt_num(gap, 1)}", accent="accent-orange" if pd.notna(avg_cap) and avg_cap > 1 else "accent-green")

    # ============================================================
    # HC CHARTS — GROUPED BY MONTH, THEN OFFICE
    # ============================================================
    month_order = [
        "Apr", "May", "Jun", "Jul", "Aug", "Sep",
        "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"
    ]

    hc_chart = data.copy()

    # Only keep rows with meaningful HC information.
    hc_chart["Actual_Total"] = pd.to_numeric(hc_chart["Actual_Total"], errors="coerce")
    hc_chart["Required_Total"] = pd.to_numeric(hc_chart["Required_Total"], errors="coerce")
    hc_chart = hc_chart[
        hc_chart[["Actual_Total", "Required_Total"]]
        .fillna(0)
        .sum(axis=1)
        .ne(0)
    ].copy()

    # FY month order: Apr -> Mar.
    hc_chart["Month"] = pd.Categorical(
        hc_chart["Month"],
        categories=month_order,
        ordered=True
    )
    hc_chart = hc_chart.sort_values(["Month", "Office"]).reset_index(drop=True)

    # Display label keeps each month together and offices in sequence.
    hc_chart["Period"] = (
        hc_chart["Month"].astype(str)
        + " · "
        + hc_chart["Office"].astype(str)
    )

    # Required / Actual HC ratio.
    hc_chart["Utilization"] = np.where(
        hc_chart["Actual_Total"] > 0,
        hc_chart["Required_Total"] / hc_chart["Actual_Total"] * 100,
        np.nan
    )

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([1, 1], gap="medium")

    with left:
        st.markdown(
            '<div class="section-title">ACTUAL vs REQUIRED HC</div>',
            unsafe_allow_html=True
        )

        if hc_chart.empty:
            st.info("No HC data available for the selected filters.")
        else:
            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=hc_chart["Period"],
                    y=hc_chart["Actual_Total"],
                    name="Actual HC",
                    marker_color="#083B82",
                    text=hc_chart["Actual_Total"].round(1),
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=(
                        "<b>%{x}</b>"
                        "<br>Actual HC: %{y:.1f}"
                        "<extra></extra>"
                    ),
                )
            )

            fig.add_trace(
                go.Bar(
                    x=hc_chart["Period"],
                    y=hc_chart["Required_Total"],
                    name="Required HC",
                    marker_color="#ED6B21",
                    text=hc_chart["Required_Total"].round(1),
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=(
                        "<b>%{x}</b>"
                        "<br>Required HC: %{y:.1f}"
                        "<extra></extra>"
                    ),
                )
            )

            fig.update_layout(
                barmode="group",
                height=390,
                margin=dict(l=15, r=15, t=35, b=70),
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(color="#172033"),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0,
                    title_text=""
                ),
                xaxis_title="",
                yaxis_title="Headcount",
                hoverlabel=dict(bgcolor="white"),
            )
            fig.update_xaxes(
                type="category",
                categoryorder="array",
                categoryarray=hc_chart["Period"].tolist(),
                tickangle=-35 if len(hc_chart) > 6 else 0,
                showgrid=False,
                tickfont=dict(size=10),
            )
            fig.update_yaxes(
                rangemode="tozero",
                gridcolor="#E9EEF5",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False},
            )

    with right:
        st.markdown(
            '<div class="section-title">CAPACITY UTILIZATION</div>',
            unsafe_allow_html=True
        )

        util_chart = hc_chart.dropna(subset=["Utilization"]).copy()

        if util_chart.empty:
            st.info("No utilization data available for the selected filters.")
        else:
            # Status colors:
            # <95% = capacity available
            # 95-100% = near full
            # >100% = required HC exceeds actual HC
            util_colors = np.select(
                [
                    util_chart["Utilization"] < 95,
                    util_chart["Utilization"] <= 100,
                ],
                [
                    "#169B62",
                    "#ED6B21",
                ],
                default="#DC2626",
            )

            fig = go.Figure(
                go.Bar(
                    x=util_chart["Period"],
                    y=util_chart["Utilization"],
                    marker_color=util_colors,
                    text=util_chart["Utilization"].map(lambda x: f"{x:.1f}%"),
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=(
                        "<b>%{x}</b>"
                        "<br>Required / Actual HC: %{y:.1f}%"
                        "<extra></extra>"
                    ),
                )
            )

            fig.add_hline(
                y=100,
                line_dash="dash",
                line_color="#DC2626",
                line_width=2,
                annotation_text="100% capacity",
                annotation_position="top right",
            )

            max_util = util_chart["Utilization"].max()
            y_max = max(110, float(max_util) * 1.12)

            fig.update_layout(
                height=390,
                margin=dict(l=15, r=15, t=35, b=70),
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(color="#172033"),
                showlegend=False,
                xaxis_title="",
                yaxis_title="Required / Actual HC (%)",
                hoverlabel=dict(bgcolor="white"),
            )
            fig.update_xaxes(
                type="category",
                categoryorder="array",
                categoryarray=util_chart["Period"].tolist(),
                tickangle=-35 if len(util_chart) > 6 else 0,
                showgrid=False,
                tickfont=dict(size=10),
            )
            fig.update_yaxes(
                range=[0, y_max],
                gridcolor="#E9EEF5",
                ticksuffix="%",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False},
            )

elif page == "Shipment Volume":
    data = ship_f.copy()
    total = data["TOTAL"].sum(min_count=1)
    active = data["Active_Customer"].sum(min_count=1)
    mode_totals = data[MODE_COLS].sum().sort_values(ascending=False)
    top_mode = mode_totals.index[0] if len(mode_totals) and mode_totals.iloc[0] > 0 else "-"
    top_mode_vol = mode_totals.iloc[0] if len(mode_totals) and mode_totals.iloc[0] > 0 else np.nan

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Shipment", fmt_num(total), "Selected office/month scope")
    with c2: kpi_card("Active Customer", fmt_num(active), "Sum of reported active customers")
    with c3: kpi_card("Top Mode", top_mode, f"{fmt_num(top_mode_vol)} shipments" if pd.notna(top_mode_vol) else "", accent="accent-orange")
    with c4:
        avg_per_cust = total/active if pd.notna(total) and pd.notna(active) and active else np.nan
        kpi_card("Shipment / Customer", fmt_num(avg_per_cust, 1), "Average volume per active customer")

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        trend = data.groupby("Month", as_index=False)["TOTAL"].sum().dropna()
        if not trend.empty:
            trend["_m"] = month_sort_key(trend["Month"])
            trend = trend.sort_values("_m")
            fig = px.bar(trend, x="Month", y="TOTAL", text="TOTAL", title="Shipment Volume by Month")
            fig.update_traces(marker_color=ORANGE, texttemplate="%{text:,.0f}", textposition="outside")
            fig = style_fig(fig, 390, legend=False)
            fig.update_xaxes(title="")
            fig.update_yaxes(title="Shipments")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        else:
            st.info("No shipment data available.")

    with right:
        mt = mode_totals[mode_totals > 0].reset_index()
        mt.columns = ["Mode","Volume"]
        mt = mt.head(10).sort_values("Volume")
        if not mt.empty:
            fig = px.bar(mt, x="Volume", y="Mode", orientation="h", text="Volume", title="Top Transportation Modes")
            fig.update_traces(marker_color=BLUE, texttemplate="%{text:,.0f}", textposition="outside")
            fig = style_fig(fig, 390, legend=False)
            fig.update_xaxes(title="Shipment volume")
            fig.update_yaxes(title="")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        else:
            st.info("No transportation mode breakdown available.")

    st.markdown('<div class="section-title">Shipment Detail</div>', unsafe_allow_html=True)
    show_cols = ["Office","Month","Active_Customer"] + MODE_COLS + ["TOTAL"]

    # Final safeguard: hide any remaining month without shipment data.
    detail_value_cols = [
        col for col in ["Active_Customer"] + MODE_COLS
        if col in data.columns
    ]
    shipment_detail = data.copy()

    if detail_value_cols:
        shipment_detail = shipment_detail[
            shipment_detail[detail_value_cols]
            .apply(pd.to_numeric, errors="coerce")
            .fillna(0)
            .sum(axis=1)
            .ne(0)
        ].copy()

    st.dataframe(
        shipment_detail[show_cols],
        use_container_width=True,
        hide_index=True
    )

# ============================================================
# WORKLOAD ALLOCATION
# ============================================================
elif page == "Workload Allocation":
    data = bu_f.copy()
    total_work = data["Total_Workload"].sum(min_count=1)
    seg_tot = data.groupby("Segment")["Total_Workload"].sum().sort_values(ascending=False)
    largest_seg = seg_tot.index[0] if not seg_tot.empty else "-"
    largest_share = seg_tot.iloc[0] / total_work if not seg_tot.empty and pd.notna(total_work) and total_work else np.nan
    exception_time = data["Exception_Time"].sum(min_count=1)

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Workload", fmt_num(total_work), "All workload components")
    with c2: kpi_card("Largest Segment", largest_seg, f"{largest_share:.1%} of workload" if pd.notna(largest_share) else "")
    with c3: kpi_card("Exception Time", fmt_num(exception_time), "Exception handling workload", accent="accent-amber")
    with c4: kpi_card("Segments", fmt_num(data["Segment"].nunique()), "Active business segments")

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        seg = data.groupby("Segment", as_index=False)["Total_Workload"].sum()
        seg["Segment"] = pd.Categorical(seg["Segment"], SEGMENT_ORDER, ordered=True)
        seg = seg.sort_values("Segment")
        if not seg.empty:
            fig = px.bar(seg, x="Segment", y="Total_Workload", text="Total_Workload", title="Workload by Segment")
            fig.update_traces(marker_color=NAVY, texttemplate="%{text:,.0f}", textposition="outside")
            fig = style_fig(fig, 390, legend=False)
            fig.update_xaxes(title="")
            fig.update_yaxes(title="Workload")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        else:
            st.info("No workload allocation data available.")

    with right:
        components = pd.DataFrame({
            "Component": ["Core", "Ancillary", "Supporting", "Exception"],
            "Time": [data["Core_Time"].sum(), data["Ancillary_Time"].sum(), data["Supporting_Time"].sum(), data["Exception_Time"].sum()]
        })
        components = components[components["Time"].notna() & (components["Time"] != 0)]
        if not components.empty:
            fig = px.pie(components, names="Component", values="Time", hole=.55, title="Workload Components")
            fig.update_traces(textinfo="percent+label")
            fig = style_fig(fig, 390, legend=True)
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        else:
            st.info("No workload component detail available for this selection.")

    st.markdown('<div class="section-title">Workload Detail</div>', unsafe_allow_html=True)
    disp = data[["Office","Month","Segment","Core_Time","Ancillary_Time","Supporting_Time","Exception_Time","Total_Workload","Network_Share"]].copy()
    disp["Network_Share"] = disp["Network_Share"].map(lambda x: f"{x:.1%}" if pd.notna(x) else "")
    st.dataframe(disp, use_container_width=True, hide_index=True)

# ============================================================
# CUSTOMER VOLUME
# ============================================================
elif page == "Customer Volume":
    data = cust.copy()
    if office != "All Offices":
        data = data[data["Office"] == office]

    # Determine FY columns found in workbook, preserving source order.
    value_cols = [c for c in data.columns if c not in ["No", "Office", "Customer", "Total"]]
    selected_period = None
    if month != "All Months":
        matching = [c for c in value_cols if str(c).startswith(month)]
        selected_period = matching[0] if matching else None

    metric_col = selected_period if selected_period else "Total"
    metric_label = selected_period if selected_period else "FY Total"
    ranked = data[["Office","Customer",metric_col]].copy()
    ranked[metric_col] = pd.to_numeric(ranked[metric_col], errors="coerce").fillna(0)
    ranked = ranked[ranked[metric_col] > 0].sort_values(metric_col, ascending=False)

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Customers", fmt_num(data["Customer"].nunique()), "Customers in selected office")
    with c2: kpi_card(metric_label, fmt_num(ranked[metric_col].sum()), "Customer shipment volume")
    with c3: kpi_card("Top Customer", ranked.iloc[0]["Customer"] if not ranked.empty else "-", "Highest shipment volume", accent="accent-orange")
    with c4: kpi_card("Top Customer Volume", fmt_num(ranked.iloc[0][metric_col]) if not ranked.empty else "-", metric_label)

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        top = ranked.head(15).sort_values(metric_col)
        if not top.empty:
            fig = px.bar(top, x=metric_col, y="Customer", orientation="h", text=metric_col, title=f"Top 15 Customers - {metric_label}")
            fig.update_traces(marker_color=BLUE, texttemplate="%{text:,.0f}", textposition="outside")
            fig = style_fig(fig, 500, legend=False)
            fig.update_xaxes(title="Shipment volume")
            fig.update_yaxes(title="")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        else:
            st.info("No customer shipment data for the selected filters.")

    with right:
        if not ranked.empty:
            top10 = ranked.head(10).copy()
            total_ranked = ranked[metric_col].sum()
            top10["Share"] = np.where(total_ranked > 0, top10[metric_col] / total_ranked, 0)
            fig = go.Figure(go.Pie(labels=top10["Customer"], values=top10[metric_col], hole=.58))
            fig.update_traces(textinfo="percent", hovertemplate="%{label}<br>%{value:,.0f}<br>%{percent}<extra></extra>")
            fig.update_layout(title="Top 10 Customer Contribution")
            fig = style_fig(fig, 500, legend=True)
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        else:
            st.info("No customer contribution data available.")

    st.markdown('<div class="section-title">Customer Volume Detail</div>', unsafe_allow_html=True)
    detail_cols = ["Office","Customer"] + value_cols + ["Total"]
    st.dataframe(data[detail_cols].sort_values("Total", ascending=False), use_container_width=True, hide_index=True)

st.markdown("<div style='text-align:center;color:#8A98A8;font-size:11px;margin-top:24px;'>© 2026 CS | Internal Use Only</div>", unsafe_allow_html=True)
