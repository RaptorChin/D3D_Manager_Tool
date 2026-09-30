"""DIMR 設定檔（dimr_config.xml）讀寫。說明見 docs/DOMAIN_NOTES_run_module.md §8。

讀取用 ElementTree；寫入時「只改 <process> 與 <mpiCommunicator> 這兩行文字」，
其餘內容（註解、縮排、命名空間宣告、換行符號）逐位元組保留。
（ElementTree 寫回會把命名空間改成 ns0:、丟掉縮排，因此不用它寫檔。）
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from .ini_lines import decode_bytes

MPI_COMMUNICATOR = "DFM_COMM_DFMWORLD"

_COMPONENT = re.compile(r"<component\b[^>]*>.*?</component>", re.DOTALL | re.IGNORECASE)


def _local(tag: str) -> str:
    """去掉命名空間：{http://...}component → component"""
    return tag.rsplit("}", 1)[-1]


@dataclass
class DimrComponent:
    name: str | None
    library: str | None
    working_dir: str | None
    input_file: str | None
    processes: list[int] | None = None      # None = 沒有 <process>（單核心）
    mpi_communicator: str | None = None
    settings: dict[str, str] = field(default_factory=dict)


class DimrConfig:
    def __init__(self, text: str, path=None, encoding: str = "utf-8"):
        self.path = Path(path) if path else None
        self.encoding = encoding
        self.text = text
        self._parse()

    @classmethod
    def load(cls, path):
        path = Path(path)
        text, encoding = decode_bytes(path.read_bytes())
        return cls(text, path=path, encoding=encoding)

    def save(self, path=None) -> Path:
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError("未指定存檔路徑")
        target.write_bytes(self.text.encode(self.encoding))
        return target

    # ── 讀取 ────────────────────────────────────
    def _parse(self):
        # ElementTree 不接受帶 encoding 宣告的 str，改傳 bytes
        root = ET.fromstring(self.text.encode("utf-8"))
        self.components: list[DimrComponent] = []
        for comp in root:
            if _local(comp.tag) != "component":
                continue
            fields = {_local(c.tag): (c.text or "").strip() for c in comp}
            settings = {
                c.get("key"): c.get("value")
                for c in comp if _local(c.tag) == "setting" and c.get("key")
            }
            process = fields.get("process")
            self.components.append(DimrComponent(
                name=comp.get("name"),
                library=fields.get("library"),
                working_dir=fields.get("workingDir"),
                input_file=fields.get("inputFile"),
                processes=[int(x) for x in process.split()] if process else None,
                mpi_communicator=fields.get("mpiCommunicator") or None,
                settings=settings,
            ))

    @property
    def flow_component(self) -> DimrComponent | None:
        """D-Flow FM 元件（library = dflowfm）"""
        for c in self.components:
            if (c.library or "").lower() == "dflowfm":
                return c
        return None

    @property
    def other_components(self) -> list[DimrComponent]:
        """D-Flow FM 以外的元件（RTC 等；預檢 I02 用）"""
        return [c for c in self.components if (c.library or "").lower() != "dflowfm"]

    @property
    def working_dir(self) -> str | None:
        c = self.flow_component
        return c.working_dir if c else None

    @property
    def input_file(self) -> str | None:
        c = self.flow_component
        return c.input_file if c else None

    @property
    def processes(self) -> list[int] | None:
        c = self.flow_component
        return c.processes if c else None

    # ── 寫入 ────────────────────────────────────
    def set_parallel(self, n: int):
        """設定 D-Flow FM 元件的平行核心數。
        n > 1：<process> 設為 0..n-1，並確保有 <mpiCommunicator>DFM_COMM_DFMWORLD</mpiCommunicator>；
        n == 1：移除 <process> 與 <mpiCommunicator>。"""
        if n < 1:
            raise ValueError("核心數必須 ≥ 1")
        match = self._flow_component_match()
        block = match.group(0)
        newline = "\r\n" if "\r\n" in self.text else "\n"

        if n == 1:
            new_block = self._remove_line(block, "process")
            new_block = self._remove_line(new_block, "mpiCommunicator")
        else:
            process_text = " ".join(str(i) for i in range(n))
            new_block = self._set_line(block, "process", process_text, after="inputFile", newline=newline)
            new_block = self._set_line(new_block, "mpiCommunicator", MPI_COMMUNICATOR, after="process", newline=newline)

        self.text = self.text[: match.start()] + new_block + self.text[match.end():]
        self._parse()

    def _flow_component_match(self) -> re.Match:
        for m in _COMPONENT.finditer(self.text):
            if re.search(r"<library>\s*dflowfm\s*</library>", m.group(0), re.IGNORECASE):
                return m
        raise ValueError("dimr_config.xml 中找不到 D-Flow FM 元件（<library>dflowfm</library>）")

    @staticmethod
    def _line_pattern(tag: str) -> re.Pattern:
        """整行（含縮排與換行）的 <tag>...</tag> 或 <tag/>"""
        return re.compile(
            rf"^[ \t]*<{tag}\b[^>]*?(?:/>|>.*?</{tag}>)[ \t]*(?:\r?\n)?",
            re.MULTILINE | re.DOTALL,
        )

    def _remove_line(self, block: str, tag: str) -> str:
        return self._line_pattern(tag).sub("", block, count=1)

    def _set_line(self, block: str, tag: str, value: str, after: str, newline: str) -> str:
        existing = re.search(rf"(<{tag}\b[^>]*>)(.*?)(</{tag}>)", block, re.DOTALL)
        if existing:
            return block[: existing.start(2)] + value + block[existing.end(2):]
        # 不存在：插在 <after> 那一行之後，縮排比照該行；找不到 <after> 則插在 </component> 前
        anchor = self._line_pattern(after).search(block)
        if anchor:
            indent = re.match(r"[ \t]*", anchor.group(0)).group(0)
            line = f"{indent}<{tag}>{value}</{tag}>{newline}"
            end = anchor.end()
            if not anchor.group(0).endswith("\n"):
                line = newline + line.rstrip("\r\n")
            return block[:end] + line + block[end:]
        close = block.lower().rindex("</component>")
        line_start = block.rfind("\n", 0, close) + 1
        indent = "  " + re.match(r"[ \t]*", block[line_start:close]).group(0)
        return block[:line_start] + f"{indent}<{tag}>{value}</{tag}>{newline}" + block[line_start:]
