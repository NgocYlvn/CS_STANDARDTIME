
# ============================================================
# EXECUTIVE WORKLOAD & CAPACITY DASHBOARD
# Dữ liệu nguồn: workbook Template data for Dashboard
# Công nghệ: Streamlit + Pandas + Plotly
# ============================================================

import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# 1. PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Executive Workload & Capacity Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Màu sắc dashboard
NAVY = "#083B82"
BLUE = "#0B63CE"
ORANGE = "#ED6B21"
GREEN = "#169B62"
AMBER = "#F59E0B"
RED = "#DC2626"
PURPLE = "#8B5CF6"
LIGHT_BLUE = "#6CB6FF"
BG = "#F7F9FC"
PANEL = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"

FISCAL_MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep",
                 "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
MONTH_ORDER = {m: i + 1 for i, m in enumerate(FISCAL_MONTHS)}

STATUS_ORDER = ["Less load", "Balanced", "High load", "Overload"]
STATUS_COLOR = {
    "Less load": GREEN,
    "Balanced": BLUE,
    "High load": AMBER,
    "Overload": RED,
}

BU_ORDER = ["AE", "AI", "OE", "OI", "CC", "TR", "WH"]

# Transportation mode columns nằm trong sheet Shipment volume.
# App sẽ tự dùng các cột D:S nếu không nhận diện được bằng tên.
KNOWN_MODE_KEYWORDS = [
    "AE", "AI", "OE", "OI", "AIR", "OCEAN", "SEA", "FCL", "LCL",
    "TRUCK", "TRUCKING", "CC", "CUSTOM", "WH", "WAREHOUSE", "RAIL"
]


