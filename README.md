# Phần mềm MES giả định – ME6182

Xưởng gia công trục bậc 5 công đoạn (T1 Cắt phôi, T2 Tiện CNC, T3 Phay CNC, T4 Nhiệt luyện, T5 Kiểm tra, đóng gói).

## Cài đặt và chạy

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py             # mở http://localhost:8501
pytest -q                        # chạy 11 ca kiểm thử bắt buộc
```

Lần chạy đầu, phần mềm tự tạo `data/mes.db` từ các file trong `data/csv/`.
Vai trò "Quản trị hệ thống" có nút khởi tạo lại CSDL.

## Kịch bản chuẩn KB0

`python kb0.py` chạy lại kịch bản chuẩn (EDD, ca CA1, bắt đầu 10/11/2026 06:00, hạt giống 1) dùng để đối chiếu số liệu trong Chương 6 (chạy được khi các hàm Buổi 2–4 đã viết xong).

## Lưu ý trên Windows

- PowerShell báo lỗi khi kích hoạt `.venv`: chạy `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` một lần, hoặc dùng Command Prompt với `.venv\Scripts\activate.bat`.
- Đặt PYTHONPATH trong PowerShell: `$env:PYTHONPATH = "."`.

## Cấu trúc

| Thư mục | Lớp | Ghi chú |
|---|---|---|
| `app.py`, `pages/`, `ui.py` | Giao diện | Mỗi file trong `pages/` là một trang |
| `services/` | Nghiệp vụ | M1–M7; không chứa giao diện |
| `db/` | Truy cập dữ liệu | `schema.sql`, `database.py` |
| `simulator/` | Mô phỏng trạm | Sinh sự kiện cho lệnh đã phát |
| `data/csv/` | Dữ liệu nền | Thay bằng dữ liệu biến thể ngành của nhóm |
| `tests/` | Kiểm thử | pytest; `tests/csv_mau/` là bộ dữ liệu mẫu cố định cho kiểm thử, không sửa |

Quy tắc: trang giao diện chỉ đọc dữ liệu (câu SELECT qua `query_df`); mọi thao tác ghi đi qua `services/` (riêng trang Dữ liệu nền dùng `insert_row`, `update_row`, `delete_row`); mọi thay đổi trạng thái lệnh đi qua `services/planning.change_status`.

## Dành cho sinh viên
Tìm `TODO Buổi N` để biết hàm, trang cần viết ở mỗi buổi. Hàm hoàn thành khi các ca kiểm thử liên quan trong `tests/` chạy đạt.
