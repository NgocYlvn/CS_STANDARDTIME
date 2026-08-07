# YLVN WORKLOAD & CAPACITY DASHBOARD

Dashboard được xây dựng bằng Python + Streamlit để theo dõi:
- Headcount / HC Capacity
- Shipment Volume
- Workload Allocation
- Customer Volume
- Tổng quan theo Office và Month

## 1. Cấu trúc thư mục khuyến nghị

```text
YLVN_Dashboard/
│
├── app.py
├── requirements.txt
├── README.md
├── RUN_DASHBOARD.bat
├── START_DASHBOARD.bat
└── 6ef9683a-8525-4425-a665-e467a6688d13.xlsx
```

> Nên để file Excel nguồn cùng thư mục với `app.py`.

## 2. Yêu cầu

- Windows 10/11
- Python 3.10 trở lên
- Có kết nối Internet khi cài thư viện lần đầu

Kiểm tra Python:

```cmd
python --version
```

Nếu lệnh trên không chạy, thử:

```cmd
py --version
```

## 3. Cài đặt lần đầu

### Cách đơn giản

Nhấp đúp:

```text
START_DASHBOARD.bat
```

File này sẽ:
1. Kiểm tra Python.
2. Tạo môi trường ảo `.venv` nếu chưa có.
3. Cài các thư viện trong `requirements.txt`.
4. Khởi động Streamlit Dashboard.

Lần đầu có thể mất vài phút để cài thư viện.

## 4. Chạy Dashboard những lần sau

Nhấp đúp:

```text
RUN_DASHBOARD.bat
```

Dashboard sẽ được mở tại địa chỉ mặc định:

```text
http://localhost:8501
```

Nếu trình duyệt không tự mở, copy địa chỉ Streamlit hiển thị trong cửa sổ CMD và dán vào Chrome/Edge.

## 5. Chạy thủ công bằng Command Prompt

Mở CMD tại thư mục dự án:

```cmd
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

## 6. File dữ liệu Excel

Dashboard hiện được thiết kế theo workbook nguồn có các sheet chính:

- `HC`
- `Shipment volume`
- `BU allocation`
- `N-S Customer list`

Ngoài ra workbook có thể chứa các customer list theo Office.

File Excel đang sử dụng header nhiều dòng, vì vậy không nên tự ý:
- đổi tên sheet;
- xóa dòng header;
- chèn thêm dòng phía trên bảng;
- đổi vị trí cột nguồn;

nếu chưa cập nhật lại logic trong `app.py`.

## 7. Cập nhật dữ liệu

Có 2 cách:

### Cách 1 — Thay file Excel nguồn

Giữ nguyên tên file Excel mà `app.py` đang nhận diện và thay dữ liệu mới vào workbook.

### Cách 2 — Upload trên Dashboard

Nếu giao diện có chức năng Upload Excel:
1. Mở Dashboard.
2. Chọn file Excel mới tại Sidebar.
3. Dashboard đọc dữ liệu mới.
4. Kiểm tra Office và Month filter trước khi sử dụng báo cáo.

## 8. Các file trong package

### `app.py`
Mã nguồn chính của Dashboard.

### `requirements.txt`
Danh sách thư viện Python cần cài.

### `START_DASHBOARD.bat`
Dùng khi thiết lập/chạy lần đầu. Tự tạo `.venv` và cài requirements.

### `RUN_DASHBOARD.bat`
Dùng cho các lần chạy thông thường. Nếu `.venv` chưa tồn tại, file sẽ hướng dẫn chạy `START_DASHBOARD.bat`.

## 9. Xử lý lỗi thường gặp

### `'python' is not recognized`

Python chưa được cài hoặc chưa được thêm vào PATH.

Cài Python và chọn:

```text
Add Python to PATH
```

trong quá trình cài đặt.

### `No module named streamlit`

Chạy lại:

```text
START_DASHBOARD.bat
```

hoặc:

```cmd
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Không tìm thấy file Excel

Kiểm tra:
- file Excel có cùng thư mục với `app.py`;
- tên file không bị thay đổi ngoài dự kiến;
- file không bị di chuyển sang thư mục khác.

### Port 8501 đang được sử dụng

Có thể chạy bằng port khác:

```cmd
.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

Sau đó mở:

```text
http://localhost:8502
```

## 10. Dừng Dashboard

Tại cửa sổ CMD đang chạy Streamlit, nhấn:

```text
Ctrl + C
```

Sau đó có thể đóng cửa sổ CMD.

## 11. Lưu ý khi chia sẻ cho đồng nghiệp

Nên gửi toàn bộ thư mục dự án, không chỉ gửi riêng `app.py`.

Người nhận chỉ cần:
1. Giải nén thư mục.
2. Cài Python nếu máy chưa có.
3. Chạy `START_DASHBOARD.bat` lần đầu.
4. Các lần sau chạy `RUN_DASHBOARD.bat`.

---
Internal Dashboard | YLVN | 2026
