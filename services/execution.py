"""M3 Theo dõi WIP, truy xuất và M4 Thu thập dữ liệu công đoạn."""
from db.database import fetch_one, query_df, transaction
from services import planning as P
from services.common import now_str


def stations_in_order(ma_san_pham):
    return list(query_df("SELECT ma_tram FROM quy_trinh WHERE ma_san_pham = ? ORDER BY thu_tu",
                         (ma_san_pham,))["ma_tram"])


def next_station(ma_lsx):
    """Trạm kế tiếp lệnh phải đi qua (None nếu đã qua hết)."""
    lsx = fetch_one("SELECT ma_san_pham FROM lenh_san_xuat WHERE ma_lsx = ?", (ma_lsx,))
    done = set(query_df("SELECT ma_tram FROM nhat_ky_cong_doan WHERE ma_lsx = ? AND thoi_diem_ket_thuc IS NOT NULL",
                        (ma_lsx,))["ma_tram"])
    for s in stations_in_order(lsx["ma_san_pham"]):
        if s not in done:
            return s
    return None


def input_quantity(ma_lsx, ma_tram):
    """Số lượng vào trạm = số đạt của trạm trước; trạm đầu = số lượng kế hoạch."""
    lsx = fetch_one("SELECT ma_san_pham, so_luong_ke_hoach FROM lenh_san_xuat WHERE ma_lsx = ?", (ma_lsx,))
    route = stations_in_order(lsx["ma_san_pham"])
    i = route.index(ma_tram)
    if i == 0:
        return lsx["so_luong_ke_hoach"]
    prev = fetch_one("SELECT so_luong_dat FROM nhat_ky_cong_doan WHERE ma_lsx = ? AND ma_tram = ?"
                     " AND thoi_diem_ket_thuc IS NOT NULL", (ma_lsx, route[i - 1]))
    return prev["so_luong_dat"] if prev else 0


def issue_material(ma_lsx, ts, conn):
    """Xuất vật tư theo BOM, lấy lô nhập trước xuất trước (FIFO). Trả về mã lô nguyên liệu chính."""
    lsx = conn.execute(
        "SELECT ma_san_pham,so_luong_ke_hoach FROM lenh_san_xuat WHERE ma_lsx=?",
        (ma_lsx,),
    ).fetchone()
    if not lsx:
        raise ValueError("Không tìm thấy lệnh sản xuất")
    bom = conn.execute(
        """SELECT ma_vat_tu,dinh_muc,COALESCE(ty_le_hao_hut_pct,0) ty_le
           FROM bom WHERE ma_san_pham=? ORDER BY ma_vat_tu""",
        (lsx["ma_san_pham"],),
    ).fetchall()
    main_lot = None
    for item in bom:
        needed = float(item["dinh_muc"]) * (1 + float(item["ty_le"]) / 100) * int(lsx["so_luong_ke_hoach"])
        remaining = needed
        lots = conn.execute(
            "SELECT ma_lo,so_luong_con FROM lo_vat_tu WHERE ma_vat_tu=? AND so_luong_con>0 "
            "ORDER BY ngay_nhap,ma_lo",
            (item["ma_vat_tu"],),
        ).fetchall()
        for lot in lots:
            if remaining <= 0:
                break
            take = min(remaining, float(lot["so_luong_con"]))
            if take > 0:
                conn.execute("UPDATE lo_vat_tu SET so_luong_con=so_luong_con-? WHERE ma_lo=?",
                             (take, lot["ma_lo"]))
                conn.execute(
                    "INSERT INTO giao_dich_kho(ma_lo,loai,so_luong,ma_lsx,thoi_diem) VALUES(?,?,?,?,?)",
                    (lot["ma_lo"], "xuất", take, ma_lsx, ts),
                )
                if item["ma_vat_tu"] == "VT-001":
                    main_lot = main_lot or lot["ma_lo"]
                remaining -= take
        if remaining > 1e-9:
            raise ValueError(f"Không đủ vật tư {item['ma_vat_tu']}")
    return main_lot


def start_operation(ma_lsx, ma_tram, ts=None, ma_nv=None):
    """Công nhân báo bắt đầu công đoạn. Kiểm tra trạng thái lệnh và thứ tự trạm."""
    ts = ts or now_str()
    lsx = fetch_one("SELECT trang_thai,ma_san_pham FROM lenh_san_xuat WHERE ma_lsx=?", (ma_lsx,))
    if not lsx:
        raise ValueError("Không tìm thấy lệnh sản xuất")
    if lsx["trang_thai"] not in (P.DA_PHAT_LENH, P.DANG_SX):
        raise ValueError("Lệnh chưa phát hoặc đã kết thúc")
    if ma_tram != next_station(ma_lsx):
        raise ValueError("Chưa đến lượt trạm này theo thứ tự quy trình")
    assignment = fetch_one(
        "SELECT ma_nv FROM phan_cong WHERE ma_lsx=? AND ma_tram=?",
        (ma_lsx, ma_tram),
    )
    worker = ma_nv or (assignment["ma_nv"] if assignment else None)
    if not worker:
        raise ValueError("Chưa phân công công nhân")
    with transaction() as conn:
        lot = None
        if ma_tram == "T1":
            lot = issue_material(ma_lsx, ts, conn)
            P.change_status(ma_lsx, P.DANG_SX, ts, conn)
        cur = conn.execute(
            "SELECT trang_thai FROM lenh_san_xuat WHERE ma_lsx=?",
            (ma_lsx,),
        ).fetchone()
        conn.execute(
            "INSERT INTO nhat_ky_cong_doan(ma_lsx,ma_tram,ma_nv,ma_lo_vat_tu,thoi_diem_bat_dau) "
            "VALUES(?,?,?,?,?)",
            (ma_lsx, ma_tram, worker, lot, ts),
        )
        log_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return log_id


