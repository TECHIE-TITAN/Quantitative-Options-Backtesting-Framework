import re
from datetime import date, datetime

_DAY_FOLDER_RE = re.compile(r"^NSE_(?P<date>\d{8})$")

def parse_day_folder(folder_name: str) -> date | None:
    m = _DAY_FOLDER_RE.match(folder_name)
    if not m:
        return None
    return datetime.strptime(m.group("date"), "%Y%m%d").date()