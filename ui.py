"""Thành phần giao diện dùng chung: chọn vai trò, kiểm tra quyền, khởi tạo CSDL."""
import os

import streamlit as st

from db import database as db

ROLES = ["Quản trị hệ thống", "Kế hoạch viên", "Tổ trưởng ca", "Công nhân vận hành",
         "Nhân viên QC", "Quản đốc"]


def sidebar():
    st.sidebar.selectbox("Vai trò đăng nhập", ROLES, key="vai_tro")
    if not os.path.exists(db.db_file()):
        db.reset_db()
    if st.session_state.get("vai_tro") == "Quản trị hệ thống":
        if st.sidebar.button("Khởi tạo lại CSDL từ CSV"):
            n = db.reset_db()
            st.sidebar.success(f"Đã nạp {sum(n.values())} dòng vào {len(n)} bảng")


def require_role(*allowed):
    """Dừng trang nếu vai trò hiện tại không được phép xem."""
    sidebar()
    role = st.session_state.get("vai_tro")
    if role not in allowed and role != "Quản đốc":
        st.warning(f"Trang này dành cho: {', '.join(allowed)}. Hãy đổi vai trò ở thanh bên.")
        st.stop()
    return role


def show_error(fn, *args, **kwargs):
    """Gọi hàm nghiệp vụ; nếu vi phạm quy tắc thì hiện thông báo thay vì làm hỏng trang.

    Trả về kết quả của hàm (True nếu hàm không trả gì) khi thành công, None khi có lỗi.
    """
    try:
        res = fn(*args, **kwargs)
        return True if res is None else res
    except ValueError as e:
        st.error(str(e))
    except Exception as e:  # lỗi CSDL, khóa ngoại...
        st.error(f"Lỗi dữ liệu: {e}")
