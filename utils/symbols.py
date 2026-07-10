import re
from dataclasses import dataclass
from datetime import date, datetime

_OPTION_RE = re.compile(
    r"^(?P<underlier>BANKNIFTY|FINNIFTY|NIFTY)"
    r"(?P<expiry>\d{6})"
    r"(?P<strike>\d+)"
    r"(?P<opt_type>CE|PE)\.csv$",
    re.IGNORECASE,
)

_FUTURES_RE = re.compile(
    r"^(?P<underlier>BANKNIFTY|FINNIFTY|NIFTY)-(?P<series>I{1,3})\.csv$",
    re.IGNORECASE,
)

_DAY_FOLDER_RE = re.compile(r"^NSE_(?P<date>\d{8})$")

@dataclass(frozen=True)
class OptionContract:
    underlier: str
    expiry: date
    strike: float
    opt_type: str  # "CE" or "PE"
    path: str

    @property
    def key(self):
        return (self.underlier, self.expiry, self.strike, self.opt_type)

    @property
    def symbol(self) -> str:
        return f"{self.underlier}{self.expiry.strftime('%y%m%d')}{int(self.strike)}{self.opt_type}"

def parse_yymmdd(s: str) -> date:
    return datetime.strptime(s, "%y%m%d").date()

def parse_option_filename(filename: str, full_path: str) -> OptionContract | None:
    m = _OPTION_RE.match(filename)
    if not m:
        return None
    return OptionContract(
        underlier=m.group("underlier").upper(),
        expiry=parse_yymmdd(m.group("expiry")),
        strike=float(m.group("strike")),
        opt_type=m.group("opt_type").upper(),
        path=full_path,
    )

def parse_futures_filename(filename: str):
    """Returns (underlier, series) or None."""
    m = _FUTURES_RE.match(filename)
    if not m:
        return None
    return m.group("underlier").upper(), m.group("series").upper()

def parse_day_folder(folder_name: str) -> date | None:
    m = _DAY_FOLDER_RE.match(folder_name)
    if not m:
        return None
    return datetime.strptime(m.group("date"), "%Y%m%d").date()
