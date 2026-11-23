"""M2 Lệnh sản xuất và điều độ."""
import pandas as pd

from db.database import fetch_one, query_df, transaction
from services.common import (due_in_work_minutes, now_str, to_dt, to_str,
                             work_minutes_to_dt)

# ---------- Vòng đời trạng thái lệnh (Bước 3, mục 4.1) ----------
MOI_TAO, DA_LAP_LICH, DA_PHAT_LENH = "Mới tạo", "Đã lập lịch", "Đã phát lệnh"
DANG_SX, TAM_DUNG, HOAN_THANH, DA_DONG, DA_HUY = (
    "Đang sản xuất", "Tạm dừng", "Hoàn thành", "Đã đóng", "Đã hủy")

TRANSITIONS = {
    MOI_TAO: {DA_LAP_LICH, DA_HUY},
    DA_LAP_LICH: {DA_PHAT_LENH, DA_HUY, DA_LAP_LICH},   # được lập lịch lại
    DA_PHAT_LENH: {DANG_SX},
    DANG_SX: {TAM_DUNG, HOAN_THANH},
    TAM_DUNG: {DANG_SX},
    HOAN_THANH: {DA_DONG},
    DA_DONG: set(),
    DA_HUY: set(),
}
RULES = {"FIFO": "Đến trước làm trước (ngày đặt)",
         "EDD": "Hạn giao sớm nhất trước",
         "SPT": "Thời gian gia công ngắn nhất trước"}


def can_transition(cur, new):
    return new in TRANSITIONS.get(cur, set())


def change_status(ma_lsx, new, ts=None, conn=None):
    """Đổi trạng thái lệnh, chặn chuyển trạng thái không hợp lệ, ghi lịch sử."""
    ts = ts or now_str()
    if conn is not None:
        row = conn.execute("SELECT trang_thai FROM lenh_san_xuat WHERE ma_lsx=?", (ma_lsx,)).fetchone()
        if not row:
            raise ValueError("Không tìm thấy lệnh sản xuất")
        cur = row["trang_thai"]
        if not can_transition(cur, new):
            raise ValueError(f"Không thể chuyển trạng thái {cur} -> {new}")
        conn.execute("UPDATE lenh_san_xuat SET trang_thai=? WHERE ma_lsx=?", (new, ma_lsx))
        conn.execute(
            "INSERT INTO lich_su_trang_thai(ma_lsx,tu_trang_thai,den_trang_thai,thoi_diem) VALUES(?,?,?,?)",
            (ma_lsx, cur, new, ts),
        )
        return

    with transaction() as local_conn:
        change_status(ma_lsx, new, ts, local_conn)


def new_order_code(day, conn):
    """Sinh mã LSX-yyMMdd-xx kế tiếp cho ngày day."""
    prefix = f"LSX-{to_dt(day):%y%m%d}-"
    n = conn.execute("SELECT COUNT(*) FROM lenh_san_xuat WHERE ma_lsx LIKE ?", (prefix + "%",)).fetchone()[0]
    return f"{prefix}{n + 1:02d}"


def create_work_order(ma_dh, ts=None):
    """Tạo lệnh sản xuất từ một đơn hàng 'mới'. Trả về mã lệnh."""
    ts = ts or now_str()
    with transaction() as conn:
        dh = conn.execute(
            "SELECT ma_san_pham, so_luong, ngay_dat, trang_thai FROM don_hang WHERE ma_dh=?",
            (ma_dh,),
        ).fetchone()
        if not dh:
            raise ValueError("Không tìm thấy đơn hàng")
        if dh["trang_thai"] != "mới":
            raise ValueError("Đơn hàng đã được lập lệnh")
        ma_lsx = new_order_code(str(to_dt(ts).date()), conn)
        conn.execute(
            """INSERT INTO lenh_san_xuat
               (ma_lsx,ma_dh,ma_san_pham,so_luong_ke_hoach,trang_thai,ngay_tao)
               VALUES(?,?,?,?,?,?)""",
            (ma_lsx, ma_dh, dh["ma_san_pham"], dh["so_luong"], MOI_TAO, ts),
        )
        conn.execute(
            "INSERT INTO lich_su_trang_thai(ma_lsx,tu_trang_thai,den_trang_thai,thoi_diem) VALUES(?,?,?,?)",
            (ma_lsx, None, MOI_TAO, ts),
        )
        conn.execute("UPDATE don_hang SET trang_thai='đã lập lệnh' WHERE ma_dh=?", (ma_dh,))
        return ma_lsx


