import streamlit as st

from ui import require_role, show_error  # noqa: F401

st.set_page_config(page_title="Dashboard", layout="wide")
require_role("Quản đốc")
st.title("M7 Dashboard KPI")

# TODO Buổi 5: xây dựng trang theo thiết kế giao diện (Bước 5, mục 5):
# 1. 4 thẻ st.metric: thành phẩm đạt, tỷ lệ lỗi, giao đúng hạn, lead time trung bình (K.kpi_summary)
# 2. Biểu đồ số lệnh theo trạng thái; biểu đồ OEE theo trạm
# 3. Bảng K.order_results; nút 'Xuất báo cáo về ERP' gọi K.export_erp_report
# Gọi hàm nghiệp vụ qua show_error(...) để lỗi quy tắc hiện thành thông báo.

st.info("Trang đang xây dựng (Buổi 5).")
