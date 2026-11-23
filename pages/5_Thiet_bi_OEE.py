import streamlit as st

from ui import require_role, show_error  # noqa: F401

st.set_page_config(page_title="Thiết bị, OEE", layout="wide")
require_role("Tổ trưởng ca")
st.title("M6 Thiết bị, dừng máy và OEE")

# TODO Buổi 5: xây dựng trang theo thiết kế giao diện (Bước 5, mục 5):
# 1. Form ghi dừng máy: thiết bị, bắt đầu, kết thúc, nguyên nhân -> E.record_downtime
# 2. Khoảng thời gian mặc định E.production_window; biểu đồ cột nhóm A, P, Q, OEE theo trạm (E.oee_all)
# 3. Bảng E.downtime_summary
# Gọi hàm nghiệp vụ qua show_error(...) để lỗi quy tắc hiện thành thông báo.

st.info("Trang đang xây dựng (Buổi 5).")
