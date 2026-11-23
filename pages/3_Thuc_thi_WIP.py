import streamlit as st

from ui import require_role, show_error  # noqa: F401

st.set_page_config(page_title="Thực thi, WIP", layout="wide")
require_role("Tổ trưởng ca", "Công nhân vận hành")
st.title("M3 Theo dõi WIP, truy xuất và M4 Thu thập dữ liệu")

# TODO Buổi 4: xây dựng trang theo thiết kế giao diện (Bước 5, mục 5):
# 1. Ô thời điểm bắt đầu + hạt giống; nút 'Chạy mô phỏng' gọi S.simulate_released (from simulator import station_sim as S)
# 2. Bảng X.wip_status; chọn lệnh, hiện trạm kế tiếp X.next_station và số lượng vào X.input_quantity
# 3. Nút 'Bắt đầu' (X.start_operation) hoặc form số đạt, số lỗi + nút 'Kết thúc' (X.finish_operation)
# 4. Hai tab truy xuất: theo lệnh (X.trace_order) và theo lô vật tư (X.trace_lot)
# Gọi hàm nghiệp vụ qua show_error(...) để lỗi quy tắc hiện thành thông báo.

st.info("Trang đang xây dựng (Buổi 4).")
