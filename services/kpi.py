"""M7 Báo cáo KPI và xuất báo cáo về ERP."""
from db.database import fetch_one, query_df
from services import planning as P
from services.common import minutes_between, to_dt


def order_results():
    """Mỗi lệnh đã xong: thời điểm bắt đầu T1, kết thúc T5, lead time, đúng hạn hay không."""
    df = query_df(
        """SELECT l.ma_lsx,l.ma_dh,d.ngay_giao,l.so_luong_ke_hoach,l.so_luong_dat,l.so_luong_loi,
                  (SELECT MIN(n.thoi_diem_bat_dau) FROM nhat_ky_cong_doan n
                   WHERE n.ma_lsx=l.ma_lsx) AS thoi_diem_bat_dau,
                  (SELECT MAX(n.thoi_diem_ket_thuc) FROM nhat_ky_cong_doan n
                   WHERE n.ma_lsx=l.ma_lsx) AS thoi_diem_ket_thuc
           FROM lenh_san_xuat l JOIN don_hang d ON d.ma_dh=l.ma_dh
           WHERE l.trang_thai=? ORDER BY l.ma_lsx""",
        (P.HOAN_THANH,),
    )
    if not df.empty:
        df["lead_time_phut"] = df.apply(
            lambda r: minutes_between(r["thoi_diem_bat_dau"], r["thoi_diem_ket_thuc"]),
            axis=1,
        )
        df["dung_han"] = df.apply(
            lambda r: to_dt(r["thoi_diem_ket_thuc"]).date() <= to_dt(r["ngay_giao"]).date(),
            axis=1,
        )
    return df


def kpi_summary():
    """Các chỉ số tổng hợp cho dashboard."""
    lsx = query_df("SELECT trang_thai,so_luong_dat,so_luong_loi FROM lenh_san_xuat")
    thanh_pham_dat = int(lsx["so_luong_dat"].sum()) if not lsx.empty else 0
    tong = int(lsx["so_luong_dat"].sum() + lsx["so_luong_loi"].sum()) if not lsx.empty else 0
    ty_le_loi = lsx["so_luong_loi"].sum() / tong if tong else 0
    lenh_theo_trang_thai = (
        lsx["trang_thai"].value_counts().to_dict() if not lsx.empty
        else {}
    )
    results = order_results()
    giao_dung_han = (
        float(results["dung_han"].mean()) if not results.empty
        else 0
    )
    lead = (
        float(results["lead_time_phut"].mean()) if not results.empty
        else 0
    )
    return {
        "thanh_pham_dat": thanh_pham_dat,
        "ty_le_loi": ty_le_loi,
        "giao_dung_han": giao_dung_han,
        "lead_time_trung_binh": lead,
        "lenh_theo_trang_thai": lenh_theo_trang_thai,
    }


def export_erp_report(path):
    """Xuất báo cáo sản lượng, tiêu hao về ERP giả lập (CSV UTF-8)."""
    df = query_df(
        """SELECT g.ma_lsx,g.ma_lo,v.ma_vat_tu,g.loai,g.so_luong,g.thoi_diem
           FROM giao_dich_kho g JOIN lo_vat_tu l ON l.ma_lo=g.ma_lo
           JOIN vat_tu v ON v.ma_vat_tu=l.ma_vat_tu
           WHERE g.loai='xuất' ORDER BY g.thoi_diem,g.ma_lsx,g.ma_lo"""
    )
    df.to_csv(path, index=False, encoding="utf-8")
