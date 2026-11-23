"""M5 Quản lý chất lượng."""
from db.database import execute, query_df
from services.common import now_str


def record_inspection(ma_lsx, ma_tram, so_mau, so_dat, ma_loi=None, so_luong_loi=0, ma_nv_qc=None, ts=None):
    """Ghi kết quả kiểm tra; số đạt + số lỗi không vượt số mẫu; có lỗi thì bắt buộc mã lỗi."""
    if so_mau < 0 or so_dat < 0 or so_luong_loi < 0:
        raise ValueError("Số lượng không được âm")
    if so_dat + so_luong_loi > so_mau:
        raise ValueError("Số đạt cộng số lỗi không được vượt số mẫu")
    if so_luong_loi > 0 and not ma_loi:
        raise ValueError("Có lỗi phải có mã lỗi")
    ts = ts or now_str()
    execute(
        """INSERT INTO kiem_tra_chat_luong
           (ma_lsx,ma_tram,thoi_diem,so_mau,so_dat,ma_loi,so_luong_loi,ma_nv_qc)
           VALUES(?,?,?,?,?,?,?,?)""",
        (ma_lsx, ma_tram, ts, so_mau, so_dat, ma_loi, so_luong_loi, ma_nv_qc),
    )


def pareto_defects():
    """Pareto lỗi: số lượng theo mã lỗi, sắp giảm dần, kèm tỷ lệ tích lũy."""
    df = query_df(
        """SELECT ma_loi,COALESCE(SUM(so_luong_loi),0) AS so_luong
           FROM kiem_tra_chat_luong WHERE ma_loi IS NOT NULL
           GROUP BY ma_loi ORDER BY so_luong DESC,ma_loi"""
    )
    if not df.empty:
        df["ty_le_tich_luy"] = df["so_luong"].cumsum() / df["so_luong"].sum()
    return df


def defect_rate_by_station():
    """Tỷ lệ lỗi theo trạm = số lỗi / (số đạt + số lỗi) từ nhật ký công đoạn."""
    df = query_df(
        """SELECT ma_tram,
                  COALESCE(SUM(so_luong_loi),0) AS so_loi,
                  COALESCE(SUM(so_luong_dat),0) AS so_dat
           FROM nhat_ky_cong_doan WHERE thoi_diem_ket_thuc IS NOT NULL
           GROUP BY ma_tram ORDER BY ma_tram"""
    )
    if not df.empty:
        tong = df["so_dat"] + df["so_loi"]
        df["ty_le_loi"] = df["so_loi"].div(tong.where(tong != 0))
        df["ty_le_loi"] = df["ty_le_loi"].fillna(0)
    return df


def quality_alerts(threshold=0.05):
    """Trạm có tỷ lệ lỗi vượt ngưỡng (mặc định 5%, Bước 3 mục 5.5)."""
    df = defect_rate_by_station()
    return df[df["ty_le_loi"] > threshold].copy() if not df.empty else df