def get_routing(ma_san_pham):
    return query_df("SELECT * FROM quy_trinh WHERE ma_san_pham = ? ORDER BY thu_tu", (ma_san_pham,))


def material_requirements(ma_lsx):
    """Nhu cầu vật tư của lệnh = định mức x (1 + hao hụt) x số lượng; so với tồn kho."""
    lsx = fetch_one("SELECT ma_san_pham,so_luong_ke_hoach FROM lenh_san_xuat WHERE ma_lsx=?", (ma_lsx,))
    if not lsx:
        raise ValueError("Không tìm thấy lệnh sản xuất")
    df = query_df(
        """SELECT b.ma_vat_tu, b.don_vi,
                  b.dinh_muc * (1 + COALESCE(b.ty_le_hao_hut_pct,0)/100.0) * ? AS can,
                  COALESCE(SUM(l.so_luong_con),0) AS ton
           FROM bom b
           LEFT JOIN lo_vat_tu l ON l.ma_vat_tu=b.ma_vat_tu
           WHERE b.ma_san_pham=? GROUP BY b.ma_vat_tu,b.don_vi,b.dinh_muc,b.ty_le_hao_hut_pct""",
        (lsx["so_luong_ke_hoach"], lsx["ma_san_pham"]),
    )
    if not df.empty:
        df["du"] = df["ton"] - df["can"]
    return df


def schedule_orders(rule, start_day, orders=None):
    """Lập lịch flow shop 5 trạm, chuyển cả lô giữa các trạm.

    rule: FIFO | EDD | SPT. orders: DataFrame lệnh cần xếp (mặc định: lệnh Mới tạo/Đã lập lịch).
    Trả về (plan, summary): plan = mỗi lệnh x mỗi trạm có bat_dau/ket_thuc;
    summary = mỗi lệnh có thời điểm hoàn thành, hạn giao, số phút trễ.
    """
    if rule not in RULES:
        raise ValueError("Quy tắc lập lịch không hợp lệ")
    if orders is None:
        orders = query_df(
            """SELECT l.*, d.ngay_giao, d.ngay_dat FROM lenh_san_xuat l
               JOIN don_hang d ON d.ma_dh=l.ma_dh
               WHERE l.trang_thai IN (?,?)""",
            (MOI_TAO, DA_LAP_LICH),
        )
    else:
        missing = {"ngay_giao", "ngay_dat"} - set(orders.columns)
        if missing:
            orders = orders.merge(
                query_df("SELECT ma_dh,ngay_giao,ngay_dat FROM don_hang"),
                on="ma_dh",
                how="left",
            )

    if rule == "FIFO":
        ordered = orders.sort_values(["ngay_dat", "ma_lsx"])
    elif rule == "EDD":
        ordered = orders.sort_values(["ngay_giao", "ma_lsx"])
    else:
        totals = {}
        for row in orders.itertuples(index=False):
            code = getattr(row, "ma_lsx")
            route = query_df(
                "SELECT thoi_gian_chuan_phut, thoi_gian_chuan_bi_phut FROM quy_trinh WHERE ma_san_pham=?",
                (getattr(row, "ma_san_pham"),),
            )
            totals[code] = float((route["thoi_gian_chuan_phut"] + route["thoi_gian_chuan_bi_phut"]).sum())
        ordered = orders.copy()
        ordered["_tong"] = ordered["ma_lsx"].map(totals)
        ordered = ordered.sort_values(["_tong", "ma_lsx"])

    station_ready = {}
    plan_rows = []
    summary_rows = []
    for _, order in ordered.iterrows():
        route = query_df(
            "SELECT ma_tram,thoi_gian_chuan_phut,thoi_gian_chuan_bi_phut FROM quy_trinh "
            "WHERE ma_san_pham=? ORDER BY thu_tu",
            (order["ma_san_pham"],),
        )
        prev_end = 0
        for _, op in route.iterrows():
            duration = float(op["thoi_gian_chuan_phut"] + op["thoi_gian_chuan_bi_phut"])
            station = op["ma_tram"]
            start_min = max(prev_end, station_ready.get(station, 0))
            end_min = start_min + duration * float(order["so_luong_ke_hoach"])
            station_ready[station] = end_min
            prev_end = end_min
            plan_rows.append({
                "ma_lsx": order["ma_lsx"],
                "ma_tram": station,
                "start_min": start_min,
                "end_min": end_min,
                "bat_dau_kh": to_str(work_minutes_to_dt(start_day, start_min)),
                "ket_thuc_kh": to_str(work_minutes_to_dt(start_day, end_min)),
            })
        due = due_in_work_minutes(start_day, order["ngay_giao"])
        summary_rows.append({
            "ma_lsx": order["ma_lsx"],
            "ket_thuc": prev_end,
            "ngay_giao": order["ngay_giao"],
            "tre_phut": max(0, prev_end - due),
        })
    plan = pd.DataFrame(plan_rows)
    summary = pd.DataFrame(summary_rows)
    return plan, summary


