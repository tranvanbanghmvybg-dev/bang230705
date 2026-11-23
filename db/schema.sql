-- Lược đồ CSDL MES giả định (SQLite). Khớp tên cột với bộ dữ liệu mẫu Bước 3.
PRAGMA foreign_keys = ON;

-- ===== D1 Sản phẩm, BOM, quy trình =====
CREATE TABLE IF NOT EXISTS san_pham (
  ma_san_pham TEXT PRIMARY KEY, ten_san_pham TEXT NOT NULL, ma_ban_ve TEXT,
  don_vi_tinh TEXT NOT NULL, khoi_luong_kg REAL, trang_thai TEXT NOT NULL DEFAULT 'đang dùng',
  nguon_tham_khao TEXT);
-- ===== D5 Trạm, thiết bị =====
CREATE TABLE IF NOT EXISTS tram (
  ma_tram TEXT PRIMARY KEY, ten_tram TEXT NOT NULL, thu_tu_tren_day_chuyen INTEGER NOT NULL, mo_ta TEXT);
CREATE TABLE IF NOT EXISTS thiet_bi (
  ma_tb TEXT PRIMARY KEY, ma_tram TEXT NOT NULL REFERENCES tram(ma_tram), ten_tb TEXT NOT NULL,
  hang_model TEXT, cong_suat_kw REAL, chu_ky_bao_tri_gio INTEGER,
  trang_thai TEXT NOT NULL DEFAULT 'sẵn sàng', nguon_tham_khao TEXT);
-- ===== D3 Nhà cung cấp, D2 Vật tư =====
CREATE TABLE IF NOT EXISTS nha_cung_cap (
  ma_ncc TEXT PRIMARY KEY, ten_ncc TEXT NOT NULL, dia_chi TEXT, nguoi_lien_he TEXT, dien_thoai TEXT,
  thoi_gian_giao_ngay INTEGER NOT NULL, diem_danh_gia REAL);
CREATE TABLE IF NOT EXISTS vat_tu (
  ma_vat_tu TEXT PRIMARY KEY, ten_vat_tu TEXT NOT NULL, loai TEXT NOT NULL, don_vi TEXT NOT NULL,
  ma_ncc_chinh TEXT REFERENCES nha_cung_cap(ma_ncc), ton_toi_thieu REAL NOT NULL DEFAULT 0,
  don_gia_vnd REAL, nguon_tham_khao TEXT);
CREATE TABLE IF NOT EXISTS lo_vat_tu (
  ma_lo TEXT PRIMARY KEY, ma_vat_tu TEXT NOT NULL REFERENCES vat_tu(ma_vat_tu),
  ma_ncc TEXT NOT NULL REFERENCES nha_cung_cap(ma_ncc), ngay_nhap TEXT NOT NULL,
  so_luong_nhap REAL NOT NULL, so_luong_con REAL NOT NULL CHECK (so_luong_con >= 0), so_chung_chi TEXT);
CREATE TABLE IF NOT EXISTS bom (
  ma_san_pham TEXT NOT NULL REFERENCES san_pham(ma_san_pham),
  ma_vat_tu TEXT NOT NULL REFERENCES vat_tu(ma_vat_tu),
  dinh_muc REAL NOT NULL CHECK (dinh_muc > 0), don_vi TEXT NOT NULL, ty_le_hao_hut_pct REAL DEFAULT 0,
  nguon_tham_khao TEXT, PRIMARY KEY (ma_san_pham, ma_vat_tu));
CREATE TABLE IF NOT EXISTS sop (
  ma_sop TEXT PRIMARY KEY, ma_tram TEXT NOT NULL REFERENCES tram(ma_tram), ten TEXT NOT NULL,
  phien_ban TEXT NOT NULL, ngay_hieu_luc TEXT NOT NULL, duong_dan_file TEXT);
