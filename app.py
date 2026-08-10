from pathlib import Path
import io
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# 01. APP CONFIG
# ============================================================
st.set_page_config(
    page_title="Operations Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "OPERATIONS PERFORMANCE DASHBOARD"
APP_SUBTITLE = "CS Workload • Capacity • Workforce • Service Mix"

FTE_HOURS_PER_DAY = 8
EFFICIENCY = 0.95
WORKING_DAYS = 22
FTE_MINUTES = FTE_HOURS_PER_DAY * 60 * EFFICIENCY * WORKING_DAYS  # 10,032 min/month

MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
SERVICE_ORDER = ["AE", "AI", "OE", "OI", "CC", "TR", "WH"]
SERVICE_LABELS = {
    "AE": "Air Export", "AI": "Air Import", "OE": "Ocean Export",
    "OI": "Ocean Import", "CC": "Customs Clearance", "TR": "Trucking", "WH": "Warehouse",
}
SERVICE_COLORS = {
    "AE": "#45BD8C", "AI": "#00B9F2", "OE": "#FFC933", "OI": "#FF6D10",
    "CC": "#0074A6", "TR": "#06183D", "WH": "#94A3B8",
}
STATUS_COLORS = {
    "Overload": "#DC2626", "High Load": "#F97316", "Balanced": "#2563EB",
    "Low Load": "#16A34A", "No data": "#94A3B8",
}
ACTIVITY_COLORS = {
    "Core": "#06183D", "Ancillary": "#00B9F2", "Supporting": "#45BD8C", "Exception": "#FF6D10"
}

# ============================================================
# 02. CORPORATE STYLE
# ============================================================
st.markdown(
    """
    <style>
    :root{
      --navy:#06183D; --blue:#00B9F2; --green:#45BD8C; --orange:#FF6D10;
      --amber:#FFC933; --red:#DC2626; --ink:#162033; --muted:#667085;
      --line:#D9E2EC; --page:#F4F7FB; --panel:#FFFFFF;
    }
    .stApp{background:var(--page)}
    .block-container{max-width:1680px;padding-top:2rem;padding-bottom:2.5rem}
    [data-testid="stSidebar"]{background:linear-gradient(180deg,#06183D 0%,#0C2B63 100%)}
    [data-testid="stSidebar"] *{color:#FFFFFF}
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
    section[data-testid="stSidebar"] div[data-baseweb="input"] > div{background:#FFFFFF!important;border-radius:10px!important}
    section[data-testid="stSidebar"] div[data-baseweb="select"] span,
    section[data-testid="stSidebar"] div[data-baseweb="select"] input,
    section[data-testid="stSidebar"] div[data-baseweb="input"] input{color:#172033!important;-webkit-text-fill-color:#172033!important}
    div[data-baseweb="popover"] *{color:#172033!important}

    .eyebrow{font-size:.72rem;font-weight:800;letter-spacing:.12em;color:#0074A6;text-transform:uppercase;margin-bottom:.25rem}
    .hero-title{font-size:2rem;font-weight:900;color:var(--navy);letter-spacing:-.035em;line-height:1.05}
    .hero-sub{font-size:.86rem;color:var(--muted);margin-top:.35rem}
    .hero-rule{height:4px;width:74px;background:var(--orange);border-radius:99px;margin:.65rem 0 1rem 0}

    .section-head{display:flex;align-items:center;justify-content:space-between;margin:1.05rem 0 .55rem 0}
    .section-title{font-size:1rem;font-weight:900;color:var(--navy);letter-spacing:.015em}
    .section-note{font-size:.74rem;color:var(--muted)}

    .kpi{background:#FFF;border:1px solid var(--line);border-radius:14px;padding:15px 16px;min-height:134px;
         box-shadow:0 3px 14px rgba(6,24,61,.045);position:relative;overflow:hidden}
    .kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--accent,#00B9F2)}
    .kpi-label{font-size:.73rem;font-weight:800;color:#475467;text-transform:uppercase;letter-spacing:.045em}
    .kpi-value{font-size:2rem;font-weight:900;color:var(--navy);line-height:1.05;margin-top:.45rem}
    .kpi-note{font-size:.73rem;color:var(--muted);margin-top:.48rem;line-height:1.25}

    .insight{background:#FFF;border:1px solid var(--line);border-radius:14px;padding:16px 18px;min-height:108px}
    .insight-kicker{font-size:.72rem;text-transform:uppercase;font-weight:850;letter-spacing:.06em;color:#667085}
    .insight-main{font-size:1.06rem;font-weight:900;color:var(--navy);margin-top:.3rem}
    .insight-text{font-size:.79rem;color:#475467;margin-top:.32rem;line-height:1.35}

    .status-chip{display:inline-block;padding:5px 9px;border-radius:999px;color:#fff;font-size:.72rem;font-weight:850}
    .panel{background:#FFF;border:1px solid var(--line);border-radius:14px;padding:10px 12px;box-shadow:0 2px 10px rgba(6,24,61,.035)}
    div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:12px;overflow:hidden}
    div[data-testid="stPlotlyChart"]{background:#FFF;border:1px solid var(--line);border-radius:14px;padding:5px 7px}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 03. HELPERS
# ============================================================
def clean_text(v):
    if pd.isna(v):
        return ""
    return re.sub(r"\s+", " ", str(v)).strip()


def normalize_month(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if hasattr(v, "strftime") and not isinstance(v, str):
        try:
            return v.strftime("%b")
        except Exception:
            pass
    s = clean_text(v)
    if not s:
        return ""
    try:
        return pd.to_datetime(s, errors="raise").strftime("%b")
    except Exception:
        abbr = s[:3].title()
        return abbr if abbr in MONTH_ORDER else ""


def safe_divide(a, b):
    try:
        return float(a) / float(b) if float(b) != 0 else 0.0
    except Exception:
        return 0.0


def load_status(util):
    if util is None or pd.isna(util):
        return "No data"
    if util > 1.00:
        return "Overload"
    if util > 0.95:
        return "High Load"
    if util >= 0.90:
        return "Balanced"
    return "Low Load"


def fmt_num(v, decimals=0):
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.{decimals}f}"


def fmt_h(minutes):
    if minutes is None or pd.isna(minutes):
        return "—"
    return f"{minutes/60:,.0f} h"


def kpi_card(label, value, note="", accent="#00B9F2"):
    st.markdown(
        f"""<div class='kpi' style='--accent:{accent}'>
        <div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div>
        <div class='kpi-note'>{note if note else '&nbsp;'}</div></div>""",
        unsafe_allow_html=True,
    )


def section(title, note=""):
    st.markdown(
        f"<div class='section-head'><div class='section-title'>{title}</div><div class='section-note'>{note}</div></div>",
        unsafe_allow_html=True,
    )


def chart_style(fig, height=340, legend=True):
    fig.update_layout(
        height=height, margin=dict(l=18, r=20, t=28, b=18), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family="Arial", color="#172033", size=12), legend_title_text="", showlegend=legend,
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#E9EEF5", zeroline=False)
    return fig


def check_columns(actual_cols, expected_keywords, sheet_name):
    cleaned = [clean_text(c).casefold() for c in actual_cols]
    for i, kw in enumerate(expected_keywords):
        if i >= len(cleaned) or kw not in cleaned[i]:
            raise ValueError(f"Sheet '{sheet_name}' changed at column {i+1}. Expected keyword: '{kw}'.")

# ============================================================
# 04. DATA SOURCE
# ============================================================
def find_source_path():
    app_dir = Path(__file__).resolve().parent
    candidates = [p for ext in ("*.xlsx", "*.xlsm") for p in app_dir.rglob(ext) if not p.name.startswith("~$")]
    required = {"HC", "BU allocation", "CS FTE"}
    for p in sorted(candidates, key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            xl = pd.ExcelFile(p)
            sheets = set(xl.sheet_names)
            has_customer = any(s.startswith("Customer Volume") for s in xl.sheet_names)
            if required.issubset(sheets) and has_customer:
                return p
        except Exception:
            continue
    return None


@st.cache_data(show_spinner=False)
def read_bytes(path, mtime):
    p = Path(path)
    return p.read_bytes(), p.name

# ============================================================
# 05. PARSERS — Excel remains calculation layer
# ============================================================
@st.cache_data(show_spinner=False)
def parse_bu(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="BU allocation", header=1)
    expected = [
        "office", "month", "segment", "core volume", "core workload", "ancillary volume", "ancillary workload",
        "supporting volume", "supporting workload", "exception volume", "exception workload", "total workload", "workload share"
    ]
    check_columns(df.columns, expected, "BU allocation")
    df = df.iloc[:, :13].copy()
    df.columns = [
        "Office", "Month", "Segment", "Core Volume", "Core Workload", "Ancillary Volume", "Ancillary Workload",
        "Supporting Volume", "Supporting Workload", "Exception Volume", "Exception Workload", "Total Workload", "Workload Share Raw"
    ]
    for c in ["Office", "Segment"]:
        df[c] = df[c].map(clean_text)
    df["Month"] = df["Month"].map(normalize_month)
    numeric = [c for c in df.columns if c not in ["Office", "Month", "Segment"]]
    for c in numeric:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df = df[df["Office"].ne("") & df["Month"].isin(MONTH_ORDER) & df["Segment"].isin(SERVICE_ORDER)].copy()
    return df


@st.cache_data(show_spinner=False)
def parse_hc(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="HC", header=1)
    check_columns(df.columns, ["office", "month"], "HC")
    if df.shape[1] < 13:
        raise ValueError("Sheet 'HC' must contain at least 13 columns.")
    df = df.iloc[:, :13].copy()
    df.columns = [
        "Office", "Month", "Approved HC Mgr", "Approved HC PIC", "Total Approved HC",
        "Actual HC Mgr", "Actual HC PIC", "Total Actual HC",
        "Required HC Mgr", "Required HC PIC", "Total Required HC", "HC Utilization", "HC Status"
    ]
    df["Office"] = df["Office"].map(clean_text)
    df["Month"] = df["Month"].map(normalize_month)
    df["HC Status"] = df["HC Status"].map(clean_text)
    for c in df.columns[2:12]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[df["Office"].ne("") & df["Month"].isin(MONTH_ORDER)].copy()


@st.cache_data(show_spinner=False)
def parse_cs_fte(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="CS FTE", header=1)
    if df.shape[1] < 3:
        return pd.DataFrame(columns=["Office", "CS PIC", "Month", "FTE", "PIC Workload"])
    office_col, pic_col = df.columns[:2]
    df[office_col] = df[office_col].map(clean_text)
    df[pic_col] = df[pic_col].map(clean_text)
    df = df[df[office_col].ne("") & df[pic_col].ne("")]
    month_cols = list(df.columns[2:])
    long = df.melt(id_vars=[office_col, pic_col], value_vars=month_cols, var_name="RawMonth", value_name="FTE")
    long["Month"] = long["RawMonth"].map(normalize_month)
    long["FTE"] = pd.to_numeric(long["FTE"], errors="coerce")
    long = long[long["Month"].isin(MONTH_ORDER)].dropna(subset=["FTE"])
    long = long.rename(columns={office_col: "Office", pic_col: "CS PIC"})
    long["PIC Workload"] = long["FTE"] * FTE_MINUTES
    return long[["Office", "CS PIC", "Month", "FTE", "PIC Workload"]]


@st.cache_data(show_spinner=False)
def parse_customer(file_bytes):
    xl = pd.ExcelFile(io.BytesIO(file_bytes))
    frames = []
    for sheet in [s for s in xl.sheet_names if s.startswith("Customer Volume")]:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=1)
        if df.shape[1] < 4:
            continue
        office_col, customer_col = df.columns[1], df.columns[2]
        df[office_col] = df[office_col].map(clean_text)
        df[customer_col] = df[customer_col].map(clean_text)
        df = df[df[office_col].ne("") & df[customer_col].ne("")]
        value_cols = [c for c in df.columns[3:] if clean_text(c).casefold() != "total"]
        if not value_cols:
            continue
        x = df.melt(id_vars=[office_col, customer_col], value_vars=value_cols, var_name="RawMonth", value_name="Volume")
        x["Month"] = x["RawMonth"].map(normalize_month)
        x["Volume"] = pd.to_numeric(x["Volume"], errors="coerce")
        x = x[x["Month"].isin(MONTH_ORDER)].dropna(subset=["Volume"])
        x = x.rename(columns={office_col: "Office", customer_col: "Customer"})
        x["_priority"] = 1 if sheet.strip() == "Customer Volume-N&S" else 0
        frames.append(x[["Office", "Customer", "Month", "Volume", "_priority"]])
    if not frames:
        return pd.DataFrame(columns=["Office", "Customer", "Month", "Volume"])
    out = pd.concat(frames, ignore_index=True).sort_values("_priority")
    out = out.drop_duplicates(["Office", "Customer", "Month"], keep="first")
    return out[["Office", "Customer", "Month", "Volume"]]


@st.cache_data(show_spinner=False)
def parse_scope(file_bytes, sheet_name):
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=1)
    except Exception:
        return pd.DataFrame(columns=["Office", "Scope", "Month", "Volume"])
    if df.shape[1] < 3:
        return pd.DataFrame(columns=["Office", "Scope", "Month", "Volume"])
    office_col, scope_col = df.columns[:2]
    df[office_col] = df[office_col].map(clean_text)
    df[scope_col] = df[scope_col].map(clean_text)
    df = df[df[office_col].ne("") & df[scope_col].ne("")]
    value_cols = [c for c in df.columns[2:] if clean_text(c).casefold() != "total"]
    x = df.melt(id_vars=[office_col, scope_col], value_vars=value_cols, var_name="RawMonth", value_name="Volume")
    x["Month"] = x["RawMonth"].map(normalize_month)
    x["Volume"] = pd.to_numeric(x["Volume"], errors="coerce")
    x = x[x["Month"].isin(MONTH_ORDER)].dropna(subset=["Volume"])
    return x.rename(columns={office_col: "Office", scope_col: "Scope"})[["Office", "Scope", "Month", "Volume"]]

# ============================================================
# 06. LOAD DATA
# ============================================================
source_path = find_source_path()
if source_path is None:
    st.error("No compatible dashboard data file found.")
    st.info(
        "Place the calculated Excel file in the same folder as this app. Required sheets: "
        "HC, BU allocation, CS FTE and at least one sheet beginning with 'Customer Volume'. "
        "Both .xlsx and .xlsm are supported."
    )
    st.stop()

file_bytes, source_name = read_bytes(str(source_path), source_path.stat().st_mtime)
try:
    bu = parse_bu(file_bytes)
    hc = parse_hc(file_bytes)
    cs = parse_cs_fte(file_bytes)
    customer = parse_customer(file_bytes)
    core_detail = parse_scope(file_bytes, "C")
    ancillary_detail = parse_scope(file_bytes, "A")
    supporting_detail = parse_scope(file_bytes, "S")
except Exception as exc:
    st.error("The Excel structure does not match the dashboard data model.")
    st.exception(exc)
    st.stop()

# ============================================================
# 07. FILTERS
# ============================================================
st.sidebar.markdown("## CS DIVISION")
st.sidebar.markdown("<div style='font-size:13px;color:#D8E5F8;margin-top:-10px'>Executive performance cockpit</div>", unsafe_allow_html=True)
st.sidebar.markdown("---")

all_offices = sorted(set(bu.Office.dropna()) | set(hc.Office.dropna()) | set(cs.Office.dropna()) | set(customer.Office.dropna()))
available_months = [m for m in MONTH_ORDER if m in set(bu.loc[bu["Total Workload"] > 0, "Month"].astype(str))]

if "office" not in st.session_state:
    st.session_state.office = "All Offices"
if "month" not in st.session_state:
    st.session_state.month = "All"
if "pic" not in st.session_state:
    st.session_state.pic = "All CS PIC"
if "customer" not in st.session_state:
    st.session_state.customer = "All Customers"


def reset_children():
    st.session_state.pic = "All CS PIC"
    st.session_state.customer = "All Customers"


office = st.sidebar.selectbox("Office", ["All Offices"] + all_offices, key="office", on_change=reset_children)
month = st.sidebar.selectbox("Reporting month", ["All"] + available_months, key="month", on_change=reset_children)

pic_scope = cs.copy()
if office != "All Offices":
    pic_scope = pic_scope[pic_scope.Office.eq(office)]
if month != "All":
    pic_scope = pic_scope[pic_scope.Month.eq(month)]
pic_options = sorted(pic_scope["CS PIC"].dropna().unique())
if st.session_state.pic not in ["All CS PIC"] + pic_options:
    st.session_state.pic = "All CS PIC"
cs_pic = st.sidebar.selectbox("CS PIC", ["All CS PIC"] + pic_options, key="pic")

cust_scope = customer.copy()
if office != "All Offices":
    cust_scope = cust_scope[cust_scope.Office.eq(office)]
if month != "All":
    cust_scope = cust_scope[cust_scope.Month.eq(month)]
cust_options = sorted(cust_scope.Customer.dropna().unique())
if st.session_state.customer not in ["All Customers"] + cust_options:
    st.session_state.customer = "All Customers"
selected_customer = st.sidebar.selectbox("Customer", ["All Customers"] + cust_options, key="customer")

if st.sidebar.button("Reset filters", use_container_width=True):
    st.session_state.office = "All Offices"
    st.session_state.month = "All"
    st.session_state.pic = "All CS PIC"
    st.session_state.customer = "All Customers"
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"Data source: {source_name}")
st.sidebar.caption("1 FTE = 10,032 productive minutes/month")

# Base filtering
f_bu = bu.copy()
f_hc = hc.copy()
f_cs = cs.copy()
f_cust = customer.copy()
for df_name in ["f_bu", "f_hc", "f_cs", "f_cust"]:
    df = locals()[df_name]
    if office != "All Offices":
        df = df[df.Office.eq(office)]
    if month != "All":
        df = df[df.Month.eq(month)]
    locals()[df_name] = df

# IMPORTANT: customer filter only impacts customer view; it does not alter workload because no customer-workload mapping exists.
if selected_customer != "All Customers":
    f_cust = f_cust[f_cust.Customer.eq(selected_customer)]

# CS PIC estimation based on share of FTE in selected office/month
pic_share = None
pic_fte = None
if cs_pic != "All CS PIC" and not f_cs.empty:
    selected_pic = f_cs[f_cs["CS PIC"].eq(cs_pic)]
    pic_fte = selected_pic.FTE.sum()
    denominator = f_cs.FTE.sum()
    pic_share = safe_divide(pic_fte, denominator)
    for col in ["Core Volume", "Core Workload", "Ancillary Volume", "Ancillary Workload", "Supporting Volume", "Supporting Workload", "Exception Volume", "Exception Workload", "Total Workload"]:
        f_bu[col] = f_bu[col] * pic_share

# ============================================================
# 08. KPI ENGINE
# ============================================================
workload_months = [m for m in MONTH_ORDER if m in set(f_bu.loc[f_bu["Total Workload"] > 0, "Month"].astype(str))]
months_count = 1 if month != "All" else max(len(workload_months), 1)
capacity_per_fte = FTE_MINUTES * months_count

total_workload = float(f_bu["Total Workload"].sum())
total_shipments = float(f_bu["Core Volume"].sum())
required_fte_workload = safe_divide(total_workload, capacity_per_fte)

service = f_bu.groupby("Segment", as_index=False).agg(
    Shipments=("Core Volume", "sum"), Core=("Core Workload", "sum"), Ancillary=("Ancillary Workload", "sum"),
    Supporting=("Supporting Workload", "sum"), Exception=("Exception Workload", "sum"), Total=("Total Workload", "sum")
)
service = pd.DataFrame({"Segment": SERVICE_ORDER}).merge(service, how="left", on="Segment").fillna(0)
service["Service"] = service.Segment.map(SERVICE_LABELS)
service["Hours"] = service.Total / 60
service["Share"] = np.where(service.Total.sum() > 0, service.Total / service.Total.sum(), 0)
service["Required FTE"] = service.Total / capacity_per_fte

top_service_row = service.loc[service.Total.idxmax()] if service.Total.sum() > 0 else None
top_service = top_service_row.Service if top_service_row is not None else "—"
top_service_share = top_service_row.Share if top_service_row is not None else 0

# HC calculations
hc_valid = f_hc[f_hc["Total Actual HC"].notna() | f_hc["Total Required HC"].notna() | f_hc["Total Approved HC"].notna()].copy()
if hc_valid.empty:
    approved_hc = actual_hc = required_hc = np.nan
else:
    if month == "All":
        monthly = hc_valid.groupby("Month", as_index=False).agg(
            Approved=("Total Approved HC", "sum"), Actual=("Total Actual HC", "sum"), Required=("Total Required HC", "sum")
        )
        approved_hc, actual_hc, required_hc = monthly[["Approved", "Actual", "Required"]].mean().tolist()
    else:
        approved_hc = hc_valid["Total Approved HC"].sum()
        actual_hc = hc_valid["Total Actual HC"].sum()
        required_hc = hc_valid["Total Required HC"].sum()

utilization = safe_divide(required_hc, actual_hc) if not pd.isna(actual_hc) and actual_hc else np.nan
status = load_status(utilization)
hc_gap = (actual_hc - required_hc) if not (pd.isna(actual_hc) or pd.isna(required_hc)) else np.nan

# Office status table
if not hc_valid.empty:
    if month == "All":
        om = hc_valid.groupby(["Office", "Month"], as_index=False).agg(Actual=("Total Actual HC", "sum"), Required=("Total Required HC", "sum"))
        office_cap = om.groupby("Office", as_index=False).agg(Actual=("Actual", "mean"), Required=("Required", "mean"))
    else:
        office_cap = hc_valid.groupby("Office", as_index=False).agg(Actual=("Total Actual HC", "sum"), Required=("Total Required HC", "sum"))
    office_cap["Utilization"] = office_cap.apply(lambda r: safe_divide(r.Required, r.Actual) if r.Actual else np.nan, axis=1)
    office_cap["Status"] = office_cap.Utilization.map(load_status)
    office_cap["Gap"] = office_cap.Actual - office_cap.Required
else:
    office_cap = pd.DataFrame(columns=["Office", "Actual", "Required", "Utilization", "Status", "Gap"])

overload_count = int((office_cap.Status == "Overload").sum()) if not office_cap.empty else 0

# ============================================================
# 09. HEADER + 10-SECOND EXECUTIVE STORY
# ============================================================
st.markdown("<div class='eyebrow'>Nationwide Customer Service</div>", unsafe_allow_html=True)
st.markdown(f"<div class='hero-title'>{APP_TITLE}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='hero-sub'>{APP_SUBTITLE} &nbsp;|&nbsp; Office: {office} &nbsp;|&nbsp; Month: {month} &nbsp;|&nbsp; CS PIC: {cs_pic}</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-rule'></div>", unsafe_allow_html=True)

if cs_pic != "All CS PIC":
    st.warning(
        f"CS PIC view is an estimate: workload is allocated by {cs_pic}'s FTE share ({pic_fte:.2f} FTE; {pic_share:.1%} of selected office/month). "
        "The source file does not contain actual workload by service at individual PIC level."
    )

k1, k2, k3, k4, k5, k6 = st.columns(6, gap="small")
with k1:
    kpi_card("Capacity status", status, f"Utilization {utilization:.1%}" if not pd.isna(utilization) else "No HC data", STATUS_COLORS[status])
with k2:
    gap_note = "Available minus required HC"
    kpi_card("HC gap", fmt_num(hc_gap, 1), gap_note, "#DC2626" if not pd.isna(hc_gap) and hc_gap < 0 else "#45BD8C")
with k3:
    kpi_card("Required HC", fmt_num(required_hc, 1), f"Actual HC {fmt_num(actual_hc,1)}", "#FF6D10")
with k4:
    kpi_card("Total workload", fmt_h(total_workload), f"{fmt_num(required_fte_workload,2)} FTE workload-based", "#00B9F2")
with k5:
    kpi_card("Shipment volume", fmt_num(total_shipments, 0), f"Across {len(service[service.Shipments>0])} active services", "#45BD8C")
with k6:
    kpi_card("Top workload driver", top_service, f"{top_service_share:.1%} of total workload", "#FFC933")

section("MANAGEMENT READOUT", "What matters before drilling down")
read1, read2, read3 = st.columns(3, gap="small")
with read1:
    msg = f"{overload_count} office(s) are above 100% utilization." if office == "All Offices" else f"Selected scope is {status.lower()}."
    st.markdown(f"<div class='insight'><div class='insight-kicker'>Capacity risk</div><div class='insight-main'>{status}</div><div class='insight-text'>{msg}</div></div>", unsafe_allow_html=True)
with read2:
    st.markdown(f"<div class='insight'><div class='insight-kicker'>Primary workload driver</div><div class='insight-main'>{top_service}</div><div class='insight-text'>Accounts for {top_service_share:.1%} of total standard workload in the selected period.</div></div>", unsafe_allow_html=True)
with read3:
    exc_share = safe_divide(service.Exception.sum(), service.Total.sum())
    st.markdown(f"<div class='insight'><div class='insight-kicker'>Exception exposure</div><div class='insight-main'>{exc_share:.1%}</div><div class='insight-text'>Share of workload caused by exception handling; use this to prioritize process stabilization.</div></div>", unsafe_allow_html=True)

# ============================================================
# 10. TABS — Overview first, details later
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Executive Overview", "Capacity & HC", "Service Workload", "People & Customers", "Activity Detail"
])

with tab1:
    section("CAPACITY RISK MAP", "Status thresholds: >100% overload | >95–100% high | 90–95% balanced | <90% low")
    c1, c2 = st.columns([1.35, 1], gap="medium")
    with c1:
        if office_cap.empty:
            st.info("No headcount data for selected filters.")
        else:
            cap_plot = office_cap.sort_values("Utilization", ascending=True).copy()
            cap_plot["UtilPct"] = cap_plot.Utilization * 100
            fig = px.bar(cap_plot, x="UtilPct", y="Office", orientation="h", text="UtilPct", color="Status",
                         color_discrete_map=STATUS_COLORS, category_orders={"Status": ["Overload","High Load","Balanced","Low Load"]})
            fig.update_traces(texttemplate="%{text:.0f}%", textposition="outside", cliponaxis=False)
            fig.add_vline(x=100, line_dash="dash", line_color="#DC2626")
            fig.add_vline(x=95, line_dash="dot", line_color="#F97316")
            chart_style(fig, max(300, 74 + 52*len(cap_plot)))
            fig.update_layout(xaxis_title="Utilization (%)", legend_orientation="h", legend_y=-0.18)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with c2:
        show = office_cap.copy()
        if not show.empty:
            show["Utilization"] = show.Utilization * 100
            st.dataframe(show.sort_values("Utilization", ascending=False), hide_index=True, use_container_width=True,
                         column_config={
                             "Actual": st.column_config.NumberColumn("Actual HC", format="%.1f"),
                             "Required": st.column_config.NumberColumn("Required HC", format="%.1f"),
                             "Utilization": st.column_config.NumberColumn("Utilization", format="%.1f%%"),
                             "Gap": st.column_config.NumberColumn("HC Gap", format="%.1f"),
                         })

    section("WORKLOAD DRIVERS", "Where the time is consumed")
    d1, d2 = st.columns([1.45, 1], gap="medium")
    with d1:
        fig = px.bar(service, x="Segment", y="Hours", color="Segment", text="Hours", category_orders={"Segment": SERVICE_ORDER}, color_discrete_map=SERVICE_COLORS)
        fig.update_traces(texttemplate="%{text:,.0f}h", textposition="outside", cliponaxis=False)
        chart_style(fig, 350, legend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with d2:
        mix = service[service.Total > 0].copy()
        if mix.empty:
            st.info("No workload data.")
        else:
            fig = px.pie(mix, values="Total", names="Segment", hole=.63, color="Segment", color_discrete_map=SERVICE_COLORS)
            fig.update_traces(textposition="outside", textinfo="percent+label", hovertemplate="%{label}: %{value:,.0f} min (%{percent})<extra></extra>")
            chart_style(fig, 350)
            fig.add_annotation(text="Workload<br>Mix", x=.5, y=.5, showarrow=False, font=dict(size=16, color="#06183D"))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    section("MONTHLY TREND", "Only months with workload data are shown")
    trend = f_bu.groupby("Month", as_index=False).agg(Workload=("Total Workload","sum"), Shipments=("Core Volume","sum"))
    trend["Month"] = pd.Categorical(trend.Month, categories=MONTH_ORDER, ordered=True)
    trend = trend[trend.Workload > 0].sort_values("Month")
    if trend.empty:
        st.info("No monthly trend available.")
    else:
        trend["Hours"] = trend.Workload / 60
        fig = go.Figure()
        fig.add_trace(go.Bar(x=trend.Month.astype(str), y=trend.Hours, name="Workload (h)", marker_color="#06183D", text=trend.Hours.round(0), textposition="outside"))
        fig.add_trace(go.Scatter(x=trend.Month.astype(str), y=trend.Shipments, name="Shipment volume", mode="lines+markers", yaxis="y2", line=dict(color="#FF6D10", width=3)))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, title="Shipments"), yaxis_title="Workload hours")
        chart_style(fig, 360)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with tab2:
    section("HEADCOUNT POSITION", "Approved vs Actual vs Required")
    hc_view = f_hc.copy()
    if hc_view.empty:
        st.info("No HC data.")
    else:
        hagg = hc_view.groupby("Office", as_index=False).agg(
            Approved=("Total Approved HC","mean"), Actual=("Total Actual HC","mean"), Required=("Total Required HC","mean")
        )
        long = hagg.melt(id_vars="Office", var_name="HC Type", value_name="HC")
        fig = px.bar(long, x="Office", y="HC", color="HC Type", barmode="group", text="HC",
                     color_discrete_map={"Approved":"#94A3B8","Actual":"#00B9F2","Required":"#FF6D10"})
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        chart_style(fig, 380)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    section("WORKLOAD / FTE", "Index 1 from Ms. HH — priority productivity indicator")
    office_work = f_bu.groupby("Office", as_index=False).agg(Workload=("Total Workload","sum"))
    office_pic = f_hc.groupby("Office", as_index=False).agg(PIC=("Actual HC PIC","mean")) if not f_hc.empty else pd.DataFrame(columns=["Office","PIC"])
    index1 = office_work.merge(office_pic, on="Office", how="left")
    index1["Workload / PIC (min)"] = index1.apply(lambda r: safe_divide(r.Workload, r.PIC), axis=1)
    index1["Utilization vs 1 FTE"] = index1["Workload / PIC (min)"] / capacity_per_fte * months_count
    st.dataframe(index1, hide_index=True, use_container_width=True,
                 column_config={
                     "Workload": st.column_config.NumberColumn("Total workload (min)", format="%.0f"),
                     "PIC": st.column_config.NumberColumn("Actual PIC", format="%.1f"),
                     "Workload / PIC (min)": st.column_config.NumberColumn("Workload / PIC (min)", format="%.0f"),
                     "Utilization vs 1 FTE": st.column_config.NumberColumn("Workload / FTE", format="%.1f%%"),
                 })

with tab3:
    section("SERVICE WORKLOAD MATRIX", "Core + Ancillary + Supporting + Exception")
    matrix = service[["Segment","Service","Shipments","Core","Ancillary","Supporting","Exception","Total","Share","Required FTE"]].copy()
    matrix["Core"] /= 60; matrix["Ancillary"] /= 60; matrix["Supporting"] /= 60; matrix["Exception"] /= 60; matrix["Total"] /= 60
    st.dataframe(matrix, hide_index=True, use_container_width=True,
                 column_config={
                     "Shipments": st.column_config.NumberColumn("Shipment volume", format="%.0f"),
                     "Core": st.column_config.NumberColumn("Core (h)", format="%.1f"),
                     "Ancillary": st.column_config.NumberColumn("Ancillary (h)", format="%.1f"),
                     "Supporting": st.column_config.NumberColumn("Supporting (h)", format="%.1f"),
                     "Exception": st.column_config.NumberColumn("Exception (h)", format="%.1f"),
                     "Total": st.column_config.NumberColumn("Total workload (h)", format="%.1f"),
                     "Share": st.column_config.NumberColumn("Workload share", format="%.1f%%"),
                     "Required FTE": st.column_config.NumberColumn("Required FTE", format="%.2f"),
                 })

    section("ACTIVITY COMPOSITION BY SERVICE", "Expose non-core workload and exception burden")
    stack = service[["Segment","Core","Ancillary","Supporting","Exception"]].melt(id_vars="Segment", var_name="Activity", value_name="Minutes")
    stack["Hours"] = stack.Minutes / 60
    fig = px.bar(stack, x="Segment", y="Hours", color="Activity", barmode="stack", category_orders={"Segment": SERVICE_ORDER}, color_discrete_map=ACTIVITY_COLORS)
    chart_style(fig, 400)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    section("FTE ALLOCATION TO BUSINESS UNITS", "Required FTE derived from workload share")
    fte_mix = service.copy()
    fig = px.bar(fte_mix, x="Segment", y="Required FTE", color="Segment", text="Required FTE", category_orders={"Segment": SERVICE_ORDER}, color_discrete_map=SERVICE_COLORS)
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    chart_style(fig, 350, legend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with tab4:
    section("CS PIC FTE", "Use as staffing distribution; not actual individual workload unless source contains job-level workload")
    pics = f_cs.copy()
    if pics.empty:
        st.info("No CS PIC FTE data.")
    else:
        picagg = pics.groupby(["Office","CS PIC"], as_index=False).agg(FTE=("FTE","sum"))
        if month == "All":
            n = max(pics.Month.nunique(),1)
            picagg.FTE = picagg.FTE / n
        pic_top = picagg.sort_values("FTE", ascending=False).head(20)
        fig = px.bar(pic_top.sort_values("FTE"), x="FTE", y="CS PIC", orientation="h", color="Office", text="FTE")
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
        chart_style(fig, max(360, 26*len(pic_top)+90))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    section("CUSTOMER PORTFOLIO", "Customer filter affects this view only because customer-level workload is not available in source")
    if f_cust.empty:
        st.info("No customer volume data for selected filters.")
    else:
        cust = f_cust.groupby(["Office","Customer"], as_index=False).Volume.sum().sort_values("Volume", ascending=False)
        top = cust.head(15)
        c1, c2 = st.columns([1.5,1], gap="medium")
        with c1:
            fig = px.bar(top.sort_values("Volume"), x="Volume", y="Customer", orientation="h", text="Volume")
            fig.update_traces(marker_color="#00B9F2", texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
            chart_style(fig, max(340, 25*len(top)+80), legend=False)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with c2:
            st.dataframe(cust, hide_index=True, use_container_width=True,
                         column_config={"Volume": st.column_config.NumberColumn("Shipment volume", format="%.0f")})

with tab5:
    section("DETAIL VOLUME BY SERVICE CODE", "Core / Ancillary / Supporting; for audit and standard-time validation")
    detail_sets = [("Core", core_detail), ("Ancillary", ancillary_detail), ("Supporting", supporting_detail)]
    detail_tabs = st.tabs([x[0] for x in detail_sets])
    for t, (label, detail) in zip(detail_tabs, detail_sets):
        with t:
            d = detail.copy()
            if office != "All Offices":
                d = d[d.Office.eq(office)]
            if month != "All":
                d = d[d.Month.eq(month)]
            if d.empty:
                st.info(f"No {label.lower()} detail data.")
            else:
                summ = d.groupby(["Office","Scope"], as_index=False).Volume.sum().sort_values("Volume", ascending=False)
                top = summ.head(20)
                fig = px.bar(top.sort_values("Volume"), x="Volume", y="Scope", orientation="h", text="Volume")
                fig.update_traces(marker_color=ACTIVITY_COLORS[label], texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
                chart_style(fig, max(360, 24*len(top)+90), legend=False)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.dataframe(summ, hide_index=True, use_container_width=True)

# ============================================================
# 11. DATA GOVERNANCE NOTES
# ============================================================
st.markdown("---")
st.caption(
    "Method: Total Standard Time = Core Service + Ancillary Services + Supporting Activities + Exception Handling (if applicable). "
    "1 FTE = 8 hours/day × 95% productive efficiency × 22 working days = 10,032 minutes/month. "
    "Dashboard reads calculated Excel outputs; it does not overwrite standard-time logic."
)
