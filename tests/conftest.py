import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Mỗi ca kiểm thử dùng một CSDL mới nạp từ bộ CSV mẫu cố định tests/csv_mau.

    Nhóm thay data/csv bằng dữ liệu ngành của mình thì kiểm thử vẫn chạy trên dữ liệu mẫu.
    """
    monkeypatch.setenv("MES_DB", str(tmp_path / "test.db"))
    from db.database import reset_db
    reset_db(csv_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv_mau"))
    return tmp_path
