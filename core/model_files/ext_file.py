"""新格式外力檔（.ext，fileVersion 2.x）讀取。說明見 docs/DOMAIN_NOTES_run_module.md §3。

允許多個同名區塊（[Boundary]、[Lateral]、[Meteo]）；整段被 # 註解掉的區塊視為「停用」，仍會列出。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .ini_lines import COMMENT, IniDocument, classify, parse_key_value, split_line_ending


@dataclass
class ExtBlock:
    type: str                       # 區塊名稱，例如 Boundary / Meteo（原始大小寫）
    values: list[tuple[str, str]] = field(default_factory=list)  # (key, value)，保留順序與重複 key
    start_line: int = 0             # 區塊標頭行號
    end_line: int = 0               # 區塊結束（不含）
    enabled: bool = True            # False = 整段被 # 註解掉

    def get(self, key: str) -> str | None:
        for k, v in self.values:
            if k.lower() == key.lower():
                return v
        return None


@dataclass
class MeteoInfo:
    quantity: str | None
    forcing_file: str | None
    forcing_file_type: str | None
    forcing_variable_name: str | None
    block: ExtBlock


class ExtFile(IniDocument):
    """base_dir：引用檔相對路徑的基準。
    PathsRelativeToParent = 0 時應為 MDU 所在資料夾（預設用 .ext 自己所在的資料夾）。"""

    def __init__(self, text: str, path=None, encoding: str = "utf-8", base_dir=None):
        self._base_dir = Path(base_dir) if base_dir else None
        super().__init__(text, path=path, encoding=encoding)

    @classmethod
    def load(cls, path, base_dir=None):
        doc = super().load(path)
        doc._base_dir = Path(base_dir) if base_dir else None
        return doc

    @property
    def base_dir(self) -> Path:
        if self._base_dir:
            return self._base_dir
        return self.path.parent if self.path else Path(".")

    def _parse(self):
        super()._parse()
        self.blocks: list[ExtBlock] = [
            ExtBlock(
                type=s.name,
                values=[(e.key, e.value) for e in s.entries],
                start_line=s.header_line,
                end_line=s.end_line,
                enabled=True,
            )
            for s in self.sections
            if s.name.lower() != "general"
        ]
        self.blocks.extend(self._disabled_blocks())
        self.blocks.sort(key=lambda b: b.start_line)

    def _disabled_blocks(self) -> list[ExtBlock]:
        """找出被註解掉的區塊：`#[Meteo]` 之後連續的 `#key=value` 行"""
        blocks: list[ExtBlock] = []
        current: ExtBlock | None = None
        for i in range(len(self._lines)):
            content, _ = split_line_ending(self._lines[i])
            if classify(content) != COMMENT:
                if current is not None:
                    current.end_line = i
                    current = None
                continue
            inner = content.strip().lstrip("#").strip()
            if inner.startswith("[") and "]" in inner:
                if current is not None:
                    current.end_line = i
                current = ExtBlock(type=inner[1:].split("]", 1)[0].strip(), start_line=i, enabled=False)
                blocks.append(current)
            elif current is not None and "=" in inner:
                key, value, _ = parse_key_value(inner)
                current.values.append((key, value))
        if current is not None:
            current.end_line = len(self._lines)
        return [b for b in blocks if b.type.lower() != "general"]

    # ── 查詢 ────────────────────────────────────
    def blocks_of(self, block_type: str, include_disabled: bool = False) -> list[ExtBlock]:
        return [
            b for b in self.blocks
            if b.type.lower() == block_type.lower() and (b.enabled or include_disabled)
        ]

    def referenced_files(self, include_disabled: bool = False) -> list[tuple[ExtBlock, str, Path]]:
        """所有被引用的檔案：key 以 file 結尾（forcingFile、locationFile、targetMaskFile…）且有值。
        回傳 (區塊, key, 絕對路徑)。"""
        result = []
        for b in self.blocks:
            if not b.enabled and not include_disabled:
                continue
            for key, value in b.values:
                if key.lower().endswith("file") and value:
                    result.append((b, key, (self.base_dir / value).resolve()))
        return result

    def meteo_blocks(self, include_disabled: bool = False) -> list[MeteoInfo]:
        return [
            MeteoInfo(
                quantity=b.get("quantity"),
                forcing_file=b.get("forcingFile"),
                forcing_file_type=b.get("forcingFileType"),
                forcing_variable_name=b.get("forcingVariableName"),
                block=b,
            )
            for b in self.blocks_of("Meteo", include_disabled)
        ]
