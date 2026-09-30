"""結構物檔（structures.ini，fileVersion 3.00）讀取。說明見 docs/DOMAIN_NOTES_run_module.md §10。"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .ini_lines import IniDocument

# 參數值以這些副檔名結尾時，代表是時間序列檔而非定值
TIME_SERIES_SUFFIXES = (".bc", ".tim")

# 不是「參數」的描述性欄位
_INFO_KEYS = {"id", "name", "type", "branchid", "chainage", "allowedflowdir", "csdefid",
              "numcoordinates", "xcoordinates", "ycoordinates"}


@dataclass
class Structure:
    id: str | None
    name: str | None
    type: str | None
    values: list[tuple[str, str]] = field(default_factory=list)
    header_line: int = 0

    def get(self, key: str) -> str | None:
        for k, v in self.values:
            if k.lower() == key.lower():
                return v
        return None

    def get_float(self, key: str) -> float | None:
        raw = self.get(key)
        try:
            return float(raw) if raw not in (None, "") else None
        except ValueError:
            return None

    def time_series_params(self) -> list[tuple[str, str]]:
        """值為時間序列檔名的參數 (key, 檔名)"""
        return [
            (k, v) for k, v in self.values
            if k.lower() not in _INFO_KEYS and v.lower().endswith(TIME_SERIES_SUFFIXES)
        ]


class StructuresFile(IniDocument):
    def _parse(self):
        super()._parse()
        self.structures: list[Structure] = [
            Structure(
                id=s.get("id"),
                name=s.get("name"),
                type=s.get("type"),
                values=[(e.key, e.value) for e in s.entries],
                header_line=s.header_line,
            )
            for s in self.find_sections("Structure")
        ]

    def of_type(self, structure_type: str) -> list[Structure]:
        return [s for s in self.structures if (s.type or "").lower() == structure_type.lower()]

    def by_id(self, structure_id: str) -> Structure | None:
        for s in self.structures:
            if s.id == structure_id:
                return s
        return None

    def type_counts(self) -> Counter:
        """各類型數量，例如 Counter({'pump': 118, 'orifice': 57, ...})"""
        return Counter((s.type or "").lower() for s in self.structures)
