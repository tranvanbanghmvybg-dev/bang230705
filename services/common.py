"""Hàm tiện ích dùng chung: định dạng thời gian, hằng số ca làm việc."""
from datetime import datetime, timedelta

FMT = "%Y-%m-%d %H:%M:%S"
DAY_START_HOUR = 6          # CA1 bắt đầu 06:00
WORK_MIN_PER_DAY = 2 * 450  # 2 ca x 450 phút làm việc


def to_str(dt):
    return dt.strftime(FMT)


def to_dt(s):
    if isinstance(s, datetime):
        return s
    s = str(s)
    return datetime.strptime(s, FMT) if len(s) > 10 else datetime.strptime(s, "%Y-%m-%d")


def now_str():
    return to_str(datetime.now().replace(microsecond=0))


def minutes_between(a, b):
    return (to_dt(b) - to_dt(a)).total_seconds() / 60


def work_minutes_to_dt(start_day, m):
    """Đổi phút làm việc tính từ 06:00 ngày start_day sang thời điểm lịch.

    Mỗi ngày có WORK_MIN_PER_DAY phút làm việc liên tục từ 06:00 (bỏ qua giờ nghỉ giữa ca).
    """
    base = to_dt(str(start_day)[:10]).replace(hour=DAY_START_HOUR)
    day, within = divmod(m, WORK_MIN_PER_DAY)
    return base + timedelta(days=int(day), minutes=within)


def due_in_work_minutes(start_day, due_date):
    """Hạn giao (hết ngày làm việc của ngày giao) đổi ra phút làm việc kể từ start_day."""
    days = (to_dt(str(due_date)[:10]) - to_dt(str(start_day)[:10])).days
    return (days + 1) * WORK_MIN_PER_DAY
