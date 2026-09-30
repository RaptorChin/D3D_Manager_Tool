"""邊界／外力條件檔（.bc）讀取。說明見 docs/DOMAIN_NOTES_run_module.md §4。

一個 .bc 可有多個 [Forcing]（大小寫皆可）；同一區塊內 quantity / unit 會重複出現，
依序對應資料列的各個欄位。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .ini_lines import IniDocument

_UNIT_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
_TIME_UNIT = re.compile(
    r"^\s*(?P<unit>seconds?|minutes?|hours?|days?)\s+since\s+"
    r"(?P<date>\d{4}-\d{1,2}-\d{1,2})(?:[ T](?P<time>\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?))?",
    re.IGNORECASE,
)


def parse_time_reference(unit: str) -> tuple[int, datetime] | None:
    """解析「seconds since 2000-01-01 00:00:00」→ (每單位秒數, 基準時間)；格式不符回傳 None"""
    m = _TIME_UNIT.match(unit or "")
    if not m:
        return None
    seconds = _UNIT_SECONDS[m.group("unit").lower().rstrip("s")]
    y, mo, d = (int(x) for x in m.group("date").split("-"))
    base = datetime(y, mo, d)
    if m.group("time"):
        parts = m.group("time").split(":")
        base += timedelta(hours=int(parts[0]), minutes=int(parts[1]),
                          seconds=float(parts[2]) if len(parts) > 2 else 0)
    return seconds, base


@dataclass
class BcForcing:
    name: str | None
    function: str | None
    time_interpolation: str | None
    quantities: list[str] = field(default_factory=list)
    units: list[str] = field(default_factory=list)
    rows: list[list[float]] = field(default_factory=list)  # 資料列（無法轉成數字的列略過）
    header_line: int = 0

    @property
    def is_time_series(self) -> bool:
        return (self.function or "").strip().lower() == "timeseries"

    @property
    def time_reference(self) -> str | None:
        """時間欄的 unit 字串，例如 seconds since 2000-01-01 00:00:00"""
        for q, u in zip(self.quantities, self.units):
            if q.lower() == "time":
                return u
        return None

    def time_range(self) -> tuple[datetime, datetime] | None:
        """時間序列的起訖時間；function 不是 timeSeries、沒有資料或時間基準無法解析時回傳 None"""
        if not self.is_time_series or not self.rows:
            return None
        ref = parse_time_reference(self.time_reference or "")
        if ref is None:
            return None
        col = next((i for i, q in enumerate(self.quantities) if q.lower() == "time"), 0)
        values = [r[col] for r in self.rows if len(r) > col]
        if not values:
            return None
        seconds, base = ref
        return (base + timedelta(seconds=min(values) * seconds),
                base + timedelta(seconds=max(values) * seconds))


class BcFile(IniDocument):
    def _parse(self):
        super()._parse()
        self.forcings: list[BcForcing] = []
        for s in self.find_sections("Forcing"):
            rows = []
            for _, content in s.data_lines:
                try:
                    rows.append([float(x) for x in content.split()])
                except ValueError:
                    continue
            self.forcings.append(BcForcing(
                name=s.get("name"),
                function=s.get("function"),
                time_interpolation=s.get("timeInterpolation"),
                quantities=s.get_all("quantity"),
                units=s.get_all("unit"),
                rows=rows,
                header_line=s.header_line,
            ))

    def forcing(self, name: str) -> BcForcing | None:
        for f in self.forcings:
            if (f.name or "").lower() == name.lower():
                return f
        return None
