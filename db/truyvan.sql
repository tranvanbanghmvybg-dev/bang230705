-- Q1. Dây chuyền 5 trạm theo thứ tự                       → 5 dòng: T1 Cắt phôi … T5 Kiểm tra, đóng gói
SELECT ma_tram, ten_tram, thu_tu_tren_day_chuyen
FROM tram ORDER BY thu_tu_tren_day_chuyen;

-- Q2. Quy trình công nghệ của SP-001 kèm tên trạm (JOIN) → 5 dòng, tổng 20 phút/sản phẩm
SELECT q.thu_tu, q.ma_tram, t.ten_tram, q.ten_cong_doan, q.thoi_gian_chuan_phut
FROM quy_trinh q JOIN tram t ON t.ma_tram = q.ma_tram
WHERE q.ma_san_pham = 'SP-001' ORDER BY q.thu_tu;

-- Q3. Đơn hàng kèm tên khách, sắp theo hạn giao          → 8 dòng, sớm nhất DH-2611-006 (11/11/2026)
SELECT d.ma_dh, k.ten_kh, d.ma_san_pham, d.so_luong, d.ngay_giao
FROM don_hang d JOIN khach_hang k ON k.ma_kh = d.ma_kh
ORDER BY d.ngay_giao, d.ma_dh;

-- Q4. Tổng thời gian chuẩn mỗi sản phẩm (GROUP BY)       → SP-001 20,0; SP-002 22,5; SP-003 17,0 phút
SELECT ma_san_pham, SUM(thoi_gian_chuan_phut) AS tong_phut_moi_sp
FROM quy_trinh GROUP BY ma_san_pham;

-- Q5. Vật tư có tồn dưới mức tối thiểu (LEFT JOIN + HAVING) → 2 dòng: VT-005, VT-006 (tồn 0)
SELECT v.ma_vat_tu, v.ten_vat_tu, v.ton_toi_thieu,
       IFNULL(SUM(l.so_luong_con), 0) AS ton
FROM vat_tu v LEFT JOIN lo_vat_tu l ON l.ma_vat_tu = v.ma_vat_tu
GROUP BY v.ma_vat_tu
HAVING ton < v.ton_toi_thieu;
