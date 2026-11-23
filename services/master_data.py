"""M1 Dữ liệu nền: kiểm tra tính hợp lệ và tồn kho."""
import pandas as pd

from db.database import query_df


def get_stock():
    """Tồn kho hiện tại của từng vật tư = tổng so_luong_con các lô; đánh dấu dưới mức tối thiểu."""
    df = query_df(
        """SELECT v.ma_vat_tu,v.ten_vat_tu,v.don_vi,v.ton_toi_thieu,
                  COALESCE(SUM(l.so_luong_con),0) AS ton
           FROM vat_tu v LEFT JOIN lo_vat_tu l ON l.ma_vat_tu=v.ma_vat_tu
           GROUP BY v.ma_vat_tu,v.ten_vat_tu,v.don_vi,v.ton_toi_thieu
           ORDER BY v.ma_vat_tu"""
    )
    if not df.empty:
        df["duoi_muc_toi_thieu"] = df["ton"] < df["ton_toi_thieu"]
    return df


def validate_master_data():
    """Kiểm tra logic nghiệp vụ mà khóa ngoại không bắt được. Trả về DataFrame các vấn đề."""
    issues = []
    bad_routes = query_df(
        """SELECT sp.ma_san_pham,COUNT(q.ma_tram) AS so_tram
           FROM san_pham sp LEFT JOIN quy_trinh q ON q.ma_san_pham=sp.ma_san_pham
           GROUP BY sp.ma_san_pham HAVING COUNT(q.ma_tram)<>5"""
    )
    for row in bad_routes.itertuples(index=False):
        issues.append({"loai": "quy_trình", "ma": row.ma_san_pham,
                       "noi_dung": f"Sản phẩm có {row.so_tram} trạm, yêu cầu 5 trạm"})
    bad_dates = query_df(
        "SELECT ma_dh FROM don_hang WHERE ngay_giao < ngay_dat"
    )
    for row in bad_dates.itertuples(index=False):
        issues.append({"loai": "đơn hàng", "ma": row.ma_dh, "noi_dung": "Ngày giao trước ngày đặt"})
    return pd.DataFrame(issues, columns=["loai", "ma", "noi_dung"]) if issues else pd.DataFrame(
        columns=["loai", "ma", "noi_dung"]
    )