CREATE TABLE IF NOT EXISTS quy_trinh (
  ma_san_pham TEXT NOT NULL REFERENCES san_pham(ma_san_pham), thu_tu INTEGER NOT NULL,
  ma_tram TEXT NOT NULL REFERENCES tram(ma_tram), ten_cong_doan TEXT NOT NULL,
  thoi_gian_chuan_phut REAL NOT NULL CHECK (thoi_gian_chuan_phut > 0), thoi_gian_chuan_bi_phut REAL DEFAULT 0,
  ma_sop TEXT REFERENCES sop(ma_sop), nguon_tham_khao TEXT, PRIMARY KEY (ma_san_pham, thu_tu));
CREATE TABLE IF NOT EXISTS tieu_chuan_kiem_tra (
  ma_san_pham TEXT NOT NULL REFERENCES san_pham(ma_san_pham), ma_tram TEXT NOT NULL REFERENCES tram(ma_tram),
  dac_tinh TEXT NOT NULL, gia_tri_danh_nghia REAL, dung_sai_duoi REAL, dung_sai_tren REAL, don_vi TEXT,
  phuong_phap TEXT, tan_suat TEXT);
-- ===== D4 Khách hàng, đơn hàng =====
CREATE TABLE IF NOT EXISTS khach_hang (
  ma_kh TEXT PRIMARY KEY, ten_kh TEXT NOT NULL, dia_chi TEXT, nguoi_lien_he TEXT, muc_uu_tien INTEGER);
CREATE TABLE IF NOT EXISTS don_hang (
  ma_dh TEXT PRIMARY KEY, ma_kh TEXT NOT NULL REFERENCES khach_hang(ma_kh),
  ma_san_pham TEXT NOT NULL REFERENCES san_pham(ma_san_pham), so_luong INTEGER NOT NULL CHECK (so_luong > 0),
  ngay_dat TEXT NOT NULL, ngay_giao TEXT NOT NULL, trang_thai TEXT NOT NULL DEFAULT 'mới',
  CHECK (ngay_giao >= ngay_dat));
