import streamlit as pd
import pandas as pd
import numpy as np
import plotly.express as px

# 1. Cấu hình trang Dashboard (Luôn đặt ở đầu file)
st.set_page_config(
    page_title="Executive Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tạo dữ liệu giả lập để chạy thử
@st.cache_data
def load_mock_data():
    months = pd.date_range(start="2025-01-01", periods=12, freq="M")
    data = {
        "Tháng": months.strftime("%m/%Y"),
        "Doanh thu":,
        "Lợi nhuận":,
        "Khu vực": ["Miền Bắc", "Miền Nam", "Miền Trung", "Miền Bắc", "Miền Nam", "Miền Trung", "Miền Bắc", "Miền Nam", "Miền Trung", "Miền Bắc", "Miền Nam", "Miền Trung"]
    }
    return pd.DataFrame(data)

df = load_mock_data()

# 2. Thanh bên (Sidebar) - Nơi chứa bộ lọc cho sếp chọn
st.sidebar.header("Bộ Lọc Báo Cáo")
selected_region = st.sidebar.multiselect(
    "Chọn Khu Vực:",
    options=df["Khu vực"].unique(),
    default=df["Khu vực"].unique()
)

# Lọc dữ liệu theo lựa chọn ở Sidebar
filtered_df = df[df["Khu vực"].isin(selected_region)]

# 3. Trang chính (Main Page)
st.title("📊 BÁO CÁO HIỆU SUẤT KINH DOANH CHO BAN LÃNH ĐẠO")
st.markdown("---")

# Hàng 1: Thẻ chỉ số KPI cốt lõi (Metrics)
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_rev = filtered_df["Doanh thu"].sum()
    st.metric(label="💰 Tổng Doanh Thu", value=f"{total_rev} tỷ", delta="+12% vs kỳ trước")

with col2:
    total_prof = filtered_df["Lợi nhuận"].sum()
    st.metric(label="📈 Tổng Lợi Nhuận", value=f"{total_prof} tỷ", delta="+15% vs kỳ trước")

with col3:
    margin = round((total_prof / total_rev) * 100, 1) if total_rev > 0 else 0
    st.metric(label="🎯 Biên Lợi Nhuận", value=f"{margin}%", delta="+1.2%")

with col4:
    st.metric(label="👥 Khách Hàng Mới", value="1,240", delta="-2% (Cần lưu ý)")

st.markdown("---")

# Hàng 2: Biểu đồ trực quan xu hướng và tỷ trọng
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("📉 Xu hướng Doanh thu & Lợi nhuận")
    fig_line = px.line(
        filtered_df, 
        x="Tháng", 
        y=["Doanh thu", "Lợi nhuận"], 
        markers=True,
        title="Biểu đồ phát triển theo dòng thời gian (Đơn vị: Tỷ VNĐ)",
        color_discrete_sequence=["#1f77b4", "#ff7f0e"]
    )
    fig_line.update_layout(legend_title_text="Chỉ số")
    st.plotly_chart(fig_line, use_container_width=True)

with col_chart2:
    st.subheader("📍 Đóng góp Lợi nhuận theo Khu vực")
    fig_bar = px.bar(
        filtered_df, 
        x="Khu vực", 
        y="Lợi nhuận", 
        color="Khu vực",
        title="Tỷ trọng lợi nhuận giữa các miền",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig_bar, use_container_width=True)
