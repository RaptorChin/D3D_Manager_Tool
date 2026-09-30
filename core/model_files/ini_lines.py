"""逐行 INI 引擎：.mdu、.ext、.bc、structures.ini 共用。

為什麼不用 configparser（詳見 CLAUDE.md「模型檔讀寫」）：
key 大小寫、行尾註解、存檔時丟失格式、不允許重複區塊。

設計原則：
- 每一行原文（含 CRLF/LF、行尾空白、註解）都保留在 self._lines，未修改的行逐位元組寫回。
- 區塊以「清單」保存，允許同名區塊（.ext 的多個 [Boundary]）。
- 區塊名稱與 key 比對都不分大小寫；取值時去除行尾 `# 註解` 與前後空白。
- 修改時只替換該行「值」的部分，保留 key 原本的大小寫、對齊空白與行尾註解。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# 行的分類
SECTION = "section"
KEY_VALUE = "kv"
COMMENT = "comment"
BLANK = "blank"
DATA = "data"

_LINE_SPLIT = re.compile(r"[^\n]*\n|[^\n]+$")
_KV_HEAD = re.compile(r"^(?P<indent>[ \t]*)(?P<key>[^=]*?)(?P<gap>[ \t]*)=(?P<after>[ \t]*)")


@dataclass
class IniEntry:
    """區塊內的一行 key = value"""
    key: str          # 原始大小寫
    value: str        # 已去除註解與前後空白
    line_no: int      # 在檔案中的行號（0 起算）
    comment: str = ""  # 行尾註解（含 #），沒有則為空字串


@dataclass
class IniSection:
    name: str                 # 原始大小寫（不含中括號）
    header_line: int          # [name] 所在行號
    end_line: int             # 區塊結束（不含），即下一個區塊標頭或檔尾
    entries: list[IniEntry] = field(default_factory=list)
    data_lines: list[tuple[int, str]] = field(default_factory=list)  # (行號, 去除換行的內容)

    def get(self, key: str) -> str | None:
        """取第一個符合的 key（不分大小寫）；不存在回傳 None"""
        for e in self.entries:
            if e.key.lower() == key.lower():
                return e.value
        return None

    def get_all(self, key: str) -> list[str]:
        """同一區塊內重複出現的 key（例如 .bc 的 quantity / unit）依序全部取出"""
        return [e.value for e in self.entries if e.key.lower() == key.lower()]

    def entry(self, key: str) -> IniEntry | None:
        for e in self.entries:
            if e.key.lower() == key.lower():
                return e
        return None


def split_lines(text: str) -> list[str]:
    """切成多行並保留各行原本的換行符號（只以 
 為界，不會被其他控制字元切斷）"""
    return _LINE_SPLIT.findall(text)


def split_line_ending(raw: str) -> tuple[str, str]:
    """把一行拆成（內容, 換行符號）"""
    if raw.endswith("\r\n"):
        return raw[:-2], "\r\n"
    if raw.endswith("\n") or raw.endswith("\r"):
        return raw[:-1], raw[-1]
    return raw, ""


def classify(content: str) -> str:
    stripped = content.strip()
    if not stripped:
        return BLANK
    if stripped[0] in "#*":
        return COMMENT
    if stripped.startswith("[") and "]" in stripped:
        return SECTION
    if "=" in stripped:
        return KEY_VALUE
    return DATA


def parse_key_value(content: str) -> tuple[str, str, str]:
    """回傳 (key, value, comment)；value 已去除註解與前後空白"""
    key, _, rest = content.partition("=")
    value, hash_, comment = rest.partition("#")
    return key.strip(), value.strip(), (hash_ + comment).rstrip() if hash_ else ""


def decode_bytes(data: bytes) -> tuple[str, str]:
    """回傳 (文字, 編碼)。預設 utf-8（含 BOM），失敗時退回 cp950，最後 latin-1（必定可逆）"""
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    for enc in ("utf-8", "cp950"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1"), "latin-1"


class IniDocument:
    """一份 INI 風格模型檔。以 load() 讀檔，修改後以 save() 寫回。"""

    def __init__(self, text: str, path: Path | None = None, encoding: str = "utf-8"):
        self.path = Path(path) if path else None
        self.encoding = encoding
        self._lines: list[str] = split_lines(text)
        self.modified = False
        self._parse()

    # ── 讀寫檔案 ─────────────────────────────────
    @classmethod
    def load(cls, path):
        path = Path(path)
        text, encoding = decode_bytes(path.read_bytes())
        return cls(text, path=path, encoding=encoding)

    def to_text(self) -> str:
        return "".join(self._lines)

    def to_bytes(self) -> bytes:
        return self.to_text().encode(self.encoding)

    def save(self, path=None) -> Path:
        """寫回檔案（預設覆寫原檔）；以讀入時的編碼寫回"""
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError("未指定存檔路徑")
        target.write_bytes(self.to_bytes())
        self.modified = False
        return target

    # ── 解析 ────────────────────────────────────
    def _parse(self):
        self.sections: list[IniSection] = []
        self.preamble_end = len(self._lines)  # 第一個區塊標頭之前的行（檔頭註解）
        current: IniSection | None = None
        for i, raw in enumerate(self._lines):
            content, _ = split_line_ending(raw)
            kind = classify(content)
            if kind == SECTION:
                if current is not None:
                    current.end_line = i
                else:
                    self.preamble_end = i
                name = content.strip()[1:].split("]", 1)[0].strip()
                current = IniSection(name=name, header_line=i, end_line=len(self._lines))
                self.sections.append(current)
            elif current is None:
                continue
            elif kind == KEY_VALUE:
                key, value, comment = parse_key_value(content)
                current.entries.append(IniEntry(key, value, i, comment))
            elif kind == DATA:
                current.data_lines.append((i, content))

    @property
    def newline(self) -> str:
        """檔案主要使用的換行符號（新增行時沿用）"""
        crlf = sum(1 for l in self._lines if l.endswith("\r\n"))
        lf = sum(1 for l in self._lines if l.endswith("\n") and not l.endswith("\r\n"))
        return "\r\n" if crlf >= lf else "\n"

    def line(self, line_no: int) -> str:
        """某一行的內容（不含換行符號）"""
        return split_line_ending(self._lines[line_no])[0]

    # ── 查詢 ────────────────────────────────────
    def find_sections(self, name: str) -> list[IniSection]:
        return [s for s in self.sections if s.name.lower() == name.lower()]

    def section(self, name: str, occurrence: int = 0) -> IniSection | None:
        found = self.find_sections(name)
        return found[occurrence] if occurrence < len(found) else None

    def get(self, section: str, key: str, occurrence: int = 0) -> str | None:
        """取值；區塊或 key 不存在回傳 None。occurrence 指第幾個同名區塊"""
        sec = self.section(section, occurrence)
        return sec.get(key) if sec else None

    # ── 修改 ────────────────────────────────────
    def set_value(self, section: str, key: str, value, occurrence: int = 0):
        """設定值：只替換該行的「值」；key 不存在時在該區塊最後一個 key 之後插入新行；
        區塊不存在時（僅限 occurrence=0）在檔尾新增區塊。"""
        value = str(value)
        sec = self.section(section, occurrence)
        if sec is None:
            if occurrence != 0:
                raise KeyError(f"找不到第 {occurrence + 1} 個 [{section}] 區塊")
            self._append_section(section, key, value)
        else:
            entry = sec.entry(key)
            if entry is not None:
                self._replace_value(entry.line_no, value)
            else:
                self._insert_key(sec, key, value)
        self.modified = True
        self._parse()

    def _replace_value(self, line_no: int, new_value: str):
        content, ending = split_line_ending(self._lines[line_no])
        m = _KV_HEAD.match(content)
        rest = content[m.end():]
        head = content[: m.end()]
        if rest.startswith("#") and m.group("after"):
            # 原本的值是空的：`Key = <空白># 註解`，head 只保留 = 後面一個空白，其餘空白算值的欄位寬度
            keep = min(1, len(m.group("after")))
            cut = m.end("after") - len(m.group("after")) + keep
            head, rest = content[:cut], content[cut:]
        value_region, hash_, comment = rest.partition("#")
        width = len(value_region)
        if hash_:
            # 有行尾註解：盡量維持註解欄位位置，新值較長時至少保留 1 個空白
            new_region = new_value + " " * max(1, width - len(new_value))
            new_content = head + new_region + hash_ + comment
        else:
            old_value = value_region.rstrip()
            pad = len(value_region) - len(old_value)
            new_content = head + new_value + (" " * max(0, width - len(new_value)) if pad else "")
        self._lines[line_no] = new_content + ending

    def _format_new_line(self, sec: IniSection, key: str, value: str) -> str:
        """仿照同區塊既有行的縮排與 = 位置，組出新的一行（不含換行）"""
        if sec.entries:
            ref = self.line(sec.entries[-1].line_no)
            m = _KV_HEAD.match(ref)
            indent = m.group("indent")
            key_field = len(m.group("key")) + len(m.group("gap"))
            after = m.group("after")[:1] if m.group("after") else ""
            return indent + key.ljust(key_field) + "=" + after + value
        return f"{key} = {value}"

    def _insert_key(self, sec: IniSection, key: str, value: str):
        new_line = self._format_new_line(sec, key, value)
        insert_at = (sec.entries[-1].line_no if sec.entries else sec.header_line) + 1
        prev = self._lines[insert_at - 1]
        if not prev.endswith(("\n", "\r")):
            # 前一行是檔尾且沒有換行，先補上
            self._lines[insert_at - 1] = prev + self.newline
        self._lines.insert(insert_at, new_line + self.newline)

    def _append_section(self, section: str, key: str, value: str):
        nl = self.newline
        if self._lines and not self._lines[-1].endswith(("\n", "\r")):
            self._lines[-1] += nl
        if self._lines and split_line_ending(self._lines[-1])[0].strip():
            self._lines.append(nl)
        self._lines.append(f"[{section}]{nl}")
        self._lines.append(f"{key} = {value}{nl}")