def finish_operation(log_id, so_dat, so_loi, ts=None):
    """Báo kết thúc công đoạn; trạm cuối thì cập nhật kết quả lệnh và chuyển Hoàn thành."""
    ts = ts or now_str()
    log = fetch_one("SELECT * FROM nhat_ky_cong_doan WHERE id=?", (log_id,))
    if not log:
        raise ValueError("Không tìm thấy nhật ký công đoạn")
    if log["thoi_diem_ket_thuc"] is not None:
        raise ValueError("Công đoạn đã kết thúc")
    if so_dat < 0 or so_loi < 0:
        raise ValueError("Số lượng không được âm")
    quantity = input_quantity(log["ma_lsx"], log["ma_tram"])
    if so_dat + so_loi > quantity:
        raise ValueError("Số đạt cộng số lỗi vượt số lượng vào trạm")
    with transaction() as conn:
        conn.execute(
            "UPDATE nhat_ky_cong_doan SET thoi_diem_ket_thuc=?,so_luong_dat=?,so_luong_loi=? WHERE id=?",
            (ts, so_dat, so_loi, log_id),
        )
        route = conn.execute(
            "SELECT ma_tram FROM quy_trinh WHERE ma_san_pham=(SELECT ma_san_pham FROM lenh_san_xuat WHERE ma_lsx=?)"
            " ORDER BY thu_tu",
            (log["ma_lsx"],),
        ).fetchall()
        final_station = route[-1]["ma_tram"]
        if log["ma_tram"] == final_station:
            P.change_status(log["ma_lsx"], P.HOAN_THANH, ts, conn)
            total_loi = conn.execute(
                "SELECT COALESCE(SUM(so_luong_loi),0) FROM nhat_ky_cong_doan "
                "WHERE ma_lsx=? AND thoi_diem_ket_thuc IS NOT NULL",
                (log["ma_lsx"],),
            ).fetchone()[0]
            conn.execute(
                "UPDATE lenh_san_xuat SET so_luong_dat=?,so_luong_loi=? WHERE ma_lsx=?",
                (so_dat, total_loi, log["ma_lsx"]),
            )


def wip_status():
    """Bảng WIP: lệnh đang sản xuất, trạm hiện tại, số trạm đã qua."""
    df = query_df(
        """SELECT l.ma_lsx,l.ma_san_pham,l.trang_thai,
                  (SELECT n.ma_tram FROM nhat_ky_cong_doan n
                   WHERE n.ma_lsx=l.ma_lsx AND n.thoi_diem_ket_thuc IS NULL
                   ORDER BY n.id DESC LIMIT 1) AS tram_hien_tai,
                  (SELECT COUNT(*) FROM nhat_ky_cong_doan n
                   WHERE n.ma_lsx=l.ma_lsx AND n.thoi_diem_ket_thuc IS NOT NULL) AS so_tram_da_qua
           FROM lenh_san_xuat l WHERE l.trang_thai=? OR l.trang_thai=?""",
        (P.DA_PHAT_LENH, P.DANG_SX),
    )
    return df


def trace_order(ma_lsx):
    """Hồ sơ phả hệ của một lệnh: công đoạn, lô vật tư, kiểm tra, dừng máy."""
    return query_df(
        """SELECT n.*, k.thoi_diem AS thoi_diem_kiem_tra,k.ma_loi,k.so_luong_loi AS loi_kiem_tra,
                  d.thoi_diem_bat_dau AS dung_may_bat_dau,d.thoi_diem_ket_thuc AS dung_may_ket_thuc
           FROM nhat_ky_cong_doan n
           LEFT JOIN kiem_tra_chat_luong k ON k.ma_lsx=n.ma_lsx AND k.ma_tram=n.ma_tram
           LEFT JOIN dung_may d ON d.ma_lsx=n.ma_lsx
           WHERE n.ma_lsx=? ORDER BY n.id""",
        (ma_lsx,),
    )


def trace_lot(ma_lo):
    """Truy xuất ngược: lô vật tư đã dùng cho những lệnh, đơn hàng, khách hàng nào."""
    return query_df(
        """SELECT DISTINCT l.ma_lsx,d.ma_dh,k.ma_kh,k.ten_kh
           FROM nhat_ky_cong_doan l
           JOIN lenh_san_xuat lsx ON lsx.ma_lsx=l.ma_lsx
           JOIN don_hang d ON d.ma_dh=lsx.ma_dh
           JOIN khach_hang k ON k.ma_kh=d.ma_kh
           WHERE l.ma_lo_vat_tu=? ORDER BY l.ma_lsx""",
        (ma_lo,),
    )
