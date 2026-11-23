"""M6 Thiết bị, dừng máy và OEE."""
import pandas as pd

from db.database import execute, query_df
from services.common import minutes_between, to_dt


def record_downtime(ma_tb, bat_dau, ket_thuc, ma_nguyen_nhan, ma_lsx=None, ghi_chu=None):
    if minutes_between(bat_dau, ket_thuc) < 0:
        raise ValueError("Thời gian kết thúc dừng máy trước thời điểm bắt đầu")
    return execute(
        """INSERT INTO dung_may(ma_tb,ma_lsx,thoi_diem_bat_dau,thoi_diem_ket_thuc,ma_nguyen_nhan,ghi_chu)
           VALUES(?,?,?,?,?,?)""",
        (ma_tb, ma_lsx, bat_dau, ket_thuc, ma_nguyen_nhan, ghi_chu),
    )


def downtime_summary():
    """Tổng phút dừng theo trạm và nguyên nhân."""
    return query_df(
        """SELECT t.ma_tram,t.ten_tram,d.ma_nguyen_nhan,n.ten AS nguyen_nhan,
                  SUM((julianday(d.thoi_diem_ket_thuc)-julianday(d.thoi_diem_bat_dau))*1440) AS tong_phut
           FROM dung_may d
           JOIN thiet_bi tb ON tb.ma_tb=d.ma_tb
           JOIN tram t ON t.ma_tram=tb.ma_tram
           JOIN nguyen_nhan_dung n ON n.ma_nguyen_nhan=d.ma_nguyen_nhan
           GROUP BY t.ma_tram,t.ten_tram,d.ma_nguyen_nhan,n.ten
           ORDER BY tong_phut DESC"""
    )


def _overlap(a0, a1, b0, b1):
    s, e = max(to_dt(a0), to_dt(b0)), min(to_dt(a1), to_dt(b1))
    return max(0.0, (e - s).total_seconds() / 60)


def calc_oee(ma_tram, tu, den):
    """OEE = A x P x Q của một trạm trong khoảng [tu, den].

    Thời gian kế hoạch = (den - tu) trừ bảo trì định kỳ (nhóm 'kế hoạch').
    A: trừ dừng máy ảnh hưởng 'khả dụng'. P: thời gian chuẩn x sản lượng / thời gian chạy.
    Q: số đạt / tổng số sản xuất.
    """
    planned = minutes_between(tu, den)
    planned_downtime = query_df(
        """SELECT COALESCE(SUM((julianday(
               CASE WHEN d.thoi_diem_ket_thuc < ? THEN d.thoi_diem_ket_thuc ELSE ? END)
               - julianday(CASE WHEN d.thoi_diem_bat_dau > ? THEN d.thoi_diem_bat_dau ELSE ? END))*1440),0) AS phut
           FROM dung_may d JOIN thiet_bi tb ON tb.ma_tb=d.ma_tb
           JOIN nguyen_nhan_dung n ON n.ma_nguyen_nhan=d.ma_nguyen_nhan
           WHERE tb.ma_tram=? AND n.nhom='kế hoạch'
             AND d.thoi_diem_bat_dau<? AND d.thoi_diem_ket_thuc>?""",
        (den, den, tu, tu, ma_tram, den, tu),
    ).iloc[0]["phut"]
    avail_time = max(0, planned - float(planned_downtime))

    available_downtime = query_df(
        """SELECT d.thoi_diem_bat_dau,d.thoi_diem_ket_thuc,n.anh_huong_oee
           FROM dung_may d JOIN thiet_bi tb ON tb.ma_tb=d.ma_tb
           JOIN nguyen_nhan_dung n ON n.ma_nguyen_nhan=d.ma_nguyen_nhan
           WHERE tb.ma_tram=? AND d.thoi_diem_bat_dau<? AND d.thoi_diem_ket_thuc>?""",
        (ma_tram, den, tu),
    )
    unavailable = sum(
        _overlap(tu, den, row.thoi_diem_bat_dau, row.thoi_diem_ket_thuc)
        for row in available_downtime.itertuples(index=False)
        if row.anh_huong_oee == "khả dụng"
    )
    runtime = max(0, avail_time - unavailable)
    A = runtime / avail_time if avail_time > 0 else 0

    logs = query_df(
        """SELECT n.thoi_diem_bat_dau,n.thoi_diem_ket_thuc,
                  n.so_luong_dat,n.so_luong_loi,n.ma_tram
           FROM nhat_ky_cong_doan n
           WHERE n.ma_tram=? AND n.thoi_diem_bat_dau<? AND n.thoi_diem_ket_thuc>?""",
        (ma_tram, den, tu),
    )
    standard = query_df(
        "SELECT thoi_gian_chuan_phut FROM quy_trinh WHERE ma_tram=?",
        (ma_tram,),
    )
    standard_min = float(standard["thoi_gian_chuan_phut"].mean()) if not standard.empty else 0
    qty = int(logs["so_luong_dat"].fillna(0).sum()) if not logs.empty else 0
    loi = int(logs["so_luong_loi"].fillna(0).sum()) if not logs.empty else 0
    total = qty + loi
    P = (standard_min * total / runtime) if runtime > 0 and standard_min > 0 else 0
    Q = qty / total if total > 0 else 0
    return {"ma_tram": ma_tram, "A": A, "P": P, "Q": Q, "OEE": A * P * Q}


def oee_all(tu, den):
    stations = query_df("SELECT ma_tram FROM tram ORDER BY thu_tu_tren_day_chuyen")["ma_tram"]
    return pd.DataFrame([calc_oee(s, tu, den) for s in stations])


def production_window():
    """Khoảng thời gian từ lúc trạm đầu bắt đầu đến lúc công đoạn cuối kết thúc (mặc định để tính OEE)."""
    r = query_df("SELECT MIN(thoi_diem_bat_dau) a, MAX(thoi_diem_ket_thuc) b FROM nhat_ky_cong_doan")
    return (r.a[0], r.b[0]) if r.a[0] else (None, None)
