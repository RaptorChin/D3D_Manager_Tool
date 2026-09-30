"""MduFile：SPEC P1 驗收條件＋時間窗與路徑解析"""
import difflib
from datetime import datetime

from conftest import DFLOWFM_DIR, requires_model_fixtures
from core.model_files import MduFile


@requires_model_fixtures
def test_get_is_case_insensitive():
    mdu = MduFile.load(DFLOWFM_DIR / "NWT_KL_v2.mdu")
    assert mdu.get("time", "tstop") == "122400"
    assert mdu.get("TIME", "TStop") == "122400"
    assert mdu.get_float("Time", "TSTOP") == 122400.0


@requires_model_fixtures
def test_set_tstop_changes_only_that_line(nwt_kl_dir):
    path = nwt_kl_dir / "dflowfm" / "NWT_KL_v2.mdu"
    original = path.read_bytes()
    mdu = MduFile.load(path)
    mdu.set("time", "TStop", "39600")
    mdu.save()
    after = path.read_bytes()

    before_lines = original.decode("utf-8").splitlines(keepends=True)
    after_lines = after.decode("utf-8").splitlines(keepends=True)
    assert len(before_lines) == len(after_lines)
    changed = [i for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
    assert len(changed) == 1
    old, new = before_lines[changed[0]], after_lines[changed[0]]
    # key 大小寫、註解、註解欄位位置、CRLF 都保留
    assert new.startswith("TStop ") and "39600" in new and "122400" not in new
    assert old.index("# Stop") == new.index("# Stop")
    assert new.endswith("\r\n")
    assert after.startswith(b"# Generated on")
    assert MduFile.load(path).get("time", "tstop") == "39600"


@requires_model_fixtures
def test_unmodified_save_is_byte_identical(tmp_path):
    for name in ("NWT_KL_v1.mdu", "NWT_KL_v2.mdu"):
        src = DFLOWFM_DIR / name
        out = MduFile.load(src).save(tmp_path / name)
        assert out.read_bytes() == src.read_bytes()


@requires_model_fixtures
def test_time_window_from_tstart_tstop():
    mdu = MduFile.load(DFLOWFM_DIR / "NWT_KL_v2.mdu")
    # RefDate 2021-06-04，TStart 36000 s、TStop 122400 s
    assert mdu.time_window() == (datetime(2021, 6, 4, 10), datetime(2021, 6, 5, 10))


def test_time_window_tunit_hours():
    mdu = MduFile("[time]\nRefDate = 20210604\nTunit = H\nTStart = 10\nTStop = 34\n")
    assert mdu.time_window() == (datetime(2021, 6, 4, 10), datetime(2021, 6, 5, 10))


def test_time_window_prefers_start_stop_datetime():
    mdu = MduFile(
        "[time]\nRefDate = 20210604\nTunit = S\nTStart = 0\nTStop = 21600\n"
        "StartDateTime = 20210605000000\nStopDateTime = 20210606000000\n"
    )
    assert mdu.time_window() == (datetime(2021, 6, 5), datetime(2021, 6, 6))


def test_empty_start_datetime_falls_back_to_tstart():
    mdu = MduFile("[time]\nRefDate = 20210604\nTStart = 3600\nTStop = 7200\nStartDateTime =   # c\n")
    assert mdu.time_window()[0] == datetime(2021, 6, 4, 1)


@requires_model_fixtures
def test_referenced_paths_are_absolute_relative_to_mdu():
    path = DFLOWFM_DIR / "NWT_KL_v2.mdu"
    mdu = MduFile.load(path)
    assert mdu.net_file == (DFLOWFM_DIR / "FlowFM_net.nc").resolve()
    assert mdu.ext_file_new == (DFLOWFM_DIR / "NWT_KL_bnd.ext").resolve()
    assert mdu.ext_file_old is None           # ExtForceFile 空白
    assert mdu.fou_file == (DFLOWFM_DIR / "Maxima.fou").resolve()
    assert mdu.structure_file == (DFLOWFM_DIR / "structures.ini").resolve()
    assert mdu.output_dir == (DFLOWFM_DIR / "output").resolve()


def test_default_output_dir():
    mdu = MduFile("[output]\nOutputDir =\n", path="D:/m/Model.mdu")
    assert mdu.output_dir.name == "DFM_OUTPUT_Model"


@requires_model_fixtures
def test_v1_output_settings():
    mdu = MduFile.load(DFLOWFM_DIR / "NWT_KL_v1.mdu")
    assert mdu.get_float("output", "MapInterval") == 60
    assert mdu.get_float("time", "DtUser") == 300
    assert mdu.get("output", "NcFormat") == "3"
