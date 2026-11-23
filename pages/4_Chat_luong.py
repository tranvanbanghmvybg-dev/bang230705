import streamlit as st

from ui import require_role, show_error  # noqa: F401

st.set_page_config(page_title="Chất lượng", layout="wide")
require_role("Nhân viên QC")
st.title("M5 Quản lý chất lượng")

# TODO Buổi 4: xây dựng trang theo thiết kế giao diện (Bước 5, mục 5):
# 1. Form ghi kết quả kiểm tra: lệnh, trạm, số mẫu, số đạt, mã lỗi (lọc theo trạm), số lỗi -> Q.record_inspection
# 2. Biểu đồ Pareto: cột số lỗi + đường tỷ lệ tích lũy (Q.pareto_defects)
# 3. Bảng Q.defect_rate_by_station và cảnh báo đỏ từ Q.quality_alerts
# Gọi hàm nghiệp vụ qua show_error(...) để lỗi quy tắc hiện thành thông báo.

st.info("Trang đang xây dựng (Buổi 4).")
