"""Lớp truy cập dữ liệu (cung cấp sẵn cho sinh viên).

Mọi trang giao diện và hàm nghiệp vụ chỉ đọc, ghi CSDL qua các hàm trong file này.
"""
import os
import sqlite3
from contextlib import contextmanager

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(BASE_DIR, "data", "mes.db")


def db_file():
    """Đường dẫn CSDL; đặt biến môi trường MES_DB để dùng CSDL khác (ví dụ khi kiểm thử)."""
    return os.environ.get("MES_DB", DEFAULT_DB)
SCHEMA_PATH = os.path.join(BASE_DIR, "db", "schema.sql")
CSV_DIR = os.path.join(BASE_DIR, "data", "csv")

# Thứ tự nạp: bảng cha trước bảng con để không vi phạm khóa ngoại.
MASTER_TABLES = [
    "san_pham", "tram", "thiet_bi", "nha_cung_cap", "vat_tu", "lo_vat_tu", "bom", "sop",
    "quy_trinh", "tieu_chuan_kiem_tra", "khach_hang", "don_hang", "ca_lam_viec",
    "nhan_vien", "ky_nang", "ma_loi", "nguyen_nhan_dung",
]
TRANSACTION_TABLES = [
    "giao_dich_kho", "phieu_bao_tri", "dung_may", "kiem_tra_chat_luong", "nhat_ky_cong_doan",
    "phan_cong", "lich_su_trang_thai", "lenh_san_xuat",
]


def get_conn(db_path=None):
    """Mở kết nối SQLite, bật khóa ngoại, trả về hàng dạng dict."""
    conn = sqlite3.connect(db_path or db_file())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(db_path=None):
    """Dùng: with transaction() as conn: ...  Tự commit khi thành công, rollback khi lỗi."""
    conn = get_conn(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path=None):
    """Tạo các bảng theo schema.sql (không xóa dữ liệu cũ)."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        sql = f.read()
    with transaction(db_path) as conn:
        conn.executescript(sql)


def reset_db(db_path=None, csv_dir=None):
    """Xóa file CSDL, tạo lại bảng và nạp toàn bộ CSV dữ liệu nền."""
    path = db_path or db_file()
    if os.path.exists(path):
        os.remove(path)
    init_db(path)
    return load_csv_folder(csv_dir or CSV_DIR, path)


def load_csv_folder(csv_dir=None, db_path=None):
    """Nạp các file <ten_bang>.csv trong thư mục vào bảng cùng tên. Trả về {bảng: số dòng}."""
    csv_dir = csv_dir or CSV_DIR
    result = {}
    with transaction(db_path) as conn:
        for table in MASTER_TABLES:
            path = os.path.join(csv_dir, f"{table}.csv")
            if not os.path.exists(path):
                continue
            df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
            df = df.replace({"": None})
            cols = ", ".join(df.columns)
            marks = ", ".join("?" for _ in df.columns)
            conn.executemany(f"INSERT INTO {table} ({cols}) VALUES ({marks})",
                             df.itertuples(index=False, name=None))
            result[table] = len(df)
    return result


def query_df(sql, params=(), db_path=None):
    """Chạy câu SELECT, trả về pandas DataFrame."""
    conn = get_conn(db_path)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def fetch_one(sql, params=(), db_path=None):
    """Chạy câu SELECT, trả về một dòng dạng dict hoặc None."""
    conn = get_conn(db_path)
    try:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def execute(sql, params=(), db_path=None):
    """Chạy một câu INSERT/UPDATE/DELETE, trả về lastrowid."""
    with transaction(db_path) as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


# ---------- CRUD tổng quát cho trang Dữ liệu nền ----------
def list_rows(table, db_path=None):
    _check_table(table)
    return query_df(f"SELECT * FROM {table}", db_path=db_path)


def insert_row(table, data, db_path=None):
    _check_table(table)
    cols = ", ".join(data)
    marks = ", ".join("?" for _ in data)
    return execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(data.values()), db_path)


def update_row(table, key_col, key, data, db_path=None):
    _check_table(table)
    sets = ", ".join(f"{c} = ?" for c in data)
    execute(f"UPDATE {table} SET {sets} WHERE {key_col} = ?", (*data.values(), key), db_path)


def delete_row(table, key_col, key, db_path=None):
    _check_table(table)
    execute(f"DELETE FROM {table} WHERE {key_col} = ?", (key,), db_path)


def _check_table(table):
    if table not in MASTER_TABLES + TRANSACTION_TABLES:
        raise ValueError(f"Bảng không hợp lệ: {table}")
