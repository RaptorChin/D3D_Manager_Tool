"""D-Flow FM 主控檔（.mdu）讀寫。格式與時間參數說明見 docs/DOMAIN_NOTES_run_module.md §2。"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from .ini_lines import IniDocument

# Tunit → 秒數
_TUNIT_SECONDS = {"D": 86400, "H": 3600, "M": 60, "S": 1}


class MduFile(IniDocument):
    """用法：
        mdu = MduFile.load("NWT_KL.mdu")
        mdu.get("time", "tstop")          # key 與區塊名稱不分大小寫
        mdu.set("time", "TStop", 39600)   # 只改那一行的值
        mdu.save()
    """

    # ── 基本讀寫 ────────────────────────────────
    def get_float(self, section: str, key: str, default: float | None = None) -> float | None:
        """取數值；不存在、空白或無法轉換時回傳 default。
        HisInterval 等可寫成「interval start end」三個數字，此時取第一個。"""
        raw = self.get(section, key)
        if raw is None or not raw.strip():
            return default
        try:
            return float(raw.split()[0])
        except ValueError:
            return default

    def set(self, section: str, key: str, value):
        self.set_value(section, key, value)

    @property
    def model_name(self) -> str:
        return self.path.stem if self.path else ""

    @property
    def base_dir(self) -> Path:
        """MDU 所在資料夾（模型檔相對路徑的基準）"""
        return self.path.parent if self.path else Path(".")

    # ── 時間 ────────────────────────────────────
    def ref_date(self) -> datetime:
        raw = (self.get("time", "RefDate") or "").strip()
        if not raw:
            raise ValueError("MDU 缺少 [time] RefDate")
        return datetime.strptime(raw[:8], "%Y%m%d")

    def tunit_seconds(self) -> int:
        unit = (self.get("time", "Tunit") or "S").strip().upper()[:1] or "S"
        if unit not in _TUNIT_SECONDS:
            raise ValueError(f"無法辨識的 Tunit：{unit}")
        return _TUNIT_SECONDS[unit]

    def to_datetime(self, t: float) -> datetime:
        """相對 RefDate 的時間（單位 Tunit）轉成日期時間"""
        return self.ref_date() + timedelta(seconds=t * self.tunit_seconds())

    def time_window(self) -> tuple[datetime, datetime]:
        """模擬起訖時間（模型時間，未做 Tzone 換算）。
        StartDateTime / StopDateTime（yyyymmddhhmmss）有值時優先於 TStart / TStop。"""
        return self._time_point("StartDateTime", "TStart"), self._time_point("StopDateTime", "TStop")

    def _time_point(self, datetime_key: str, relative_key: str) -> datetime:
        raw = (self.get("time", datetime_key) or "").strip()
        if raw:
            return datetime.strptime(raw.ljust(14, "0")[:14], "%Y%m%d%H%M%S")
        t = self.get_float("time", relative_key)
        if t is None:
            raise ValueError(f"MDU 缺少 [time] {relative_key}")
        return self.to_datetime(t)

    # ── 引用檔路徑（相對 MDU 資料夾轉成絕對路徑；未設定回傳 None）──
    def _file(self, section: str, key: str) -> Path | None:
        raw = (self.get(section, key) or "").strip()
        return (self.base_dir / raw).resolve() if raw else None

    @property
    def net_file(self) -> Path | None:
        return self._file("geometry", "NetFile")

    @property
    def ext_file_new(self) -> Path | None:
        return self._file("external forcing", "ExtForceFileNew")

    @property
    def ext_file_old(self) -> Path | None:
        return self._file("external forcing", "ExtForceFile")

    @property
    def fou_file(self) -> Path | None:
        return self._file("output", "FouFile")

    @property
    def structure_file(self) -> Path | None:
        return self._file("geometry", "StructureFile")

    @property
    def output_dir(self) -> Path:
        """輸出資料夾；未設定時為 D-Flow FM 預設的 DFM_OUTPUT_<模型名稱>"""
        raw = (self.get("output", "OutputDir") or "").strip()
        return (self.base_dir / (raw or f"DFM_OUTPUT_{self.model_name}")).resolve()
