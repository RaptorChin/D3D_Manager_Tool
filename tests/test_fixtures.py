"""確認測試資料齊全（M0 建立；缺檔時其他測試的失敗原因會很難看懂，所以先在這裡擋下）"""
from conftest import DFLOWFM_DIR, NWT_KL_DIR, RUNS_DIR, requires_model_fixtures

pytestmark = requires_model_fixtures  # 整個檔案都用到真實模型測試資料

# 應存在的真實模型測試資料（見 tests/fixtures/README.md；不進 Git）；雨量 nc 不在此列
EXPECTED_FILES = [
    NWT_KL_DIR / "dimr_config.xml",
    NWT_KL_DIR / "run_original_wrong.bat",
    DFLOWFM_DIR / "NWT_KL_v1.mdu",
    DFLOWFM_DIR / "NWT_KL_v2.mdu",
    DFLOWFM_DIR / "NWT_KL_bnd.ext",
    DFLOWFM_DIR / "NWT_KL_meteo.bc",
    DFLOWFM_DIR / "NWT_KL_boundaryconditions1d.bc",
    DFLOWFM_DIR / "Maxima_old.fou",
    DFLOWFM_DIR / "Maxima.fou",
    DFLOWFM_DIR / "structures.ini",
    RUNS_DIR / "dimr_run_log.txt",
    RUNS_DIR / "NWT_KL_0000_init.dia",
    RUNS_DIR / "partition_log_failed.txt",
]


def test_fixture_files_exist():
    missing = [str(p) for p in EXPECTED_FILES if not p.exists()]
    assert not missing, "缺少測試資料：\n" + "\n".join(missing)


def test_mdu_fixtures_use_crlf():
    # 逐位元組 round-trip 測試（P1）依賴原檔的 CRLF；若被 Git 轉成 LF 會讓測試失去意義
    for name in ("NWT_KL_v1.mdu", "NWT_KL_v2.mdu"):
        data = (DFLOWFM_DIR / name).read_bytes()
        assert b"\r\n" in data, f"{name} 應為 CRLF 換行"


def test_rain_nc_fixture(rain_nc):
    # 雨量檔不存在時此測試會顯示為「略過」，屬正常情況
    assert rain_nc.stat().st_size > 10 * 1024 * 1024


def test_nwt_kl_copy_is_isolated(nwt_kl_dir):
    mdu = nwt_kl_dir / "dflowfm" / "NWT_KL_v2.mdu"
    mdu.write_bytes(b"changed")
    assert (DFLOWFM_DIR / "NWT_KL_v2.mdu").read_bytes() != b"changed"
