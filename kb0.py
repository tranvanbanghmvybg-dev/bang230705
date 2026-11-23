"""Kịch bản chuẩn KB0 (Chương 6, mục 6.8.8). Chạy tại gốc dự án: python kb0.py"""
from db import database as db
from services import planning as P
from simulator import station_sim as S

db.reset_db()
T0 = "2026-11-09 08:00:00"
for d in db.query_df("SELECT ma_dh FROM don_hang ORDER BY ma_dh").ma_dh:
    P.create_work_order(d, T0)
plan, _ = P.schedule_orders("EDD", "2026-11-10")
P.save_schedule(plan)
for m in db.query_df("SELECT ma_lsx FROM lenh_san_xuat ORDER BY uu_tien").ma_lsx:
    P.auto_assign(m, "CA1", "2026-11-10")
    P.release_order(m, T0)
ev = S.simulate_released("2026-11-10 06:00:00", seed=1)
print(ev["LSX-261109-06"])
