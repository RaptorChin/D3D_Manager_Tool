"""pytest 共用設定與 fixture。

測試資料放在 tests/fixtures/（真實模型檔，勿修改原檔；不進 Git，缺檔時相關測試自動略過）。
需要寫入時一律使用 nwt_kl_dir 取得 tmp_path 內的複本。
"""
import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
NWT_KL_DIR = FIXTURES_DIR / "NWT_KL"
DFLOWFM_DIR = NWT_KL_DIR / "dflowfm"
RUNS_DIR = FIXTURES_DIR / "runs"

# 14.7 MB 的格網雨量檔不進 Git（docs/OVERVIEW.md 待決事項 D2），換電腦時可能不存在
def _rain_nc_name() -> str:
    """格網雨量檔名（檔名含事件資訊，不寫死在程式中）：從 .ext 的 [Meteo] forcingFile 讀出"""
    ext = DFLOWFM_DIR / "NWT_KL_bnd.ext"
    if ext.exists():
        for line in ext.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip().lower() == "forcingfile" and value.strip().lower().endswith(".nc"):
                return value.strip()
    return "<格網雨量>.nc"


RAIN_NC_NAME = _rain_nc_name()
RAIN_NC = DFLOWFM_DIR / RAIN_NC_NAME
RAIN_NC_SKIP_REASON = (
    f"找不到測試雨量檔 {RAIN_NC_NAME}（不進 Git）。"
    "請從 D3D_run_module_handoff.zip 或原模型的 DIMR\\dflowfm\\ 複製到 tests/fixtures/NWT_KL/dflowfm/"
)


# 真實模型測試資料不進 Git（公開儲存庫，docs/OVERVIEW.md 待決事項 D2），換電腦時可能不存在
MODEL_FIXTURES_PRESENT = (DFLOWFM_DIR / "NWT_KL_v2.mdu").exists()
MODEL_FIXTURES_SKIP_REASON = (
    "找不到真實模型測試資料 tests/fixtures/NWT_KL/、runs/（不進 Git）。"
    "請從 D3D_run_module_handoff.zip 解壓到 tests/fixtures/"
)
requires_model_fixtures = pytest.mark.skipif(not MODEL_FIXTURES_PRESENT, reason=MODEL_FIXTURES_SKIP_REASON)


@pytest.fixture
def rain_nc() -> Path:
    """測試雨量檔路徑；檔案不存在時略過該測試（不算失敗）"""
    if not RAIN_NC.exists():
        pytest.skip(RAIN_NC_SKIP_REASON)
    return RAIN_NC


@pytest.fixture
def nwt_kl_dir(tmp_path) -> Path:
    """把 fixtures/NWT_KL 複製到暫存資料夾，回傳複本路徑（測試可任意修改）。

    雨量檔若存在也會一併複製；不存在時複本中就沒有它，需要它的測試請另外要求 rain_nc。
    """
    if not MODEL_FIXTURES_PRESENT:
        pytest.skip(MODEL_FIXTURES_SKIP_REASON)
    dest = tmp_path / "NWT_KL"
    shutil.copytree(NWT_KL_DIR, dest)
    return dest