def compare_rules(start_day):
    """So sánh 3 quy tắc: makespan, tổng phút trễ, số lệnh trễ."""
    rows = []
    for rule in ("FIFO", "EDD", "SPT"):
        _, summary = schedule_orders(rule, start_day)
        rows.append({
            "quy_tac": rule,
            "makespan": float(summary["ket_thuc"].max()) if not summary.empty else 0,
            "tong_tre_phut": float(summary["tre_phut"].sum()) if not summary.empty else 0,
            "so_lenh_tre": int((summary["tre_phut"] > 0).sum()) if not summary.empty else 0,
        })
    return pd.DataFrame(rows)


def save_schedule(plan):
    """Ghi thứ tự ưu tiên và thời gian kế hoạch vào lệnh, chuyển sang Đã lập lịch."""
    if plan.empty:
        raise ValueError("Lịch trống")
    with transaction() as conn:
        priority = 1
        for ma_lsx in plan["ma_lsx"].drop_duplicates():
            rows = plan[plan["ma_lsx"] == ma_lsx]
            first = rows.sort_values("start_min").iloc[0]
            last = rows.sort_values("end_min").iloc[-1]
            cur = conn.execute("SELECT trang_thai FROM lenh_san_xuat WHERE ma_lsx=?", (ma_lsx,)).fetchone()
            if not cur:
                raise ValueError("Không tìm thấy lệnh sản xuất")
            if cur["trang_thai"] not in (MOI_TAO, DA_LAP_LICH):
                raise ValueError("Chỉ lập lịch cho lệnh Mới tạo hoặc Đã lập lịch")
            conn.execute(
                "UPDATE lenh_san_xuat SET bat_dau_kh=?,ket_thuc_kh=?,uu_tien=?,trang_thai=? WHERE ma_lsx=?",
                (first["bat_dau_kh"], last["ket_thuc_kh"], priority, DA_LAP_LICH, ma_lsx),
            )
            conn.execute(
                "INSERT INTO lich_su_trang_thai(ma_lsx,tu_trang_thai,den_trang_thai,thoi_diem) "
                "VALUES(?,?,?,?)",
                (ma_lsx, cur["trang_thai"], DA_LAP_LICH, now_str()),
            )
            priority += 1


