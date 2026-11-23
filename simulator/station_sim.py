"""Bộ mô phỏng 5 trạm (tầng 2–1): sinh sự kiện bắt đầu, kết thúc, lỗi, dừng máy cho lệnh đã phát.

Mô phỏng chuyển cả lô qua từng trạm; thời gian thực tế = thời gian chuẩn x hệ số ngẫu nhiên 1,00–1,12.
"""
import random
from datetime import timedelta

from db.database import fetch_one, query_df
from services import equipment as E, execution as X, planning as P, quality as Qy
from services.common import to_dt, to_str

DEFECT_PROB = {"T1": 0.01, "T2": 0.03, "T3": 0.02, "T4": 0.02, "T5": 0.01}
BREAKDOWN_PROB = 0.25
STOP_CAUSES = ["D-01", "D-02", "D-03", "D-04"]


def station_free_at(ma_tram):
    r = fetch_one("SELECT MAX(thoi_diem_ket_thuc) t FROM nhat_ky_cong_doan WHERE ma_tram = ?", (ma_tram,))
    return to_dt(r["t"]) if r and r["t"] else None


def simulate_order(ma_lsx, start_ts, seed=None):
    """Chạy lệnh qua toàn bộ các trạm. Trả về danh sách sự kiện đã sinh."""
    rnd = random.Random(seed)
    lsx = fetch_one("SELECT * FROM lenh_san_xuat WHERE ma_lsx = ?", (ma_lsx,))
    if lsx["trang_thai"] not in (P.DA_PHAT_LENH, P.DANG_SX):
        raise ValueError(f"Lệnh {ma_lsx} chưa được phát lệnh")
    route = P.get_routing(lsx["ma_san_pham"]).set_index("ma_tram")
    t = to_dt(start_ts)
    events = []
    while (s := X.next_station(ma_lsx)) is not None:
        free = station_free_at(s)
        st = max(t, free) if free else t
        qty = X.input_quantity(ma_lsx, s)
        log_id = X.start_operation(ma_lsx, s, to_str(st))
        dur = float(route.loc[s, "thoi_gian_chuan_bi_phut"] or 0) + \
            qty * float(route.loc[s, "thoi_gian_chuan_phut"]) * rnd.uniform(1.0, 1.12)
        if rnd.random() < BREAKDOWN_PROB:
            stop = rnd.randint(10, 40)
            d0 = st + timedelta(minutes=rnd.uniform(0, dur))
            tb = fetch_one("SELECT ma_tb FROM thiet_bi WHERE ma_tram = ? LIMIT 1", (s,))["ma_tb"]
            E.record_downtime(tb, to_str(d0), to_str(d0 + timedelta(minutes=stop)), rnd.choice(STOP_CAUSES), ma_lsx)
            dur += stop
            events.append((s, "dừng máy", stop))
        bad = sum(rnd.random() < DEFECT_PROB[s] for _ in range(qty))
        end = (st + timedelta(minutes=dur)).replace(microsecond=0)
        X.finish_operation(log_id, qty - bad, bad, to_str(end))
        if bad:
            codes = list(query_df("SELECT ma_loi FROM ma_loi WHERE ma_tram_phat_sinh = ?", (s,))["ma_loi"])
            Qy.record_inspection(ma_lsx, s, qty, qty - bad, rnd.choice(codes), bad, ts=to_str(end))
        events.append((s, "xong", qty - bad, bad))
        t = end
    return events


def simulate_released(start_ts, seed=None):
    """Chạy lần lượt mọi lệnh Đã phát lệnh theo thứ tự ưu tiên."""
    orders = query_df("SELECT ma_lsx FROM lenh_san_xuat WHERE trang_thai = ? ORDER BY uu_tien, ma_lsx",
                      (P.DA_PHAT_LENH,))["ma_lsx"]
    return {m: simulate_order(m, start_ts, None if seed is None else seed + i) for i, m in enumerate(orders)}
