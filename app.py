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
            --page: {LIGHT_BG};
        }}

        html, body, [class*="css"] {{font-family: Arial, "Segoe UI", sans-serif;}}
        .stApp {{background:var(--page); color:var(--text);}}
        [data-testid="stHeader"] {{height:3.25rem; background:var(--page);}}
        [data-testid="stToolbar"] {{top:.35rem;}}
        .block-container {{max-width:1600px; padding-top:1.65rem; padding-bottom:2rem;}}

        [data-testid="stSidebar"] {{background:linear-gradient(180deg,#073472 0%,#0B4D9B 100%);}}
        [data-testid="stSidebar"] * {{color:#FFFFFF;}}
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stRadio label {{color:#FFFFFF !important; font-weight:600;}}
        [data-testid="stSidebar"] div[data-baseweb="select"] * {{color:#17324D !important;}}

        .dashboard-title {{
            display:block; position:static; font-size:1.9rem; line-height:1.15;
            font-weight:800; color:{NAVY} !important; opacity:1 !important;
            filter:none !important; text-shadow:none !important; -webkit-text-fill-color:{NAVY} !important;
            margin:0 0 .35rem 0; letter-spacing:-.02em;
        }}
        .dashboard-subtitle {{
            display:block; color:#667085 !important; font-size:.82rem; line-height:1.2;
            margin:0 0 .75rem 0;
        }}
        .dashboard-filter {{
            color:#667085; font-size:.76rem; margin:-.25rem 0 .9rem 0;
        }}

        .section-title {{
            background:var(--navy); color:#FFFFFF; padding:.52rem .8rem;
            border-radius:10px 10px 0 0; font-size:.95rem; font-weight:750;
            margin-top:.25rem; margin-bottom:0;
        }}

        .kpi-card {{
            background:var(--panel); border:1px solid var(--line); border-radius:12px;
            height:142px; min-height:142px; max-height:142px; display:flex;
            flex-direction:column; justify-content:center; align-items:center;
            box-sizing:border-box; overflow:hidden; box-shadow:0 2px 10px rgba(28,54,89,.05);
            padding:0 12px;
        }}
        .kpi-label {{
            color:var(--navy); font-size:.88rem; font-weight:700; text-align:center;
            margin-bottom:12px; text-transform:none; letter-spacing:0;
        }}
        .kpi-value {{
            font-size:2.25rem; font-weight:800; line-height:1; color:var(--blue);
            text-align:center; margin:0;
        }}
        .kpi-note {{
            color:var(--muted); font-size:.71rem; line-height:1.2; margin-top:.48rem;
            text-align:center; padding:0 .4rem;
        }}
        .accent-orange .kpi-value {{color:var(--orange);}}
        .accent-green .kpi-value {{color:var(--green);}}
        .accent-amber .kpi-value {{color:var(--amber);}}
        .accent-red .kpi-value {{color:var(--red);}}

        .panel {{background:white; border:1px solid var(--line); border-radius:12px; padding:12px 14px;}}
        div[data-testid="stDataFrame"] {{border:1px solid var(--line); border-radius:10px; overflow:hidden;}}
        h1,h2,h3 {{color:var(--navy);}}
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
    st.markdown("## 📊 CS Workload")
    st.caption("Capacity & Shipment Dashboard")
    st.markdown("---")
    page = st.radio(
        "Navigation",
        ["Overview", "HC Capacity", "Shipment Volume", "Workload Allocation", "Customer Volume"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    uploaded = st.file_uploader("Upload updated Excel", type=["xlsx", "xlsm"])

try:
    source = uploaded if uploaded is not None else discover_default_excel()
    if source is None:
        st.error("No Excel workbook found. Please upload the workload workbook from the sidebar.")
        st.stop()
    hc, ship, bu, cust = load_data(source)
except Exception as e:
    st.error(f"Cannot read workbook: {e}")
    st.stop()

# Last-updated label for the dashboard header.
if uploaded is not None:
    data_date = "Uploaded file"
else:
    try:
        data_date = pd.Timestamp(Path(source).stat().st_mtime, unit="s").strftime("%d %b %Y")
    except Exception:
        data_date = "Not available"

# Global filters
all_offices = sorted(set(hc["Office"].dropna()) | set(ship["Office"].dropna()) | set(bu["Office"].dropna()))
with st.sidebar:
    st.markdown("### Filters")
    office = st.selectbox("Office", ["All Offices"] + all_offices)

    available_months = []
    for m in MONTH_ORDER:
        exists = (
            ((hc["Month"] == m) & ((hc["Office"] == office) if office != "All Offices" else True)).any()
            or ((ship["Month"] == m) & ((ship["Office"] == office) if office != "All Offices" else True)).any()
            or ((bu["Month"] == m) & ((bu["Office"] == office) if office != "All Offices" else True)).any()
        )
        if exists:
            available_months.append(m)
    month = st.selectbox("Month", ["All Months"] + available_months)
    st.markdown("---")
    st.caption("FY2026 | Internal Use Only")

hc_f = filtered(hc, office, month)
ship_f = filtered(ship, office, month)
bu_f = filtered(bu, office, month)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="dashboard-title">CS WORKLOAD & CAPACITY DASHBOARD</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="dashboard-subtitle">📅 Last Updated: {data_date}</div>',
    unsafe_allow_html=True,
)
filter_text = f"FY2026 &nbsp; • &nbsp; Office: {office} &nbsp; • &nbsp; Month: {month}"
st.markdown(f'<div class="dashboard-filter">{filter_text}</div>', unsafe_allow_html=True)

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
    capacity = (required_hc / actual_hc) if pd.notna(actual_hc) and actual_hc else np.nan
    total_ship = ship_f["TOTAL"].sum(min_count=1)
    active_cust = ship_f["Active_Customer"].sum(min_count=1)
    workload = bu_f["Total_Workload"].sum(min_count=1)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: kpi_card("Actual HC", fmt_num(actual_hc), "Latest available HC in selected scope")
    with c2: kpi_card("Required HC", fmt_num(required_hc, 1), "Calculated workforce requirement")
    with c3:
        cap_note = "Overload" if pd.notna(capacity) and capacity > 1 else "Within capacity"
        kpi_card("Capacity Load", f"{capacity:.1%}" if pd.notna(capacity) else "-", cap_note, accent="accent-orange" if pd.notna(capacity) and capacity > 1 else "accent-green")
    with c4: kpi_card("Shipment Volume", fmt_num(total_ship), "Total shipments in selected period", accent="accent-orange")
    with c5: kpi_card("Total Workload", fmt_num(workload), "Processing time / workload units")

    st.markdown('<div class="section-title">Management Overview</div>', unsafe_allow_html=True)
    left, right = st.columns([1.05, 1], gap="large")

    with left:
        cap_df = hc_f.dropna(subset=["Capacity"]).copy()
        if not cap_df.empty:
            cap_df["Capacity %"] = cap_df["Capacity"] * 100
            cap_df["Office-Month"] = cap_df["Office"] + " - " + cap_df["Month"]
            fig = px.bar(cap_df, x="Office-Month", y="Capacity %", text="Capacity %", title="HC Capacity Load")
            fig.update_traces(marker_color=BLUE, texttemplate="%{text:.1f}%", textposition="outside")
            fig.add_hline(y=100, line_dash="dash", line_color=RED, annotation_text="100% capacity")
            fig = style_fig(fig, 370, legend=False)
            fig.update_yaxes(title="Capacity load (%)")
            fig.update_xaxes(title="")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        else:
            st.info("No HC capacity data for the selected filters.")

    with right:
        seg = bu_f.groupby("Segment", as_index=False)["Total_Workload"].sum().dropna()
        if not seg.empty:
            seg["Segment"] = pd.Categorical(seg["Segment"], SEGMENT_ORDER, ordered=True)
            seg = seg.sort_values("Segment")
            fig = px.pie(seg, names="Segment", values="Total_Workload", hole=.58, title="Workload Mix by Business Segment")
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig = style_fig(fig, 370, legend=True)
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        else:
            st.info("No workload allocation data for the selected filters.")

    left, right = st.columns([1.25, 1], gap="large")
    with left:
        trend = ship_f.groupby("Month", as_index=False)["TOTAL"].sum().dropna()
        if not trend.empty:
            trend["_m"] = month_sort_key(trend["Month"])
            trend = trend.sort_values("_m")
            fig = px.line(trend, x="Month", y="TOTAL", markers=True, title="Shipment Volume Trend")
            fig.update_traces(line_color=ORANGE, marker=dict(size=8))
            fig = style_fig(fig, 340, legend=False)
            fig.update_yaxes(title="Shipments")
            fig.update_xaxes(title="")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        else:
            st.info("No shipment trend data for the selected filters.")

    with right:
        office_work = bu_f.groupby("Office", as_index=False)["Total_Workload"].sum().sort_values("Total_Workload")
        if not office_work.empty:
            fig = px.bar(office_work, y="Office", x="Total_Workload", orientation="h", text="Total_Workload", title="Workload by Office")
            fig.update_traces(marker_color=NAVY, texttemplate="%{text:,.0f}", textposition="outside")
            fig = style_fig(fig, 340, legend=False)
            fig.update_xaxes(title="Workload")
            fig.update_yaxes(title="")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        else:
            st.info("No workload data for the selected filters.")

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

    left, right = st.columns([1.25, 1], gap="large")
    with left:
        chart = valid.copy()
        if not chart.empty:
            chart["_m"] = month_sort_key(chart["Month"])
            chart = chart.sort_values(["Office", "_m"])
            long = chart.melt(id_vars=["Office", "Month"], value_vars=["Actual_Total", "Required_Total"], var_name="HC Type", value_name="HC")
            long["HC Type"] = long["HC Type"].map({"Actual_Total":"Actual HC", "Required_Total":"Required HC"})
            long["Period"] = long["Office"] + " - " + long["Month"]
            fig = px.bar(long, x="Period", y="HC", color="HC Type", barmode="group", title="Actual vs Required HC")
            fig = style_fig(fig, 390, legend=True)
            fig.update_xaxes(title="")
            fig.update_yaxes(title="Headcount")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        else:
            st.info("No actual/required HC data available.")

    with right:
        cap = valid.copy()
        if not cap.empty:
            cap["Capacity %"] = cap["Capacity"] * 100
            cap["Period"] = cap["Office"] + " - " + cap["Month"]
            fig = px.bar(cap, x="Period", y="Capacity %", title="Capacity Utilization")
            fig.update_traces(marker_color=BLUE)
            fig.add_hrect(y0=100, y1=max(115, cap["Capacity %"].max()+5), fillcolor=RED, opacity=.06, line_width=0)
            fig.add_hline(y=100, line_dash="dash", line_color=RED)
            fig = style_fig(fig, 390, legend=False)
            fig.update_yaxes(title="Required / Actual HC (%)")
            fig.update_xaxes(title="")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        else:
            st.info("No capacity utilization data available.")

    st.markdown('<div class="section-title">HC Status Detail</div>', unsafe_allow_html=True)
    display = data[["Office","Month","Approved_Total","Actual_Total","Required_Total","Capacity","Status"]].copy()
    display["Capacity"] = display["Capacity"].map(lambda x: f"{x:.1%}" if pd.notna(x) else "")
    display.columns = ["Office","Month","Approved HC","Actual HC","Required HC","Capacity","Status"]
    st.dataframe(display, use_container_width=True, hide_index=True)

# ============================================================
# SHIPMENT VOLUME
# ============================================================
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
    st.dataframe(data[show_cols], use_container_width=True, hide_index=True)

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