def eligible_workers(ma_tram, ma_ca=None):
    sql = """SELECT n.ma_nv, n.ho_ten, n.ma_ca, k.muc_thanh_thao FROM nhan_vien n
             JOIN ky_nang k ON k.ma_nv = n.ma_nv WHERE k.ma_tram = ? AND n.vai_tro = 'công nhân'"""
    params = [ma_tram]
    if ma_ca:
        sql += " AND n.ma_ca = ?"
        params.append(ma_ca)
    return query_df(sql + " ORDER BY k.muc_thanh_thao DESC, n.ma_nv", tuple(params))


def assign_worker(ma_lsx, ma_tram, ma_nv, ma_ca, ngay):
    """Phân công công nhân cho một công đoạn; chặn người không có kỹ năng ở trạm đó."""
    with transaction() as conn:
        lsx = conn.execute("SELECT trang_thai FROM lenh_san_xuat WHERE ma_lsx=?", (ma_lsx,)).fetchone()
        if not lsx:
            raise ValueError("Không tìm thấy lệnh sản xuất")
        skill = conn.execute(
            "SELECT 1 FROM ky_nang k JOIN nhan_vien n ON n.ma_nv=k.ma_nv "
            "WHERE k.ma_nv=? AND k.ma_tram=? AND n.ma_ca=?",
            (ma_nv, ma_tram, ma_ca),
        ).fetchone()
        if not skill:
            raise ValueError("Nhân viên không có kỹ năng ở trạm hoặc không thuộc ca")
        conn.execute(
            "INSERT INTO phan_cong(ma_lsx,ma_tram,ma_nv,ma_ca,ngay) VALUES(?,?,?,?,?) "
            "ON CONFLICT(ma_lsx,ma_tram) DO UPDATE SET ma_nv=excluded.ma_nv,ma_ca=excluded.ma_ca,ngay=excluded.ngay",
            (ma_lsx, ma_tram, ma_nv, ma_ca, ngay),
        )


def auto_assign(ma_lsx, ma_ca, ngay):
    """Gán cho mỗi trạm công nhân thành thạo nhất trong ca."""
    lsx = fetch_one("SELECT ma_san_pham FROM lenh_san_xuat WHERE ma_lsx=?", (ma_lsx,))
    if not lsx:
        raise ValueError("Không tìm thấy lệnh sản xuất")
    route = get_routing(lsx["ma_san_pham"])
    for station in route["ma_tram"]:
        candidates = eligible_workers(station, ma_ca)
        if candidates.empty:
            raise ValueError(f"Không có nhân viên có kỹ năng trạm {station} trong ca {ma_ca}")
        worker = candidates.iloc[0]["ma_nv"]
        assign_worker(ma_lsx, station, worker, ma_ca, ngay)


def release_order(ma_lsx, ts=None):
    """Phát lệnh xuống trạm: đủ vật tư và đủ phân công 5 trạm mới được phát."""
    ts = ts or now_str()
    lsx = fetch_one("SELECT trang_thai,ma_san_pham FROM lenh_san_xuat WHERE ma_lsx=?", (ma_lsx,))
    if not lsx:
        raise ValueError("Không tìm thấy lệnh sản xuất")
    if lsx["trang_thai"] != DA_LAP_LICH:
        raise ValueError("Lệnh chưa ở trạng thái Đã lập lịch")
    route = get_routing(lsx["ma_san_pham"])
    if len(route) != 5:
        raise ValueError("Sản phẩm phải có đủ 5 trạm")
    assigned = query_df("SELECT ma_tram FROM phan_cong WHERE ma_lsx=?", (ma_lsx,))
    if set(route["ma_tram"]) - set(assigned["ma_tram"]):
        raise ValueError("Chưa phân công đủ 5 trạm")
    req = material_requirements(ma_lsx)
    if not req.empty and (req["du"] < 0).any():
        raise ValueError("Không đủ vật tư")
    change_status(ma_lsx, DA_PHAT_LENH, ts)
