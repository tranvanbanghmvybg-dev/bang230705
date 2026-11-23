"""Trang chủ phần mềm MES giả định. Chạy: streamlit run app.py"""
import streamlit as st

from services import kpi
from ui import sidebar

st.set_page_config(page_title="MES giả định", layout="wide")
sidebar()
st.title("Phần mềm MES giả định: xưởng gia công trục bậc 5 công đoạn")
st.caption("Học phần ME6182. Chọn vai trò ở thanh bên, sau đó mở trang chức năng.")
try:
    k = kpi.kpi_summary()
    c1, c2, c3 = st.columns(3)
    c1.metric("Thành phẩm đạt", k["thanh_pham_dat"])
    c2.metric("Tỷ lệ lỗi", f"{k['ty_le_loi']:.1%}")
    c3.metric("Số lệnh", sum(k["lenh_theo_trang_thai"].values()))
except NotImplementedError:
    st.info("Các chỉ số sẽ hiện khi nhóm hoàn thành kpi_summary (Buổi 5).")
st.markdown("""
| Trang | Module | Vai trò chính |
|---|---|---|
| 1 Dữ liệu nền | M1 | Quản trị hệ thống |
| 2 Điều độ | M2 | Kế hoạch viên, Tổ trưởng ca |
| 3 Thực thi, WIP | M3, M4 | Tổ trưởng ca, Công nhân vận hành |
| 4 Chất lượng | M5 | Nhân viên QC |
| 5 Thiết bị, OEE | M6 | Tổ trưởng ca |
| 6 Dashboard | M7 | Quản đốc |
""")
