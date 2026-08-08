from pathlib import Path
import io
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# APP CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="OPERATIONS WORKLOAD & CAPACITY DASHBOARD",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "OPERATIONS WORKLOAD & CAPACITY DASHBOARD"
FTE_HOURS_PER_DAY = 8
EFFICIENCY = 0.95
WORKING_DAYS = 22
FTE_MINUTES = FTE_HOURS_PER_DAY * 60 * EFFICIENCY * WORKING_DAYS  # 10,032 min/month
MANAGER_FTE = 8
MANAGER_MINUTES = MANAGER_FTE * FTE_MINUTES                       # 80,256 min/month

SERVICE_ORDER = ["AI", "AE", "OI", "OE", "TR", "CC", "WH"]
SERVICE_LABELS = {
    "AI": "Air Import",
    "AE": "Air Export",
    "OI": "Ocean Import",
    "OE": "Ocean Export",
    "TR": "Trucking",
    "CC": "Customs Clearance",
    "WH": "Warehouse",
}

MONTH_ORDER = [
    "Apr", "May", "Jun", "Jul", "Aug", "Sep",
    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
]

# ============================================================
# STYLE
# ============================================================
st.markdown(
    """
    <style>
    :root {
        --navy:#083B82;
        --blue:#0B63CE;
        --orange:#ED6B21;
        --green:#169B62;
        --amber:#F59E0B;
        --red:#DC2626;
        --muted:#667085;
        --line:#DCE5F0;
        --panel:#FFFFFF;
        --page:#F7F9FC;
    }
    .stApp {background:var(--page);}
    [data-testid="stSidebar"] {
        background:linear-gradient(180deg,#073472 0%,#0B4D9B 100%);
        color:#FFFFFF;
    }

    /* Sidebar labels: Office / Month / CS PIC / Customer */
    section[data-testid="stSidebar"] label {
        color:#FFFFFF !important;
        font-weight:600 !important;
    }

    /* Filter box background + selected text */
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color:#FFFFFF !important;
        color:#172033 !important;
        border-radius:10px !important;
    }

    /* Selected value / text inside Selectbox */
    section[data-testid="stSidebar"] div[data-baseweb="select"] span {
        color:#172033 !important;
    }

    /* Input text */
    section[data-testid="stSidebar"] div[data-baseweb="select"] input {
        color:#172033 !important;
        -webkit-text-fill-color:#172033 !important;
    }

    /* Placeholder */
    section[data-testid="stSidebar"] div[data-baseweb="select"] input::placeholder {
        color:#667085 !important;
        opacity:1 !important;
    }

    /* Dropdown menu opened from Selectbox */
    div[data-baseweb="popover"] ul,
    div[data-baseweb="menu"] {
        background:#FFFFFF !important;
    }

    div[data-baseweb="popover"] li,
    div[data-baseweb="menu"] li {
        color:#172033 !important;
    }

    /* Arrow / icons inside filter */
    section[data-testid="stSidebar"] div[data-baseweb="select"] svg {
        fill:#667085 !important;
        color:#667085 !important;
    }

    .block-container {max-width:1650px;padding-top:3.5rem;padding-bottom:2rem;}
    .dashboard-title {
        font-size:1.85rem;font-weight:850;color:var(--navy);
        margin-bottom:0.2rem;letter-spacing:-0.02em;
    }
    .dashboard-subtitle {color:var(--muted);font-size:0.82rem;margin-bottom:0.9rem;}
    .section-title {
        background:var(--navy);color:#FFFFFF;padding:0.55rem 0.8rem;
        border-radius:10px 10px 0 0;font-weight:800;margin-top:0.25rem;
    }
    .kpi-card {
        background:#FFFFFF;border:1px solid var(--line);border-radius:12px;
        min-height:132px;display:flex;flex-direction:column;align-items:center;
        justify-content:center;box-shadow:0 2px 10px rgba(28,54,89,.05);
        text-align:center;padding:8px 10px;box-sizing:border-box;
    }
    .kpi-label {font-size:0.80rem;color:var(--navy);font-weight:800;margin-bottom:9px;}
    .kpi-value {font-size:2.05rem;font-weight:850;color:var(--blue);line-height:1;}
    .kpi-note {font-size:0.70rem;color:var(--muted);margin-top:8px;line-height:1.25;}
    .orange .kpi-value {color:var(--orange);}
    .green .kpi-value {color:var(--green);}
    .amber .kpi-value {color:var(--amber);}
    .red .kpi-value {color:var(--red);}
    div[data-testid="stDataFrame"] {border:1px solid var(--line);border-radius:10px;overflow:hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# HELPERS
# ============================================================
def clean_text(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_month(value):
    """Convert Excel/text month headers such as Apr, Apr-26, or Excel dates to Apr."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""

    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%b")

    # Python datetime/date values
    if hasattr(value, "strftime") and not isinstance(value, str):
        try:
            return value.strftime("%b")
        except Exception:
            pass

    s = clean_text(value)
    if not s:
        return ""

    # Try datetime parsing first for values like 2026-08-01 / 01-Aug-2026
    try:
        dt = pd.to_datetime(s, errors="raise")
        return dt.strftime("%b")
    except Exception:
        pass

    # Fallback for text such as Apr-26, Apr, APR
    abbr = s[:3].title()
    return abbr if abbr in MONTH_ORDER else ""


def safe_num(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


def safe_divide(a, b):
    if b is None or pd.isna(b) or float(b) == 0:
        return 0.0
    return float(a) / float(b)


def fmt_hours(minutes):
    return f"{minutes / 60:,.1f} h"


def fmt_fte(minutes):
    return f"{safe_divide(minutes, FTE_MINUTES):,.2f}"


def kpi_card(label, value, note="", accent=""):
    st.markdown(
        f"""
        <div class="kpi-card {accent}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def standard_chart_layout(fig, height=350):
    fig.update_layout(
        height=height,
        margin=dict(l=15, r=15, t=35, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#172033"),
        legend_title_text="",
        xaxis_title="",
        yaxis_title="",
        hoverlabel=dict(bgcolor="white"),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E9EEF5")
    return fig


@st.cache_data(show_spinner=False)
def load_excel(file_bytes: bytes):
    return pd.ExcelFile(io.BytesIO(file_bytes))


def read_source_file():
    app_dir = Path(__file__).resolve().parent
    xlsx_files = [
        p for p in app_dir.rglob("*.xlsx")
        if not p.name.startswith("~$")
    ]

    required = {"HC", "BU allocation", "Shipment volume", "CS FTE"}

    for p in sorted(xlsx_files, key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            xl = pd.ExcelFile(p)
            sheet_names = set(xl.sheet_names)
            has_customer = any(s.startswith("Customer Volume") for s in xl.sheet_names)

            if required.issubset(sheet_names) and has_customer:
                return p.read_bytes(), p.name
        except Exception:
            continue

    st.error(
        "Không tìm thấy file Excel có đủ các sheet chính: "
        "HC, BU allocation, Shipment volume, CS FTE và Customer Volume."
    )
    st.info("Đặt file Excel cùng thư mục/repository với file .py rồi Reboot app.")
    st.stop()


@st.cache_data(show_spinner=False)
def parse_bu_allocation(file_bytes: bytes) -> pd.DataFrame:
    """
    Read the standardized BU allocation sheet.
    Row 1 = title, Row 2 = one-line header, Row 3 onward = data.
    """
    df = pd.read_excel(
        io.BytesIO(file_bytes),
        sheet_name="BU allocation",
        header=1,
        usecols="A:M",
    )

    expected = [
        "Office", "Month", "Segment",
        "Core Volume", "Core Workload (min)",
        "Ancillary Volume", "Ancillary Workload (min)",
        "Supporting Volume", "Supporting Workload (min)",
        "Exception Volume", "Exception Workload (min)",
        "Total Workload (min)", "% of Network",
    ]

    if df.shape[1] < 13:
        raise ValueError("Sheet 'BU allocation' không đủ 13 cột dữ liệu.")

    # Use positional mapping so minor wording/spacing changes do not break the app.
    df = df.iloc[:, :13].copy()
    df.columns = [
        "Office", "Month", "Segment",
        "Core Volume", "Core Workload",
        "Ancillary Volume", "Ancillary Workload",
        "Supporting Volume", "Supporting Workload",
        "Exception Volume", "Exception Workload",
        "Total Workload", "Network Share",
    ]

    for c in ["Office", "Segment"]:
        df[c] = df[c].map(clean_text)

    df["Month"] = df["Month"].map(normalize_month)

    numeric_cols = [
        "Core Volume", "Core Workload",
        "Ancillary Volume", "Ancillary Workload",
        "Supporting Volume", "Supporting Workload",
        "Exception Volume", "Exception Workload",
        "Total Workload", "Network Share",
    ]

    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df[
        df["Office"].ne("")
        & df["Month"].isin(MONTH_ORDER)
        & df["Segment"].isin(SERVICE_ORDER)
    ].copy()

    df["Total Workload"] = df["Total Workload"].fillna(0)
    df["Core Volume"] = df["Core Volume"].fillna(0)
    df["Month"] = pd.Categorical(df["Month"], categories=MONTH_ORDER, ordered=True)

    return df.sort_values(["Month", "Office", "Segment"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def parse_cs_fte(file_bytes: bytes) -> pd.DataFrame:
    """
    Read CS FTE sheet:
    Row 1 = title, Row 2 = Office / CS PIC / Apr-26 ... Mar-27.
    """
    df = pd.read_excel(
        io.BytesIO(file_bytes),
        sheet_name="CS FTE",
        header=1,
    )

    if df.shape[1] < 3:
        return pd.DataFrame(columns=["Office", "CS PIC", "Month", "FTE", "PIC Workload"])

    office_col = df.columns[0]
    pic_col = df.columns[1]

    records = []
    for _, row in df.iterrows():
        office = clean_text(row.get(office_col))
        pic = clean_text(row.get(pic_col))

        if not office or not pic:
            continue

        for col in df.columns[2:]:
            month = normalize_month(col)
            if month not in MONTH_ORDER:
                continue

            value = pd.to_numeric(pd.Series([row.get(col)]), errors="coerce").iloc[0]
            if pd.isna(value):
                continue

            records.append({
                "Office": office,
                "CS PIC": pic,
                "Month": month,
                "FTE": float(value),
                "PIC Workload": float(value) * FTE_MINUTES,
            })

    return pd.DataFrame(records)


@st.cache_data(show_spinner=False)
def parse_customer_lists(file_bytes: bytes) -> pd.DataFrame:
    """
    Combine Customer Volume sheets into Office / Customer / Month / Shipment Volume.

    Dedicated sheets (Customer Volume - HAD/HAN/HLC/HCM) are preferred.
    Customer Volume-N&S is used only as a fallback for records not already
    available in the dedicated office sheets, preventing double counting.
    """
    xl = pd.ExcelFile(io.BytesIO(file_bytes))
    candidate_sheets = [s for s in xl.sheet_names if s.startswith("Customer Volume")]

    all_records = []

    for sheet in candidate_sheets:
        df = pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=sheet,
            header=1,
        )

        if df.shape[1] < 4:
            continue

        # Standardized customer sheets:
        # No. | Office | Customer | Apr-26 ... Mar-27 | Total
        office_col = df.columns[1]
        customer_col = df.columns[2]

        # Dedicated office sheets should win over N&S if the same record exists.
        source_priority = 1 if sheet.strip() == "Customer Volume-N&S" else 0

        for _, row in df.iterrows():
            office = clean_text(row.get(office_col))
            customer_name = clean_text(row.get(customer_col))

            if not office or not customer_name:
                continue

            for col in df.columns[3:]:
                if clean_text(col).casefold() == "total":
                    continue

                month = normalize_month(col)
                if month not in MONTH_ORDER:
                    continue

                value = pd.to_numeric(pd.Series([row.get(col)]), errors="coerce").iloc[0]
                if pd.isna(value):
                    continue

                all_records.append({
                    "Office": office,
                    "Customer": customer_name,
                    "Month": month,
                    "Customer Shipment Volume": float(value),
                    "_priority": source_priority,
                    "_sheet": sheet,
                })

    if not all_records:
        return pd.DataFrame(
            columns=["Office", "Customer", "Month", "Customer Shipment Volume"]
        )

    out = pd.DataFrame(all_records)
    out = out.sort_values("_priority")

    # Prefer the dedicated Office sheet over N&S duplicates.
    out = out.drop_duplicates(
        subset=["Office", "Customer", "Month"],
        keep="first",
    )

    return out[
        ["Office", "Customer", "Month", "Customer Shipment Volume"]
    ].reset_index(drop=True)


# ============================================================
# LOAD DATA
# ============================================================
try:
    source_bytes, source_name = read_source_file()
    bu = parse_bu_allocation(source_bytes)
    cs_fte = parse_cs_fte(source_bytes)
    customer = parse_customer_lists(source_bytes)
except Exception as exc:
    st.error("Không thể đọc dữ liệu nguồn.")
    st.exception(exc)
    st.stop()

# ============================================================
# SIDEBAR FILTERS
# ============================================================
st.sidebar.markdown("## 📊 CS Division")
st.sidebar.markdown(
    "<div style='color:#D8E5F8;font-size:14px;margin-top:-8px;margin-bottom:14px;'>FTE & Capacity Dashboard</div>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

def reset_child_filters():
    """Reset dependent filters when Office or Month changes."""
    st.session_state["filter_cs_pic"] = "All CS PIC"
    st.session_state["filter_customer"] = "All Customers"


all_offices = sorted(
    set(bu["Office"].dropna().astype(str))
    | set(cs_fte.get("Office", pd.Series(dtype=str)).dropna().astype(str))
    | set(customer.get("Office", pd.Series(dtype=str)).dropna().astype(str))
)

office = st.sidebar.selectbox(
    "Office",
    ["All Offices"] + all_offices,
    key="filter_office",
    on_change=reset_child_filters,
)

# Month options only from populated BU rows; keep FY order.
# Add "All" so the dashboard can show the full available period.
available_months = [m for m in MONTH_ORDER if m in set(bu["Month"].astype(str))]
month_options = ["All"] + available_months

month = st.sidebar.selectbox(
    "Month",
    month_options,
    index=0,
    key="filter_month",
    on_change=reset_child_filters,
)

# Number of months currently included in the calculation.
# This is important because Manager FTE and FTE capacity are monthly values.
selected_month_count = len(available_months) if month == "All" else 1
selected_month_count = max(selected_month_count, 1)

# CS PIC scope
if cs_fte.empty:
    pic_scope = cs_fte.copy()
elif month == "All":
    pic_scope = cs_fte.copy()
else:
    pic_scope = cs_fte[cs_fte["Month"].eq(month)].copy()

if office != "All Offices" and not pic_scope.empty:
    pic_scope = pic_scope[pic_scope["Office"].eq(office)]

pic_options = sorted(
    pic_scope["CS PIC"].dropna().unique().tolist()
) if not pic_scope.empty else []
pic_select_options = ["All CS PIC"] + pic_options

# If the previous CS PIC is no longer valid after changing Office/Month,
# force it back to All CS PIC before rendering the widget.
if (
    "filter_cs_pic" in st.session_state
    and st.session_state["filter_cs_pic"] not in pic_select_options
):
    st.session_state["filter_cs_pic"] = "All CS PIC"

cs_pic = st.sidebar.selectbox(
    "CS PIC",
    pic_select_options,
    key="filter_cs_pic",
)

# Customer scope
if customer.empty:
    cust_scope = customer.copy()
elif month == "All":
    cust_scope = customer.copy()
else:
    cust_scope = customer[customer["Month"].eq(month)].copy()

if office != "All Offices" and not cust_scope.empty:
    cust_scope = cust_scope[cust_scope["Office"].eq(office)]

customer_options = sorted(
    cust_scope["Customer"].dropna().unique().tolist()
) if not cust_scope.empty else []
customer_select_options = ["All Customers"] + customer_options

# Keep Customer selection synchronized with the currently available list.
if (
    "filter_customer" in st.session_state
    and st.session_state["filter_customer"] not in customer_select_options
):
    st.session_state["filter_customer"] = "All Customers"

selected_customer = st.sidebar.selectbox(
    "Customer",
    customer_select_options,
    key="filter_customer",
)

st.sidebar.markdown("---")
# ============================================================
# FILTER / CALCULATION MODEL
# ============================================================
if month == "All":
    base_bu_month = bu.copy()
else:
    base_bu_month = bu[bu["Month"].astype(str).eq(month)].copy()

filtered_bu = base_bu_month.copy()
if office != "All Offices":
    filtered_bu = filtered_bu[filtered_bu["Office"].eq(office)].copy()

# Customer filter is informational because current workbook does not map customer to segment workload.
filtered_customer = cust_scope.copy()
if selected_customer != "All Customers" and not filtered_customer.empty:
    filtered_customer = filtered_customer[filtered_customer["Customer"].eq(selected_customer)]

# Office / network base workload before manager allocation.
network_base_workload = float(base_bu_month["Total Workload"].sum())
selected_base_workload = float(filtered_bu["Total Workload"].sum())

# Allocate 8 managers per month to offices by each office's share of network workload.
# When Month = All, the manager pool is multiplied by the number of selected months.
manager_pool_minutes = MANAGER_MINUTES * selected_month_count

if office == "All Offices":
    selected_manager_minutes = manager_pool_minutes
else:
    office_share = safe_divide(selected_base_workload, network_base_workload)
    selected_manager_minutes = manager_pool_minutes * office_share

# PIC selection: use CS FTE as the source of total PIC workload; service split is allocated by office service mix.
pic_workload_minutes = None
pic_fte_value = None
pic_share = None
if cs_pic != "All CS PIC" and not pic_scope.empty:
    selected_pic_rows = pic_scope[pic_scope["CS PIC"].eq(cs_pic)]
    pic_fte_value = float(selected_pic_rows["FTE"].sum())
    pic_workload_minutes = float(selected_pic_rows["PIC Workload"].sum())
    office_pic_total = float(pic_scope["PIC Workload"].sum())
    pic_share = safe_divide(pic_workload_minutes, office_pic_total)

    # Allocate office service workload to selected PIC by PIC workload share.
    filtered_bu["Total Workload"] = filtered_bu["Total Workload"] * pic_share
    filtered_bu["Core Volume"] = filtered_bu["Core Volume"] * pic_share
    selected_base_workload = float(filtered_bu["Total Workload"].sum())
    selected_manager_minutes = selected_manager_minutes * pic_share

# Aggregate selected service data.
service = (
    filtered_bu.groupby("Segment", as_index=False)
    .agg(
        Shipment_Volume=("Core Volume", "sum"),
        Base_Workload=("Total Workload", "sum"),
    )
)
service = pd.DataFrame({"Segment": SERVICE_ORDER}).merge(service, on="Segment", how="left").fillna(0)
service["Service Share"] = np.where(
    service["Base_Workload"].sum() > 0,
    service["Base_Workload"] / service["Base_Workload"].sum(),
    0,
)
service["Manager Allocated"] = service["Service Share"] * selected_manager_minutes
service["Adjusted Workload"] = service["Base_Workload"] + service["Manager Allocated"]
service["Adjusted FTE"] = 0.0
service["Service"] = service["Segment"].map(SERVICE_LABELS)

adjusted_total_workload = float(service["Adjusted Workload"].sum())

# Required FTE is shown as average monthly FTE for the selected period.
period_capacity_minutes = FTE_MINUTES * selected_month_count
required_fte = safe_divide(adjusted_total_workload, period_capacity_minutes)
service["Adjusted FTE"] = service["Adjusted Workload"] / period_capacity_minutes

total_shipments = float(service["Shipment_Volume"].sum())

# Manager FTE is also shown as average monthly FTE for the selected period.
manager_fte_selected = safe_divide(selected_manager_minutes, period_capacity_minutes)

# ============================================================
# HEADER / DATA NOTE
# ============================================================
st.markdown(f'<div class="dashboard-title">{APP_TITLE}</div>', unsafe_allow_html=True)

# Display exactly the values currently selected in the sidebar filters.
filter_summary = (
    f"Month: {st.session_state.get('filter_month', month)}"
    f" · Office: {st.session_state.get('filter_office', office)}"
    f" · CS PIC: {st.session_state.get('filter_cs_pic', cs_pic)}"
    f" · Customer: {st.session_state.get('filter_customer', selected_customer)}"
)

st.markdown(
    f'<div class="dashboard-subtitle">{filter_summary}</div>',
    unsafe_allow_html=True,
)

if selected_customer != "All Customers":
    st.info(
        "Customer filter hiện chỉ lọc phần Customer Volume. File nguồn chưa có mapping Customer → Service Segment → CS PIC, "
        "nên workload/FTE không được giảm theo Customer để tránh phân bổ sai dữ liệu."
    )

# ============================================================
# KPI ROW
# ============================================================
k1, k2, k3, k4, k5 = st.columns(5, gap="small")
with k1:
    kpi_card("Shipment Volume", f"{total_shipments:,.0f}", "Core volume across AI/AE/OI/OE/TR/CC/WH")
with k2:
    kpi_card("Base Workload", fmt_hours(selected_base_workload), "Before manager allocation")
with k3:
    kpi_card("Manager Allocation", fmt_hours(selected_manager_minutes), f"Equivalent to {manager_fte_selected:.2f} manager FTE", "orange")
with k4:
    kpi_card("Adjusted Workload", fmt_hours(adjusted_total_workload), "Base workload + allocated manager time", "green")
with k5:
    kpi_card("Required FTE", f"{required_fte:.2f}", f"Average monthly FTE · 1 FTE = {FTE_MINUTES/60:.1f} productive hours/month", "amber")

# ============================================================
# SERVICE VOLUME + SERVICE WORKLOAD
# ============================================================
st.markdown("<br>", unsafe_allow_html=True)
left, right = st.columns([1.05, 1.25], gap="medium")

with left:
    st.markdown('<div class="section-title">SHIPMENT VOLUME BY SERVICE</div>', unsafe_allow_html=True)
    volume_plot = service.copy()
    volume_plot["Display"] = volume_plot["Segment"]
    fig = px.bar(
        volume_plot,
        x="Display",
        y="Shipment_Volume",
        text="Shipment_Volume",
        category_orders={"Display": SERVICE_ORDER},
    )
    fig.update_traces(marker_color="#0B63CE", texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
    standard_chart_layout(fig, 340)
    fig.update_yaxes(rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with right:
    st.markdown('<div class="section-title">WORKLOAD & MANAGER ALLOCATION BY SERVICE</div>', unsafe_allow_html=True)
    workload_long = service.melt(
        id_vars=["Segment"],
        value_vars=["Base_Workload", "Manager Allocated"],
        var_name="Workload Type",
        value_name="Minutes",
    )

    # Rename only for display in the chart legend
    workload_long["Workload Type"] = workload_long["Workload Type"].replace({
        "Base_Workload": "Base Workload"
    })

    workload_long["Hours"] = workload_long["Minutes"] / 60
    fig = px.bar(
        workload_long,
        x="Segment",
        y="Hours",
        color="Workload Type",
        barmode="stack",
        category_orders={"Segment": SERVICE_ORDER},
        color_discrete_map={
            "Base Workload": "#0B63CE",
            "Manager Allocated": "#ED6B21",
        },
    )
    standard_chart_layout(fig, 340)
    fig.update_yaxes(title_text="Hours")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ============================================================
# OFFICE / PIC WORKLOAD + SERVICE SHARE
# ============================================================
st.markdown("<br>", unsafe_allow_html=True)
left, right = st.columns([1.2, 1], gap="medium")

with left:
    title = "WORKLOAD BY OFFICE" if cs_pic == "All CS PIC" else "SELECTED CS PIC WORKLOAD"
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

    if cs_pic == "All CS PIC":
        office_workload = (
            base_bu_month.groupby("Office", as_index=False)["Total Workload"].sum()
            .rename(columns={"Total Workload": "Base Workload"})
        )
        office_workload["Network Share"] = np.where(
            office_workload["Base Workload"].sum() > 0,
            office_workload["Base Workload"] / office_workload["Base Workload"].sum(),
            0,
        )
        office_workload["Manager Allocated"] = office_workload["Network Share"] * manager_pool_minutes
        office_workload["Adjusted Workload"] = office_workload["Base Workload"] + office_workload["Manager Allocated"]
        office_workload["Hours"] = office_workload["Adjusted Workload"] / 60
        office_workload = office_workload.sort_values("Hours", ascending=True)
        fig = px.bar(office_workload, x="Hours", y="Office", orientation="h", text="Hours")
        fig.update_traces(marker_color="#0B63CE", texttemplate="%{text:.1f}h", textposition="outside", cliponaxis=False)
        standard_chart_layout(fig, 340)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        pic_display = pic_scope[pic_scope["CS PIC"].eq(cs_pic)].copy()

        if office != "All Offices":
            pic_display = pic_display[pic_display["Office"].eq(office)]

        if month == "All" and not pic_display.empty:
            pic_display = (
                pic_display.groupby(["Office", "CS PIC"], as_index=False)
                .agg(**{"PIC Workload": ("PIC Workload", "mean")})
            )

        pic_display["Hours"] = pic_display["PIC Workload"] / 60
        pic_display = pic_display.sort_values("Hours", ascending=True)

        fig = px.bar(
            pic_display,
            x="Hours",
            y="CS PIC",
            orientation="h",
            text="Hours",
        )
        fig.update_traces(
            marker_color="#169B62",
            texttemplate="%{text:.1f}h",
            textposition="outside",
            cliponaxis=False,
        )
        standard_chart_layout(fig, 340)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with right:
    st.markdown('<div class="section-title">SERVICE SHARE OF TOTAL TIME</div>', unsafe_allow_html=True)
    pie = service[service["Adjusted Workload"] > 0].copy()
    if pie.empty:
        st.info("No workload data available for selected filters.")
    else:
        fig = px.pie(
            pie,
            names="Segment",
            values="Adjusted Workload",
            hole=0.58,
            category_orders={"Segment": SERVICE_ORDER},
        )
        fig.update_traces(textposition="inside", textinfo="label+percent")
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=20), paper_bgcolor="white", showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ============================================================
# CS PIC FTE TABLE / CUSTOMER VOLUME
# ============================================================
st.markdown("<br>", unsafe_allow_html=True)
left, right = st.columns([1.25, 1], gap="medium")

with left:
    st.markdown('<div class="section-title">CS PIC FTE & WORKLOAD</div>', unsafe_allow_html=True)
    if month == "All":
        pic_table = cs_fte.copy()
    else:
        pic_table = cs_fte[cs_fte["Month"].eq(month)].copy()

    if office != "All Offices":
        pic_table = pic_table[pic_table["Office"].eq(office)]
    if cs_pic != "All CS PIC":
        pic_table = pic_table[pic_table["CS PIC"].eq(cs_pic)]

    # For Month = All, show average monthly FTE and average monthly workload
    # instead of summing FTE across months.
    if month == "All" and not pic_table.empty:
        pic_table = (
            pic_table.groupby(["Office", "CS PIC"], as_index=False)
            .agg(
                FTE=("FTE", "mean"),
                **{"PIC Workload": ("PIC Workload", "mean")},
            )
        )

    if pic_table.empty:
        st.info("No CS PIC FTE data available for selected filters.")
    else:
        pic_table["Workload Hours"] = pic_table["PIC Workload"] / 60
        pic_table["Capacity Status"] = np.select(
            [pic_table["FTE"] > 1.05, pic_table["FTE"] >= 0.95],
            ["Overload", "Near Full"],
            default="Available",
        )
        st.dataframe(
            pic_table[["Office", "CS PIC", "FTE", "Workload Hours", "Capacity Status"]]
            .sort_values(["Office", "FTE"], ascending=[True, False]),
            hide_index=True,
            use_container_width=True,
            height=335,
            column_config={
                "FTE": st.column_config.NumberColumn("Required FTE", format="%.2f"),
                "Workload Hours": st.column_config.NumberColumn("Workload Hours", format="%.1f h"),
            },
        )

with right:
    st.markdown('<div class="section-title">CUSTOMER SHIPMENT VOLUME</div>', unsafe_allow_html=True)
    cust_plot = filtered_customer.copy()
    if cust_plot.empty:
        st.info("No customer volume data available for selected filters.")
    else:
        cust_plot = (
            cust_plot.groupby(["Office", "Customer"], as_index=False)["Customer Shipment Volume"].sum()
            .sort_values("Customer Shipment Volume", ascending=False)
            .head(15)
        )
        fig = px.bar(
            cust_plot.sort_values("Customer Shipment Volume"),
            x="Customer Shipment Volume",
            y="Customer",
            orientation="h",
            text="Customer Shipment Volume",
        )
        fig.update_traces(marker_color="#0B63CE", texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
        standard_chart_layout(fig, 335)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ============================================================
# DETAIL TABLE
# ============================================================
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-title">SERVICE WORKLOAD DETAIL</div>', unsafe_allow_html=True)
service_table = service[[
    "Segment", "Service", "Shipment_Volume", "Base_Workload",
    "Service Share", "Manager Allocated", "Adjusted Workload", "Adjusted FTE",
]].copy()
service_table["Base Workload (h)"] = service_table["Base_Workload"] / 60
service_table["Manager Allocation (h)"] = service_table["Manager Allocated"] / 60
service_table["Adjusted Workload (h)"] = service_table["Adjusted Workload"] / 60
service_table = service_table[[
    "Segment", "Service", "Shipment_Volume", "Base Workload (h)",
    "Service Share", "Manager Allocation (h)", "Adjusted Workload (h)", "Adjusted FTE",
]]
st.dataframe(
    service_table,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Shipment_Volume": st.column_config.NumberColumn("Shipment Volume", format="%.0f"),
        "Base Workload (h)": st.column_config.NumberColumn("Base Workload (h)", format="%.1f"),
        "Service Share": st.column_config.NumberColumn("% of Total Time", format="%.1f%%"),
        "Manager Allocation (h)": st.column_config.NumberColumn("Manager Allocation (h)", format="%.1f"),
        "Adjusted Workload (h)": st.column_config.NumberColumn("Adjusted Workload (h)", format="%.1f"),
        "Adjusted FTE": st.column_config.NumberColumn("Required FTE", format="%.2f"),
    },
)
