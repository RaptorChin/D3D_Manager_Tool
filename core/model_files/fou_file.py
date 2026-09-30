"""統計輸出設定檔（.fou）讀取。說明見 docs/DOMAIN_NOTES_run_module.md §5。

以空白分隔的表格，`*` 開頭為註解；tstart / tstop 單位為 MDU 的 Tunit、相對 RefDate，-1 代表模擬起訖。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ini_lines import decode_bytes, split_line_ending, split_lines


@dataclass
class FouEntry:
    quantity: str
    tstart: float
    tstop: float
    columns: list[str]   # 整行以空白切開的所有欄位
    line_no: int

    @property
    def uses_full_period(self) -> bool:
        """tstart 與 tstop 皆為 -1（整個模擬時段）"""
        return self.tstart == -1 and self.tstop == -1


class FouFile:
    def __init__(self, text: str, path=None, encoding: str = "utf-8"):
        self.path = Path(path) if path else None
        self.encoding = encoding
        self._lines = split_lines(text)
        self.entries: list[FouEntry] = []
        for i, raw in enumerate(self._lines):
            content, _ = split_line_ending(raw)
            stripped = content.strip()
            if not stripped or stripped.startswith("*"):
                continue
            cols = stripped.split()
            if len(cols) < 3:
                continue
            try:
                tstart, tstop = float(cols[1]), float(cols[2])
            except ValueError:
                continue
            self.entries.append(FouEntry(cols[0], tstart, tstop, cols, i))

    @classmethod
    def load(cls, path):
        path = Path(path)
        text, encoding = decode_bytes(path.read_bytes())
        return cls(text, path=path, encoding=encoding)

    def to_text(self) -> str:
        return "".join(self._lines)

    def entry(self, quantity: str) -> FouEntry | None:
        for e in self.entries:
            if e.quantity.lower() == quantity.lower():
                return e
        return None
