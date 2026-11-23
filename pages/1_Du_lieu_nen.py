import streamlit as st

from db import database as db
from services import master_data as M
from ui import require_role, show_error

st.set_page_config(page_title="Dữ liệu nền", layout="wide")
require_role("Quản trị hệ thống")
st.title("M1 Dữ liệu nền")

table = st.selectbox("Bảng dữ liệu", db.MASTER_TABLES)
df = db.list_rows(table)
st.dataframe(df, width="stretch", hide_index=True)

with st.expander("Thêm một dòng"):
    with st.form("them"):
        values = {c: st.text_input(c) for c in df.columns}
        if st.form_submit_button("Lưu"):
            data = {k: (v if v != "" else None) for k, v in values.items()}
            if show_error(db.insert_row, table, data) is not None:
                st.success("Đã thêm")
                st.rerun()

with st.expander("Xóa một dòng"):
    key_col = df.columns[0]
    key = st.selectbox(f"Chọn {key_col}", df[key_col].astype(str).tolist() if not df.empty else [])
    if st.button("Xóa") and key:
        show_error(db.delete_row, table, key_col, key)
        st.rerun()

st.subheader("Kiểm tra dữ liệu nền")
# TODO Buổi 2: viết M.validate_master_data và M.get_stock trong services/master_data.py
try:
    issues = M.validate_master_data()
except NotImplementedError:
    st.info("Chưa viết validate_master_data (Buổi 2)")
    st.stop()
if issues.empty:
    st.success("Không phát hiện vấn đề")
else:
    st.dataframe(issues, width="stretch", hide_index=True)
st.subheader("Tồn kho vật tư")
st.dataframe(M.get_stock(), width="stretch", hide_index=True)