-- ===== D6 Nhân lực =====
CREATE TABLE IF NOT EXISTS ca_lam_viec (
  ma_ca TEXT PRIMARY KEY, gio_bat_dau TEXT NOT NULL, gio_ket_thuc TEXT NOT NULL, nghi_giua_ca_phut INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS nhan_vien (
  ma_nv TEXT PRIMARY KEY, ho_ten TEXT NOT NULL, vai_tro TEXT NOT NULL, bac_tho INTEGER,
  ma_ca TEXT NOT NULL REFERENCES ca_lam_viec(ma_ca));
CREATE TABLE IF NOT EXISTS ky_nang (
  ma_nv TEXT NOT NULL REFERENCES nhan_vien(ma_nv), ma_tram TEXT NOT NULL REFERENCES tram(ma_tram),
  muc_thanh_thao INTEGER NOT NULL CHECK (muc_thanh_thao BETWEEN 1 AND 3), PRIMARY KEY (ma_nv, ma_tram));
-- ===== Danh mục quy trình =====
CREATE TABLE IF NOT EXISTS ma_loi (
  ma_loi TEXT PRIMARY KEY, ten_loi TEXT NOT NULL, ma_tram_phat_sinh TEXT NOT NULL REFERENCES tram(ma_tram),
  muc_do TEXT NOT NULL, huong_xu_ly TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS nguyen_nhan_dung (
  ma_nguyen_nhan TEXT PRIMARY KEY, ten TEXT NOT NULL, nhom TEXT NOT NULL, anh_huong_oee TEXT NOT NULL);

-- ===== D7 Lệnh sản xuất (giao dịch) =====
CREATE TABLE IF NOT EXISTS lenh_san_xuat (
  ma_lsx TEXT PRIMARY KEY, ma_dh TEXT NOT NULL REFERENCES don_hang(ma_dh),
  ma_san_pham TEXT NOT NULL REFERENCES san_pham(ma_san_pham),
  so_luong_ke_hoach INTEGER NOT NULL CHECK (so_luong_ke_hoach > 0),
  so_luong_dat INTEGER NOT NULL DEFAULT 0, so_luong_loi INTEGER NOT NULL DEFAULT 0,
  trang_thai TEXT NOT NULL DEFAULT 'Mới tạo', uu_tien INTEGER,
  bat_dau_kh TEXT, ket_thuc_kh TEXT, ngay_tao TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lich_su_trang_thai (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ma_lsx TEXT NOT NULL REFERENCES lenh_san_xuat(ma_lsx),
  tu_trang_thai TEXT, den_trang_thai TEXT NOT NULL, thoi_diem TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS phan_cong (
  ma_lsx TEXT NOT NULL REFERENCES lenh_san_xuat(ma_lsx), ma_tram TEXT NOT NULL REFERENCES tram(ma_tram),
  ma_nv TEXT NOT NULL REFERENCES nhan_vien(ma_nv), ma_ca TEXT NOT NULL REFERENCES ca_lam_viec(ma_ca),
  ngay TEXT NOT NULL, PRIMARY KEY (ma_lsx, ma_tram));
-- ===== D8 Nhật ký công đoạn =====
CREATE TABLE IF NOT EXISTS nhat_ky_cong_doan (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ma_lsx TEXT NOT NULL REFERENCES lenh_san_xuat(ma_lsx),
  ma_tram TEXT NOT NULL REFERENCES tram(ma_tram), ma_nv TEXT REFERENCES nhan_vien(ma_nv),
  ma_lo_vat_tu TEXT REFERENCES lo_vat_tu(ma_lo), thoi_diem_bat_dau TEXT NOT NULL, thoi_diem_ket_thuc TEXT,
  so_luong_dat INTEGER, so_luong_loi INTEGER);
-- ===== D9 Chất lượng =====
CREATE TABLE IF NOT EXISTS kiem_tra_chat_luong (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ma_lsx TEXT NOT NULL REFERENCES lenh_san_xuat(ma_lsx),
  ma_tram TEXT NOT NULL REFERENCES tram(ma_tram), thoi_diem TEXT NOT NULL, so_mau INTEGER NOT NULL,
  so_dat INTEGER NOT NULL, ma_loi TEXT REFERENCES ma_loi(ma_loi), so_luong_loi INTEGER NOT NULL DEFAULT 0,
  ket_luan TEXT, ma_nv_qc TEXT REFERENCES nhan_vien(ma_nv));
-- ===== D10 Dừng máy, bảo trì =====
CREATE TABLE IF NOT EXISTS dung_may (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ma_tb TEXT NOT NULL REFERENCES thiet_bi(ma_tb),
  ma_lsx TEXT REFERENCES lenh_san_xuat(ma_lsx), thoi_diem_bat_dau TEXT NOT NULL, thoi_diem_ket_thuc TEXT NOT NULL,
  ma_nguyen_nhan TEXT NOT NULL REFERENCES nguyen_nhan_dung(ma_nguyen_nhan), ghi_chu TEXT);
CREATE TABLE IF NOT EXISTS phieu_bao_tri (
  ma_phieu TEXT PRIMARY KEY, ma_tb TEXT NOT NULL REFERENCES thiet_bi(ma_tb), loai TEXT NOT NULL,
  ngay_ke_hoach TEXT NOT NULL, ngay_thuc_hien TEXT, noi_dung TEXT);
-- ===== D2 Giao dịch kho =====
CREATE TABLE IF NOT EXISTS giao_dich_kho (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ma_lo TEXT NOT NULL REFERENCES lo_vat_tu(ma_lo),
  loai TEXT NOT NULL CHECK (loai IN ('nhập','xuất')), so_luong REAL NOT NULL,
  ma_lsx TEXT REFERENCES lenh_san_xuat(ma_lsx), thoi_diem TEXT NOT NULL);