# ============================================================
# 2. CSS
# ============================================================
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {BG};
    }}

    .block-container {{
        padding-top: 1.25rem;
        padding-bottom: 2rem;
        max-width: 1600px;
    }}

    [data-testid="stSidebar"] {{
        background: {NAVY};
    }}

    [data-testid="stSidebar"] * {{
        color: white;
    }}

    [data-testid="stSidebar"] label {{
        color: white !important;
    }}

    .dashboard-title {{
        font-size: 30px;
        font-weight: 800;
        color: {NAVY};
        margin-bottom: 2px;
        line-height: 1.15;
    }}

    .dashboard-subtitle {{
        font-size: 13px;
        color: {MUTED};
        margin-bottom: 16px;
    }}

    .section-title {{
        color: {NAVY};
        font-size: 19px;
        font-weight: 750;
        margin: 18px 0 8px 0;
        padding-bottom: 6px;
        border-bottom: 2px solid {ORANGE};
    }}

    .kpi-card {{
        background: {PANEL};
        border: 1px solid #E5E7EB;
        border-radius: 14px;
        padding: 16px 18px;
        min-height: 122px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}

    .kpi-label {{
        font-size: 12px;
        color: {MUTED};
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: .35px;
    }}

    .kpi-value {{
        font-size: 29px;
        color: {NAVY};
        font-weight: 800;
        margin-top: 7px;
        line-height: 1.05;
    }}

    .kpi-note {{
        font-size: 11px;
        color: {MUTED};
        margin-top: 8px;
    }}

    .info-box {{
        background: white;
        border: 1px solid #E5E7EB;
        border-left: 4px solid {ORANGE};
        border-radius: 10px;
        padding: 11px 14px;
        margin: 4px 0 12px 0;
        color: {TEXT};
        font-size: 13px;
    }}

    .warning-box {{
        background: #FFF7ED;
        border: 1px solid #FED7AA;
        border-left: 4px solid {ORANGE};
        border-radius: 10px;
        padding: 11px 14px;
        margin: 4px 0 12px 0;
        color: #7C2D12;
        font-size: 13px;
    }}

    div[data-testid="stPlotlyChart"] {{
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 14px;
        padding: 4px;
    }}

    .footer {{
        color: {MUTED};
        font-size: 11px;
        text-align: center;
        margin-top: 24px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. HELPERS
# ============================================================
def clean_text(value):
    """Chuẩn hóa một giá trị về text; an toàn khi vô tình nhận Series/list."""
    if isinstance(value, pd.Series):
        non_null = value.dropna()
        value = non_null.iloc[0] if not non_null.empty else None
    elif isinstance(value, (list, tuple, np.ndarray)):
        values = [v for v in value if not pd.isna(v)]
        value = values[0] if values else None

    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def normalize_month(value):
    """Chuẩn hóa Month về Apr, May, ..."""
    if pd.isna(value):
        return None
    text = str(value).strip()
    # Trường hợp Apr-26 / Apr 26 / datetime-like text
    if len(text) >= 3:
        month = text[:3].title()
        if month in MONTH_ORDER:
            return month
    return None


def month_label(month):
    """FY2026: Apr-Dec = 2026, Jan-Mar = 2027"""
    if month not in MONTH_ORDER:
        return str(month)
    year = 2026 if month in ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"] else 2027
    return f"{month}-{str(year)[-2:]}"


def fig_layout(fig, title=None, height=360, showlegend=True):
    fig.update_layout(
        title=dict(text=title or "", x=0.02, xanchor="left"),
        height=height,
        margin=dict(l=25, r=20, t=55, b=30),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color=TEXT, size=12),
        showlegend=showlegend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#EEF2F7", zeroline=False)
    return fig


def kpi_card(label, value, note=""):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def no_data(message="No data for selected filters."):
    st.info(message)


def find_header_row(raw_df, required_words, max_rows=8):
    """
    Tìm dòng header dựa trên số keyword xuất hiện nhiều nhất.
    raw_df được đọc với header=None.
    """
    best_idx, best_score = None, -1
    for idx in range(min(max_rows, len(raw_df))):
        values = " | ".join(clean_text(v).lower() for v in raw_df.iloc[idx].tolist())
        score = sum(1 for w in required_words if w.lower() in values)
        if score > best_score:
            best_idx, best_score = idx, score
    return best_idx


def build_multilevel_columns(raw, header_rows):
    """
    Ghép merged/multi-level header thành tên cột duy nhất.
    Forward-fill từng header row theo chiều ngang.
    """
    parts = []
    for r in header_rows:
        row = pd.Series(raw.iloc[r].tolist()).ffill()
        parts.append(row)

    cols = []
    for c in range(raw.shape[1]):
        labels = []
        for row in parts:
            text = clean_text(row.iloc[c])
            if text and text.lower() != "nan":
                if not labels or text != labels[-1]:
                    labels.append(text)
        name = " | ".join(labels).strip(" |")
        cols.append(name if name else f"Column_{c+1}")
    return cols


def fuzzy_col(columns, includes=None, excludes=None):
    includes = [x.lower() for x in (includes or [])]
    excludes = [x.lower() for x in (excludes or [])]
    for col in columns:
        low = str(col).lower()
        if all(x in low for x in includes) and not any(x in low for x in excludes):
            return col
    return None


# ============================================================
# 4. DATA LOADERS
# ============================================================
@st.cache_data(show_spinner=False)
def read_sheet(file_bytes, sheet_name):
    return pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=None, engine="openpyxl")


@st.cache_data(show_spinner=False)
def get_sheet_names(file_bytes):
    xls = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    return xls.sheet_names


@st.cache_data(show_spinner=False)
def load_hc(file_bytes):
    raw = read_sheet(file_bytes, "HC")
    # Workbook hiện tại: 3 dòng header, data bắt đầu dòng 4.
    columns = build_multilevel_columns(raw, [1, 2])
    df = raw.iloc[3:].copy()
    df.columns = columns
    df = df.dropna(how="all").reset_index(drop=True)

    office_col = fuzzy_col(df.columns, ["office"])
    month_col = fuzzy_col(df.columns, ["month"])

    # Xác định cột Total của Approved / Actual / Required
    approved_total = fuzzy_col(df.columns, ["approved", "total"])
    actual_total = fuzzy_col(df.columns, ["actual", "total"])
    required_total = fuzzy_col(df.columns, ["required", "total"])
    capacity_pct = fuzzy_col(df.columns, ["capacity", "%"])
    status_col = fuzzy_col(df.columns, ["capacity", "status"]) or fuzzy_col(df.columns, ["status"])

    # Fallback theo vị trí đã phân tích: Office=A, Month=B, E/H/K/L/M
    if office_col is None and len(df.columns) >= 1:
        office_col = df.columns[0]
    if month_col is None and len(df.columns) >= 2:
        month_col = df.columns[1]
    if approved_total is None and len(df.columns) >= 5:
        approved_total = df.columns[4]
    if actual_total is None and len(df.columns) >= 8:
        actual_total = df.columns[7]
    if required_total is None and len(df.columns) >= 11:
        required_total = df.columns[10]
    if capacity_pct is None and len(df.columns) >= 12:
        capacity_pct = df.columns[11]
    if status_col is None and len(df.columns) >= 13:
        status_col = df.columns[12]

    out = pd.DataFrame({
        "Office": df[office_col].map(clean_text),
        "Month": df[month_col].map(normalize_month),
        "Approved HC": safe_numeric(df[approved_total]),
        "Actual HC": safe_numeric(df[actual_total]),
        "Required HC": safe_numeric(df[required_total]),
        "Capacity % Source": safe_numeric(df[capacity_pct]),
        "Status Source": df[status_col].map(clean_text),
    })

    # Không lấy dòng chỉ có Office/Month template nhưng không có dữ liệu HC thực
    metrics = ["Approved HC", "Actual HC", "Required HC"]
    out["Data_Available"] = out[metrics].notna().any(axis=1)
    out = out[out["Office"].ne("") & out["Month"].notna()].copy()

    # Recalculate Capacity để không phụ thuộc cached formula.
    out["Capacity %"] = np.where(
        out["Actual HC"].fillna(0) > 0,
        out["Required HC"] / out["Actual HC"],
        np.nan
    )

    def cap_status(v):
        if pd.isna(v):
            return "No data"
        if v > 1:
            return "Overload"
        if v > 0.95:
            return "High load"
        if v >= 0.90:
            return "Balanced"
        return "Less load"

    out["Capacity Status"] = out["Capacity %"].map(cap_status)
    out["Month Order"] = out["Month"].map(MONTH_ORDER)
    out["Month Label"] = out["Month"].map(month_label)
    return out


@st.cache_data(show_spinner=False)
def load_shipment(file_bytes):
    raw = read_sheet(file_bytes, "Shipment volume")
    columns = build_multilevel_columns(raw, [1, 2])
    df = raw.iloc[3:].copy()
    df.columns = columns
    df = df.dropna(how="all").reset_index(drop=True)

    office_col = fuzzy_col(df.columns, ["office"])
    month_col = fuzzy_col(df.columns, ["month"])
    active_col = fuzzy_col(df.columns, ["active", "customer"])
    total_col = fuzzy_col(df.columns, ["total"])

    # Fallback positional logic từ workbook đã phân tích
    if office_col is None:
        office_col = df.columns[0]
    if month_col is None:
        month_col = df.columns[1]
    if active_col is None and len(df.columns) >= 3:
        active_col = df.columns[2]
    if total_col is None and len(df.columns) >= 20:
        total_col = df.columns[19]

    base_cols = {office_col, month_col, active_col, total_col}

    # Theo workbook, D:S là transportation mode.
    positional_modes = list(df.columns[3:19]) if len(df.columns) >= 20 else []
    mode_cols = [c for c in positional_modes if c not in base_cols]

    wide = pd.DataFrame({
        "Office": df[office_col].map(clean_text),
        "Month": df[month_col].map(normalize_month),
        "Active Customer": safe_numeric(df[active_col]),
        "Total Source": safe_numeric(df[total_col]),
    })

    for col in mode_cols:
        wide[str(col)] = safe_numeric(df[col])

    wide = wide[wide["Office"].ne("") & wide["Month"].notna()].copy()
    wide["Data_Available"] = wide[["Active Customer", "Total Source"] + [str(c) for c in mode_cols]].notna().any(axis=1)

    # Tính lại Total từ các mode thay vì phụ thuộc cached formula
    numeric_mode_names = [str(c) for c in mode_cols]
    wide["Total Shipment Volume"] = wide[numeric_mode_names].sum(axis=1, min_count=1)
    wide["Month Order"] = wide["Month"].map(MONTH_ORDER)
    wide["Month Label"] = wide["Month"].map(month_label)

    long = wide.melt(
        id_vars=["Office", "Month", "Month Order", "Month Label", "Active Customer",
                 "Total Source", "Total Shipment Volume", "Data_Available"],
        value_vars=numeric_mode_names,
        var_name="Transportation Mode",
        value_name="Volume",
    )
    long["Transportation Mode"] = (
        long["Transportation Mode"]
        .astype(str)
        .str.replace(r"^.*\|\s*", "", regex=True)
        .str.strip()
    )
    long["Volume"] = safe_numeric(long["Volume"])
    return wide, long


@st.cache_data(show_spinner=False)
def load_bu(file_bytes):
    raw = read_sheet(file_bytes, "BU allocation")
    columns = build_multilevel_columns(raw, [1, 2])
    df = raw.iloc[3:].copy()
    df.columns = columns
    df = df.dropna(how="all").reset_index(drop=True)

    office_col = fuzzy_col(df.columns, ["office"])
    month_col = fuzzy_col(df.columns, ["month"])

    if office_col is None:
        office_col = df.columns[0]
    if month_col is None:
        month_col = df.columns[1]

    # Workbook analysis: A Office, B Month, C BU/Segment, D:K 4 cặp Volume/Processing Time, L workload, M %
    segment_col = df.columns[2] if len(df.columns) > 2 else None
    total_workload_col = df.columns[11] if len(df.columns) > 11 else fuzzy_col(df.columns, ["total", "workload"])
    network_pct_col = df.columns[12] if len(df.columns) > 12 else fuzzy_col(df.columns, ["network"])

    out = pd.DataFrame({
        "Office": df[office_col].map(clean_text),
        "Month": df[month_col].map(normalize_month),
        "BU": df[segment_col].map(clean_text) if segment_col else "",
        "Total Workload": safe_numeric(df[total_workload_col]) if total_workload_col else np.nan,
        "% of Network Source": safe_numeric(df[network_pct_col]) if network_pct_col else np.nan,
    })

    # Cặp cột theo vị trí
    group_defs = {
        "Core": (3, 4),
        "Ancillary": (5, 6),
        "Supporting": (7, 8),
        "Exception": (9, 10),
    }

    long_rows = []
    for idx, row in df.iterrows():
        office = clean_text(row[office_col])
        month = normalize_month(row[month_col])
        bu = clean_text(row[segment_col]) if segment_col else ""
        if not office or month is None:
            continue

        total_workload = pd.to_numeric(row[total_workload_col], errors="coerce") if total_workload_col else np.nan

        for work_type, (vol_idx, time_idx) in group_defs.items():
            volume = pd.to_numeric(row.iloc[vol_idx], errors="coerce") if len(row) > vol_idx else np.nan
            proc_time = pd.to_numeric(row.iloc[time_idx], errors="coerce") if len(row) > time_idx else np.nan
            long_rows.append({
                "Office": office,
                "Month": month,
                "Month Order": MONTH_ORDER.get(month),
                "Month Label": month_label(month),
                "BU": bu,
                "Work Type": work_type,
                "Volume": volume,
                "Processing Time": proc_time,
                "Total Workload": total_workload,
            })

    detail = pd.DataFrame(long_rows)

    out = out[out["Office"].ne("") & out["Month"].notna()].copy()
    out["Month Order"] = out["Month"].map(MONTH_ORDER)
    out["Month Label"] = out["Month"].map(month_label)
    out["Data_Available"] = out["Total Workload"].notna()

    # Recalculate % of workload contribution theo Office+Month
    denom = out.groupby(["Office", "Month"])["Total Workload"].transform("sum")
    out["Workload Contribution %"] = np.where(
        denom.abs() > 0,
        out["Total Workload"] / denom,
        np.nan
    )

    return out, detail


@st.cache_data(show_spinner=False)
def load_customer(file_bytes):
    """
    Đọc customer-level data từ N-S Customer list.

    Lưu ý:
    - Sheet có header 2 dòng:
        Row 1: No. | Office | Customer | SHIPMENT VOLUME ...
        Row 2: ... | Apr-26 | May-26 | ... | Mar-27 | Total
    - Dùng truy cập THEO VỊ TRÍ (.iloc), không dùng tên cột trùng/rỗng.
      Cách này tránh lỗi:
      "The truth value of a Series is ambiguous".
    - Không sử dụng cột Total hardcoded.
    - Không dùng cached TOTAL của HAN Customer list / HLC.
    """
    raw = read_sheet(file_bytes, "N-S Customer list")

    if raw.shape[1] < 4 or raw.shape[0] < 3:
        return pd.DataFrame(), pd.DataFrame()

    # Vị trí cố định theo workbook đã phân tích:
    # A=No., B=Office, C=Customer, D:O=12 tháng, P=Total
    OFFICE_IDX = 1
    CUSTOMER_IDX = 2
    MONTH_START_IDX = 3
    MONTH_END_IDX_EXCLUSIVE = min(15, raw.shape[1])  # D:O

    month_indices = list(range(MONTH_START_IDX, MONTH_END_IDX_EXCLUSIVE))

    # Header tháng nằm ở row index 1.
    month_map = {}
    for idx in month_indices:
        month = normalize_month(raw.iat[1, idx])
        if month is not None:
            month_map[idx] = month

    records = []

    # Data bắt đầu từ row index 2.
    for row_idx in range(2, len(raw)):
        office = clean_text(raw.iat[row_idx, OFFICE_IDX])
        customer = clean_text(raw.iat[row_idx, CUSTOMER_IDX])

        # Bỏ dòng trống / TOTAL
        if not customer or customer.lower() == "total":
            continue

        # Theo dữ liệu hiện tại, N-S Customer list thuộc HAD.
        if not office:
            office = "HAD"

        for col_idx, month in month_map.items():
            volume = pd.to_numeric(raw.iat[row_idx, col_idx], errors="coerce")

            records.append({
                "Office": office,
                "Customer": customer,
                "Month": month,
                "Month Order": MONTH_ORDER.get(month),
                "Month Label": month_label(month),
                "Volume": volume,
            })

    long = pd.DataFrame(records)

    if long.empty:
        return long, pd.DataFrame(
            columns=["Office", "Customer", "Customer Total"]
        )

    # Missing vẫn là NaN, KHÔNG tự đổi thành 0.
    valid = long[long["Volume"].notna()].copy()

    if valid.empty:
        totals = pd.DataFrame(
            columns=["Office", "Customer", "Customer Total"]
        )
    else:
        totals = (
            valid.groupby(["Office", "Customer"], as_index=False)["Volume"]
            .sum()
            .rename(columns={"Volume": "Customer Total"})
        )

    return long, totals


# ============================================================
# 5. DATA SOURCE
# ============================================================
st.sidebar.markdown("## 📊 Dashboard")
st.sidebar.caption("Workload • Capacity • Volume • Customer")

uploaded_file = st.sidebar.file_uploader(
    "Upload Excel workbook",
    type=["xlsx", "xlsm"],
    help="Chọn file Template data for Dashboard."
)

DEFAULT_FILE = Path("Template data for Dashboard.xlsx")

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    source_name = uploaded_file.name
elif DEFAULT_FILE.exists():
    file_bytes = DEFAULT_FILE.read_bytes()
    source_name = DEFAULT_FILE.name
else:
    st.title("Executive Workload & Capacity Dashboard")
    st.warning(
        "Vui lòng upload file Excel ở sidebar. "
        "Nếu muốn chạy không cần upload, đặt file cùng thư mục app.py và đổi tên thành "
        "`Template data for Dashboard.xlsx`."
    )
    st.stop()


# ============================================================
# 6. LOAD & VALIDATE
# ============================================================
try:
    sheet_names = get_sheet_names(file_bytes)
    required_sheets = ["HC", "Shipment volume", "BU allocation", "N-S Customer list"]
    missing = [s for s in required_sheets if s not in sheet_names]
    if missing:
        st.error(f"Thiếu sheet bắt buộc: {', '.join(missing)}")
        st.stop()

    hc = load_hc(file_bytes)
    shipment_wide, shipment_long = load_shipment(file_bytes)
    bu, bu_detail = load_bu(file_bytes)
    customer_long, customer_total = load_customer(file_bytes)

except Exception as exc:
    st.error("Không thể đọc workbook hoặc cấu trúc file đã thay đổi.")
    st.exception(exc)
    st.stop()


# ============================================================
# 7. FILTERS
# ============================================================
all_offices = sorted(
    set(hc["Office"].dropna())
    | set(shipment_wide["Office"].dropna())
    | set(bu["Office"].dropna())
)
all_offices = [x for x in all_offices if x]

available_months = sorted(
    set(hc.loc[hc["Data_Available"], "Month"].dropna())
    | set(shipment_wide.loc[shipment_wide["Data_Available"], "Month"].dropna())
    | set(bu.loc[bu["Data_Available"], "Month"].dropna()),
    key=lambda x: MONTH_ORDER.get(x, 99),
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Filters")

office_filter = st.sidebar.multiselect(
    "Office",
    options=all_offices,
    default=all_offices,
)

month_filter = st.sidebar.multiselect(
    "Month",
    options=available_months,
    default=available_months,
    format_func=month_label,
)

if not office_filter or not month_filter:
    st.warning("Vui lòng chọn ít nhất 1 Office và 1 Month.")
    st.stop()


# ============================================================
# 8. FILTERED DATA
# ============================================================
def apply_main_filter(df):
    if df.empty:
        return df
    return df[
        df["Office"].isin(office_filter)
        & df["Month"].isin(month_filter)
    ].copy()


f_hc = apply_main_filter(hc)
f_ship_wide = apply_main_filter(shipment_wide)
f_ship_long = apply_main_filter(shipment_long)
f_bu = apply_main_filter(bu)
f_bu_detail = apply_main_filter(bu_detail)
f_customer = apply_main_filter(customer_long) if not customer_long.empty else customer_long


# ============================================================
# 9. HEADER
# ============================================================
st.markdown(
    '<div class="dashboard-title">EXECUTIVE WORKLOAD & CAPACITY DASHBOARD</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="dashboard-subtitle">Source: {source_name} &nbsp;|&nbsp; '
    f'Office: {", ".join(office_filter)} &nbsp;|&nbsp; '
    f'Month: {", ".join(month_label(m) for m in month_filter)}</div>',
    unsafe_allow_html=True,
)


# ============================================================
# 10. NAVIGATION
# ============================================================
page = st.sidebar.radio(
    "Navigation",
    ["Executive Overview", "Workload & Capacity", "Volume & Customer Analysis", "Data Quality"],
)


# ============================================================
# 11. CALCULATIONS
# ============================================================
actual_hc = f_hc.loc[f_hc["Data_Available"], "Actual HC"].sum(min_count=1)
required_hc = f_hc.loc[f_hc["Data_Available"], "Required HC"].sum(min_count=1)
approved_hc = f_hc.loc[f_hc["Data_Available"], "Approved HC"].sum(min_count=1)

# Network Capacity: weighted theo business logic = SUM Required / SUM Actual
network_capacity = (
    required_hc / actual_hc
    if pd.notna(actual_hc) and actual_hc != 0 and pd.notna(required_hc)
    else np.nan
)

total_volume = f_ship_wide.loc[
    f_ship_wide["Data_Available"], "Total Shipment Volume"
].sum(min_count=1)

total_workload = f_bu.loc[
    f_bu["Data_Available"], "Total Workload"
].sum(min_count=1)


# ============================================================
# 12. PAGE 1 — EXECUTIVE OVERVIEW
# ============================================================
if page == "Executive Overview":
    st.markdown('<div class="section-title">Executive Overview</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card(
            "Actual HC",
            f"{actual_hc:,.1f}" if pd.notna(actual_hc) else "No data",
            "SUM of available Actual HC",
        )
    with c2:
        kpi_card(
            "Required HC",
            f"{required_hc:,.1f}" if pd.notna(required_hc) else "No data",
            "SUM of available Required HC",
        )
    with c3:
        kpi_card(
            "Network Capacity",
            f"{network_capacity:.1%}" if pd.notna(network_capacity) else "No data",
            "SUM Required HC / SUM Actual HC",
        )
    with c4:
        kpi_card(
            "Shipment Volume",
            f"{total_volume:,.0f}" if pd.notna(total_volume) else "No data",
            "Recalculated from transportation modes",
        )
    with c5:
        kpi_card(
            "Total Workload",
            f"{total_workload:,.0f}" if pd.notna(total_workload) else "No data",
            "SUM of available workload",
        )

    st.markdown(
        '<div class="info-box"><b>Capacity logic:</b> Network Capacity is calculated as '
        '<b>SUM(Required HC) / SUM(Actual HC)</b>, not the simple average of office percentages.</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        cap_data = f_hc[f_hc["Data_Available"]].copy()
        if cap_data.empty:
            no_data()
        else:
            cap_data = cap_data.sort_values(["Month Order", "Office"])
            fig = px.bar(
                cap_data,
                x="Office",
                y="Capacity %",
                color="Capacity Status",
                facet_col="Month Label" if cap_data["Month"].nunique() <= 3 else None,
                category_orders={"Capacity Status": STATUS_ORDER},
                color_discrete_map=STATUS_COLOR,
                text=cap_data["Capacity %"].map(lambda x: f"{x:.0%}" if pd.notna(x) else ""),
            )
            fig.update_yaxes(tickformat=".0%")
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig = fig_layout(fig, "Capacity by Office", 360)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        vol_month = (
            f_ship_wide[f_ship_wide["Data_Available"]]
            .groupby(["Month", "Month Order", "Month Label"], as_index=False)["Total Shipment Volume"]
            .sum()
            .sort_values("Month Order")
        )
        if vol_month.empty:
            no_data()
        else:
            fig = px.line(
                vol_month,
                x="Month Label",
                y="Total Shipment Volume",
                markers=True,
            )
            fig.update_traces(line=dict(width=3), marker=dict(size=8))
            fig = fig_layout(fig, "Shipment Volume Trend", 360, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)

    with left:
        wl_office = (
            f_bu[f_bu["Data_Available"]]
            .groupby("Office", as_index=False)["Total Workload"]
            .sum()
            .sort_values("Total Workload", ascending=True)
        )
        if wl_office.empty:
            no_data()
        else:
            fig = px.bar(
                wl_office,
                x="Total Workload",
                y="Office",
                orientation="h",
                text_auto=".3s",
            )
            fig = fig_layout(fig, "Total Workload by Office", 340, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        hc_compare = (
            f_hc[f_hc["Data_Available"]]
            .groupby("Office", as_index=False)[["Approved HC", "Actual HC", "Required HC"]]
            .sum(min_count=1)
            .melt(id_vars="Office", var_name="HC Type", value_name="HC")
        )
        if hc_compare.empty:
            no_data()
        else:
            fig = px.bar(
                hc_compare,
                x="Office",
                y="HC",
                color="HC Type",
                barmode="group",
                color_discrete_map={
                    "Approved HC": LIGHT_BLUE,
                    "Actual HC": BLUE,
                    "Required HC": ORANGE,
                },
            )
            fig = fig_layout(fig, "Approved vs Actual vs Required HC", 340)
            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 13. PAGE 2 — WORKLOAD & CAPACITY
# ============================================================
elif page == "Workload & Capacity":
    st.markdown('<div class="section-title">Workload & Capacity</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Approved HC", f"{approved_hc:,.1f}" if pd.notna(approved_hc) else "No data")
    with c2:
        kpi_card("Actual HC", f"{actual_hc:,.1f}" if pd.notna(actual_hc) else "No data")
    with c3:
        kpi_card("Required HC", f"{required_hc:,.1f}" if pd.notna(required_hc) else "No data")
    with c4:
        kpi_card(
            "Network Capacity",
            f"{network_capacity:.1%}" if pd.notna(network_capacity) else "No data",
            "Weighted network calculation",
        )

    left, right = st.columns(2)

    with left:
        cap = f_hc[f_hc["Data_Available"]].copy()
        if cap.empty:
            no_data()
        else:
            pivot = cap.pivot_table(
                index="Office",
                columns="Month Label",
                values="Capacity %",
                aggfunc="mean",
            )
            ordered_cols = [
                month_label(m) for m in sorted(month_filter, key=lambda x: MONTH_ORDER[x])
                if month_label(m) in pivot.columns
            ]
            pivot = pivot.reindex(columns=ordered_cols)

            fig = go.Figure(
                data=go.Heatmap(
                    z=pivot.values,
                    x=pivot.columns,
                    y=pivot.index,
                    text=np.where(
                        pd.isna(pivot.values),
                        "No data",
                        np.vectorize(lambda x: f"{x:.0%}")(np.nan_to_num(pivot.values, nan=0))
                    ),
                    texttemplate="%{text}",
                    hovertemplate="Office=%{y}<br>Month=%{x}<br>Capacity=%{text}<extra></extra>",
                    zmin=0.80,
                    zmax=1.10,
                    colorscale=[
                        [0.00, "#DCFCE7"],
                        [0.45, "#DBEAFE"],
                        [0.70, "#FEF3C7"],
                        [1.00, "#FEE2E2"],
                    ],
                    colorbar=dict(tickformat=".0%"),
                )
            )
            fig = fig_layout(fig, "Capacity Heatmap", 360, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        hc_long = (
            f_hc[f_hc["Data_Available"]]
            .groupby(["Office", "Month", "Month Order", "Month Label"], as_index=False)[
                ["Approved HC", "Actual HC", "Required HC"]
            ]
            .sum(min_count=1)
            .melt(
                id_vars=["Office", "Month", "Month Order", "Month Label"],
                var_name="HC Type",
                value_name="HC",
            )
        )
        if hc_long.empty:
            no_data()
        else:
            fig = px.bar(
                hc_long,
                x="Office",
                y="HC",
                color="HC Type",
                barmode="group",
                facet_col="Month Label" if hc_long["Month"].nunique() <= 3 else None,
                color_discrete_map={
                    "Approved HC": LIGHT_BLUE,
                    "Actual HC": BLUE,
                    "Required HC": ORANGE,
                },
            )
            fig = fig_layout(fig, "HC Comparison", 360)
            st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)

    with left:
        wl_bu = (
            f_bu[f_bu["Data_Available"] & f_bu["BU"].ne("")]
            .groupby("BU", as_index=False)["Total Workload"]
            .sum()
            .sort_values("Total Workload", ascending=True)
        )
        if wl_bu.empty:
            no_data("No workload breakdown available for selected filters.")
        else:
            fig = px.bar(
                wl_bu,
                x="Total Workload",
                y="BU",
                orientation="h",
                text_auto=".3s",
                category_orders={"BU": BU_ORDER},
            )
            fig = fig_layout(fig, "Workload by BU / Service Segment", 360, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        wt = f_bu_detail[
            f_bu_detail["Processing Time"].notna()
        ].copy()

        # Giá trị âm được giữ nguyên để phản ánh nguồn nhưng sẽ cảnh báo
        wt_group = (
            wt.groupby("Work Type", as_index=False)["Processing Time"]
            .sum(min_count=1)
        )
        if wt_group.empty:
            no_data("No Core/Ancillary/Supporting/Exception breakdown available.")
        else:
            fig = px.bar(
                wt_group,
                x="Work Type",
                y="Processing Time",
                category_orders={
                    "Work Type": ["Core", "Ancillary", "Supporting", "Exception"]
                },
            )
            fig = fig_layout(fig, "Processing Time by Work Type", 360, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # Workload vs Capacity — không dùng dual-axis mặc định vì khác đơn vị,
    # thay bằng scatter để nhìn quan hệ dễ hơn.
    joined_hc = (
        f_hc[f_hc["Data_Available"]]
        .groupby(["Office", "Month"], as_index=False)
        .agg(
            Actual_HC=("Actual HC", "sum"),
            Required_HC=("Required HC", "sum"),
        )
    )
    joined_hc["Capacity %"] = np.where(
        joined_hc["Actual_HC"] != 0,
        joined_hc["Required_HC"] / joined_hc["Actual_HC"],
        np.nan,
    )
    joined_wl = (
        f_bu[f_bu["Data_Available"]]
        .groupby(["Office", "Month"], as_index=False)["Total Workload"]
        .sum()
    )
    relation = joined_hc.merge(joined_wl, on=["Office", "Month"], how="inner")
    relation["Month Label"] = relation["Month"].map(month_label)

    if not relation.empty:
        fig = px.scatter(
            relation,
            x="Total Workload",
            y="Capacity %",
            color="Office",
            symbol="Month Label",
            size="Actual_HC",
            hover_data=["Required_HC", "Actual_HC"],
        )
        fig.add_hline(y=1.0, line_dash="dash", annotation_text="100% Overload threshold")
        fig.add_hline(y=0.95, line_dash="dot", annotation_text="95%")
        fig.update_yaxes(tickformat=".0%")
        fig = fig_layout(fig, "Workload vs Capacity", 400)
        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 14. PAGE 3 — VOLUME & CUSTOMER ANALYSIS
# ============================================================
elif page == "Volume & Customer Analysis":
    st.markdown('<div class="section-title">Volume & Customer Analysis</div>', unsafe_allow_html=True)

    # Page-specific filters
    mode_options = sorted([
        x for x in f_ship_long["Transportation Mode"].dropna().unique()
        if clean_text(x)
    ])
    customer_options = sorted([
        x for x in f_customer["Customer"].dropna().unique()
    ]) if not f_customer.empty else []

    f1, f2 = st.columns(2)
    with f1:
        selected_modes = st.multiselect(
            "Transportation Mode",
            mode_options,
            default=mode_options,
        )
    with f2:
        top_n = st.select_slider(
            "Top Customers",
            options=[5, 10, 15, 20],
            value=10,
        )

    page_ship_long = f_ship_long[
        f_ship_long["Transportation Mode"].isin(selected_modes)
    ].copy()

    mode_volume = page_ship_long["Volume"].sum(min_count=1)

    # Active Customer không SUM xuyên nhiều tháng vì có thể double count.
    # Chỉ hiển thị khi 1 tháng được chọn; nhiều tháng = N/A.
    if len(month_filter) == 1:
        active_customer_value = f_ship_wide.loc[
            f_ship_wide["Data_Available"], "Active Customer"
        ].sum(min_count=1)
        active_display = (
            f"{active_customer_value:,.0f}"
            if pd.notna(active_customer_value)
            else "No data"
        )
        active_note = "SUM across selected offices for one month"
    else:
        active_display = "N/A"
        active_note = "Not aggregated across multiple months"

    customer_data_available = (
        not f_customer.empty and f_customer["Volume"].notna().any()
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card(
            "Shipment Volume",
            f"{mode_volume:,.0f}" if pd.notna(mode_volume) else "No data",
            "From transportation mode source",
        )
    with c2:
        kpi_card("Active Customers", active_display, active_note)
    with c3:
        customer_volume = f_customer["Volume"].sum(min_count=1) if customer_data_available else np.nan
        kpi_card(
            "Customer-list Volume",
            f"{customer_volume:,.0f}" if pd.notna(customer_volume) else "No data",
            "Separate source — not reconciled with mode volume",
        )

    st.markdown(
        '<div class="warning-box"><b>Data-quality rule:</b> Shipment Volume by mode and '
        'Customer-list Volume are displayed as separate sources because the workbook currently '
        'does not reconcile them. They are never added together.</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        vol_office = (
            page_ship_long.groupby("Office", as_index=False)["Volume"]
            .sum(min_count=1)
            .sort_values("Volume", ascending=True)
        )
        if vol_office.empty:
            no_data()
        else:
            fig = px.bar(
                vol_office,
                x="Volume",
                y="Office",
                orientation="h",
                text_auto=".3s",
            )
            fig = fig_layout(fig, "Shipment Volume by Office", 350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        vol_month = (
            page_ship_long.groupby(
                ["Month", "Month Order", "Month Label"], as_index=False
            )["Volume"]
            .sum(min_count=1)
            .sort_values("Month Order")
        )
        if vol_month.empty:
            no_data()
        else:
            fig = px.line(
                vol_month,
                x="Month Label",
                y="Volume",
                markers=True,
            )
            fig = fig_layout(fig, "Shipment Volume Trend", 350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    mode_breakdown = (
        page_ship_long.groupby("Transportation Mode", as_index=False)["Volume"]
        .sum(min_count=1)
        .query("Volume != 0")
        .sort_values("Volume", ascending=True)
    )
    if not mode_breakdown.empty:
        fig = px.bar(
            mode_breakdown,
            x="Volume",
            y="Transportation Mode",
            orientation="h",
            text_auto=".3s",
        )
        fig = fig_layout(fig, "Volume by Transportation Mode", 420, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Customer Analysis</div>', unsafe_allow_html=True)

    # Customer data hiện tại chỉ đáng tin cậy cho HAD.
    if "HAD" not in office_filter:
        no_data("Customer-level data is currently available only for HAD in the source workbook.")
    elif not customer_data_available:
        no_data("No customer-level data available for the selected month(s).")
    else:
        customer_filtered = f_customer[
            (f_customer["Office"] == "HAD")
            & f_customer["Volume"].notna()
        ].copy()

        cust_totals = (
            customer_filtered.groupby("Customer", as_index=False)["Volume"]
            .sum()
            .sort_values("Volume", ascending=False)
        )
        overall_customer_volume = cust_totals["Volume"].sum()
        cust_totals["Contribution %"] = np.where(
            overall_customer_volume != 0,
            cust_totals["Volume"] / overall_customer_volume,
            np.nan,
        )

        top = cust_totals.head(top_n).sort_values("Volume", ascending=True)

        left, right = st.columns(2)

        with left:
            fig = px.bar(
                top,
                x="Volume",
                y="Customer",
                orientation="h",
                text_auto=".3s",
            )
            fig = fig_layout(fig, f"Top {top_n} Customers by Volume", 430, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with right:
            pareto = cust_totals.copy()
            pareto["Cumulative %"] = pareto["Volume"].cumsum() / pareto["Volume"].sum()
            fig = go.Figure()
            fig.add_bar(
                x=pareto["Customer"].head(top_n),
                y=pareto["Volume"].head(top_n),
                name="Volume",
            )
            fig.add_scatter(
                x=pareto["Customer"].head(top_n),
                y=pareto["Cumulative %"].head(top_n),
                name="Cumulative %",
                yaxis="y2",
                mode="lines+markers",
            )
            fig.update_layout(
                yaxis2=dict(
                    overlaying="y",
                    side="right",
                    tickformat=".0%",
                    range=[0, 1.05],
                    showgrid=False,
                )
            )
            fig = fig_layout(fig, f"Customer Contribution — Top {top_n}", 430)
            fig.update_xaxes(tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)

        top_names = cust_totals.head(min(top_n, 10))["Customer"].tolist()
        trend = (
            customer_filtered[customer_filtered["Customer"].isin(top_names)]
            .groupby(["Customer", "Month", "Month Order", "Month Label"], as_index=False)["Volume"]
            .sum()
            .sort_values("Month Order")
        )
        if not trend.empty:
            fig = px.line(
                trend,
                x="Month Label",
                y="Volume",
                color="Customer",
                markers=True,
            )
            fig = fig_layout(fig, "Monthly Customer Volume Trend", 430)
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            cust_totals.rename(columns={"Volume": "Total Volume"}).style.format(
                {"Total Volume": "{:,.0f}", "Contribution %": "{:.1%}"}
            ),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# 15. DATA QUALITY PAGE
# ============================================================
else:
    st.markdown('<div class="section-title">Data Quality & Validation</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="warning-box">
        Dashboard intentionally keeps <b>Missing data ≠ Zero</b>. Missing Office/Month records
        are excluded from KPI calculations instead of being filled with zero.
        </div>
        """,
        unsafe_allow_html=True,
    )

    quality_rows = []

    for office in all_offices:
        for month in FISCAL_MONTHS:
            hc_ok = bool(
                ((hc["Office"] == office) & (hc["Month"] == month) & hc["Data_Available"]).any()
            )
            ship_ok = bool(
                ((shipment_wide["Office"] == office) & (shipment_wide["Month"] == month) & shipment_wide["Data_Available"]).any()
            )
            bu_ok = bool(
                ((bu["Office"] == office) & (bu["Month"] == month) & bu["Data_Available"]).any()
            )
            cust_ok = bool(
                not customer_long.empty
                and (
                    (customer_long["Office"] == office)
                    & (customer_long["Month"] == month)
                    & customer_long["Volume"].notna()
                ).any()
            )

            quality_rows.append({
                "Office": office,
                "Month": month_label(month),
                "HC": "Available" if hc_ok else "No data",
                "Shipment": "Available" if ship_ok else "No data",
                "BU Allocation": "Available" if bu_ok else "No data",
                "Customer": "Available" if cust_ok else "No data",
            })

    quality_df = pd.DataFrame(quality_rows)

    st.markdown("#### Data Availability Matrix")
    st.dataframe(
        quality_df,
        use_container_width=True,
        hide_index=True,
    )

    # Negative processing time check
    neg = bu_detail[bu_detail["Processing Time"] < 0].copy()
    st.markdown("#### Flagged Issues")

    issue_count = 0

    if not neg.empty:
        issue_count += 1
        st.warning(
            f"Found {len(neg)} record(s) with negative Processing Time. "
            "These values are kept as source data and are not auto-corrected."
        )
        st.dataframe(
            neg[["Office", "Month Label", "BU", "Work Type", "Processing Time"]],
            use_container_width=True,
            hide_index=True,
        )

    # BU suspicious Office rows check, based on source observation
    suspicious = bu[
        (bu["Month"].isin(["Apr", "May"]))
        & (bu["Office"] == "HAN")
        & bu["BU"].isin(["TR", "WH"])
    ]
    if not suspicious.empty:
        issue_count += 1
        st.warning(
            "BU allocation contains rows that may require Office validation. "
            "Dashboard does not automatically relabel them."
        )

    # Reconciliation example
    if "HAD" in shipment_wide["Office"].values and not customer_long.empty:
        ship_had = (
            shipment_wide[
                (shipment_wide["Office"] == "HAD")
                & shipment_wide["Data_Available"]
            ]
            .groupby("Month", as_index=False)["Total Shipment Volume"]
            .sum()
        )
        cust_had = (
            customer_long[
                (customer_long["Office"] == "HAD")
                & customer_long["Volume"].notna()
            ]
            .groupby("Month", as_index=False)["Volume"]
            .sum()
        )
        recon = ship_had.merge(cust_had, on="Month", how="outer")
        recon["Difference"] = recon["Volume"] - recon["Total Shipment Volume"]
        recon["Month Order"] = recon["Month"].map(MONTH_ORDER)
        recon["Month"] = recon["Month"].map(month_label)
        recon = recon.sort_values("Month Order")

        if not recon.empty:
            issue_count += 1
            st.markdown("##### Shipment vs Customer-list Reconciliation — HAD")
            st.dataframe(
                recon[["Month", "Total Shipment Volume", "Volume", "Difference"]]
                .rename(columns={
                    "Total Shipment Volume": "Shipment Source",
                    "Volume": "Customer-list Source",
                }),
                use_container_width=True,
                hide_index=True,
            )

    if issue_count == 0:
        st.success("No flagged data-quality issue was detected by the current checks.")


# ============================================================
# 16. FOOTER
# ============================================================
st.markdown(
    '<div class="footer">Internal management dashboard • '
    'Missing data is not treated as zero • Source workbook remains unchanged</div>',
    unsafe_allow_html=True,
)
