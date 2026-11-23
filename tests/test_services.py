"""Các ca kiểm thử bắt buộc (Bước 5, mục 7). Chạy: pytest -q"""
import pytest

from db.database import fetch_one, query_df
from services import equipment as E, execution as X, planning as P, quality as Q

T0 = "2026-11-09 08:00:00"


def released_order(ma_dh="DH-2611-001"):
    m = P.create_work_order(ma_dh, T0)
    plan, _ = P.schedule_orders("EDD", "2026-11-10")
    P.save_schedule(plan[plan.ma_lsx == m])
    P.auto_assign(m, "CA1", "2026-11-10")
    P.release_order(m, T0)
    return m


# KT-01 Tạo lệnh từ đơn hàng
def test_create_work_order(db):
    m = P.create_work_order("DH-2611-001", T0)
    assert m == "LSX-261109-01"
    assert fetch_one("SELECT trang_thai FROM don_hang WHERE ma_dh='DH-2611-001'")["trang_thai"] == "đã lập lệnh"
    with pytest.raises(ValueError):
        P.create_work_order("DH-2611-001", T0)          # không lập lệnh hai lần


# KT-02 Chặn chuyển trạng thái sai
def test_invalid_transition(db):
    m = P.create_work_order("DH-2611-001", T0)
    with pytest.raises(ValueError):
        P.change_status(m, P.HOAN_THANH)


# KT-03 Nhu cầu vật tư theo BOM
def test_material_requirements(db):
    m = P.create_work_order("DH-2611-001", T0)                # 60 chiếc SP-001
    req = P.material_requirements(m).set_index("ma_vat_tu")
    assert req.loc["VT-001", "can"] == pytest.approx(2.47 * 1.03 * 60, rel=1e-3)


# KT-04 Quy tắc EDD không trễ hơn FIFO trên dữ liệu mẫu
def test_edd_vs_fifo(db):
    for d in query_df("SELECT ma_dh FROM don_hang").ma_dh:
        P.create_work_order(d, T0)
    cmp = P.compare_rules("2026-11-10").set_index("quy_tac")
    assert cmp.loc["EDD", "tong_tre_phut"] <= cmp.loc["FIFO", "tong_tre_phut"]


# KT-05 Lịch flow shop: một trạm không làm hai lệnh cùng lúc
def test_no_overlap(db):
    for d in query_df("SELECT ma_dh FROM don_hang").ma_dh:
        P.create_work_order(d, T0)
    plan, _ = P.schedule_orders("SPT", "2026-11-10")
    for _, g in plan.sort_values("start_min").groupby("ma_tram"):
        assert (g.start_min.values[1:] >= g.end_min.values[:-1]).all()


# KT-06 Không phân công người chưa có kỹ năng
def test_assign_skill(db):
    m = P.create_work_order("DH-2611-001", T0)
    with pytest.raises(ValueError):
        P.assign_worker(m, "T3", "NV-001", "CA1", "2026-11-10")   # NV-001 chỉ có kỹ năng T1, T2


# KT-07 Phải làm đúng thứ tự trạm
def test_station_order(db):
    m = released_order()
    with pytest.raises(ValueError):
        X.start_operation(m, "T2", "2026-11-10 06:00:00")


# KT-08 Xuất vật tư FIFO và truy xuất lô
def test_issue_fifo_and_trace(db):
    m = released_order()
    X.start_operation(m, "T1", "2026-11-10 06:00:00")
    lot = fetch_one("SELECT ma_lo_vat_tu FROM nhat_ky_cong_doan WHERE ma_lsx = ?", (m,))["ma_lo_vat_tu"]
    assert lot == "LOT-261101-01"                                # lô nhập sớm nhất
    assert m in list(X.trace_lot("LOT-261101-01").ma_lsx)


# KT-09 Số đạt + lỗi không vượt số lượng vào; hoàn thành ở trạm cuối
def test_finish_and_complete(db):
    m = released_order()
    t = ["2026-11-10 06:00:00", "2026-11-10 08:00:00", "2026-11-10 15:00:00",
         "2026-11-10 21:00:00", "2026-11-11 02:00:00", "2026-11-11 06:00:00"]
    qty = 60
    for i, s in enumerate(["T1", "T2", "T3", "T4", "T5"]):
        log = X.start_operation(m, s, t[i])
        if i == 0:
            with pytest.raises(ValueError):
                X.finish_operation(log, qty, 1, t[i + 1])
        X.finish_operation(log, qty - 1, 1, t[i + 1])
        qty -= 1
    r = fetch_one("SELECT * FROM lenh_san_xuat WHERE ma_lsx = ?", (m,))
    assert r["trang_thai"] == P.HOAN_THANH and r["so_luong_dat"] == 55 and r["so_luong_loi"] == 5


# KT-10 Kiểm tra chất lượng: có lỗi phải có mã lỗi
def test_inspection_rules(db):
    m = P.create_work_order("DH-2611-001", T0)
    with pytest.raises(ValueError):
        Q.record_inspection(m, "T2", 10, 8, None, 2)
    Q.record_inspection(m, "T2", 10, 8, "L-03", 2)
    assert Q.pareto_defects().so_luong.sum() == 2


# KT-11 OEE tính tay khớp với hàm
def test_oee(db):
    m = released_order()
    log = X.start_operation(m, "T1", "2026-11-10 06:00:00")
    X.finish_operation(log, 59, 1, "2026-11-10 08:30:00")     # 150 phút
    E.record_downtime("TB-01", "2026-11-10 07:00:00", "2026-11-10 07:30:00", "D-01", m)
    o = E.calc_oee("T1", "2026-11-10 06:00:00", "2026-11-10 08:30:00")
    # A = 120/150, P = 60 x 2 / 120 = 1, Q = 59/60
    assert o["A"] == pytest.approx(0.8)
    assert o["P"] == pytest.approx(1.0)
    assert o["OEE"] == pytest.approx(0.8 * 59 / 60, abs=1e-4)
