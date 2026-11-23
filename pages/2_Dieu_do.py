import streamlit as st

from ui import require_role, show_error  # noqa: F401

st.set_page_config(page_title="Điều độ", layout="wide")
require_role("Kế hoạch viên", "Tổ trưởng ca")
st.title("M2 Lệnh sản xuất và điều độ")

# TODO Buổi 3: xây dựng trang theo thiết kế giao diện (Bước 5, mục 5):
# 1. Bảng đơn hàng trạng thái 'mới' + nút 'Tạo lệnh' gọi P.create_work_order
# 2. Chọn ngày bắt đầu; bảng so sánh quy tắc P.compare_rules
# 3. st.radio chọn FIFO/EDD/SPT; P.schedule_orders; biểu đồ Gantt plotly px.timeline (y = trạm, màu = lệnh)
# 4. Nút 'Lưu lịch' gọi P.save_schedule
# 5. Chọn lệnh Đã lập lịch: bảng P.material_requirements, chọn ca, nút 'Tự phân công' (P.auto_assign), nút 'Phát lệnh' (P.release_order)
# Gọi hàm nghiệp vụ qua show_error(...) để lỗi quy tắc hiện thành thông báo.

st.info("Trang đang xây dựng (Buổi 3).")
