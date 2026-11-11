"""Tìm thư mục mã nguồn và dữ liệu, dùng được cả trong repo (tests/) lẫn gói nộp (05_Test/)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_candidates = [HERE.parent, HERE.parent / "01_SourceCode"]
SRC = next(p for p in _candidates if (p / "fraud_core.py").exists())
DATA = SRC / "data"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def btc_files():
    """Data Pack BTC dạng {tên tệp: bytes}, như app nhận khi người dùng tải lên."""
    return {p.name.lower(): p.read_bytes() for p in DATA.glob("*.csv")}
