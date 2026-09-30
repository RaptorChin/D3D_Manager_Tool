"""DimrConfig：讀取與 set_parallel（只改 <process> / <mpiCommunicator>，其餘逐位元組保留）"""
import pytest

from conftest import NWT_KL_DIR, requires_model_fixtures
from core.model_files import DimrConfig

pytestmark = requires_model_fixtures  # 整個檔案都用到真實模型測試資料

SRC = NWT_KL_DIR / "dimr_config.xml"


def _without_parallel_lines() -> str:
    text = SRC.read_bytes().decode("utf-8")
    lines = text.splitlines(keepends=True)
    return "".join(l for l in lines if "<process>" not in l and "<mpiCommunicator>" not in l)


def test_read_fixture():
    cfg = DimrConfig.load(SRC)
    assert cfg.working_dir == "dflowfm"
    assert cfg.input_file == "NWT_KL.mdu"
    assert cfg.processes == list(range(8))
    assert cfg.flow_component.mpi_communicator == "DFM_COMM_DFMWORLD"
    assert cfg.flow_component.settings == {"threads": "1"}
    assert cfg.other_components == []


def test_unmodified_save_is_byte_identical(tmp_path):
    out = DimrConfig.load(SRC).save(tmp_path / "dimr_config.xml")
    assert out.read_bytes() == SRC.read_bytes()


def test_set_parallel_same_value_keeps_bytes(tmp_path):
    cfg = DimrConfig.load(SRC)
    cfg.set_parallel(8)
    assert cfg.save(tmp_path / "d.xml").read_bytes() == SRC.read_bytes()


def test_set_parallel_inserts_when_missing():
    cfg = DimrConfig(_without_parallel_lines())
    assert cfg.processes is None
    cfg.set_parallel(4)
    assert cfg.processes == [0, 1, 2, 3]
    assert cfg.flow_component.mpi_communicator == "DFM_COMM_DFMWORLD"
    # 插在 <inputFile> 之後，縮排比照 <inputFile>，換行為 CRLF
    assert "    <inputFile>NWT_KL.mdu</inputFile>\r\n    <process>0 1 2 3</process>\r\n" \
           "    <mpiCommunicator>DFM_COMM_DFMWORLD</mpiCommunicator>\r\n  </component>" in cfg.text


def test_set_parallel_changes_existing_values_only():
    cfg = DimrConfig.load(SRC)
    before = cfg.text
    cfg.set_parallel(4)
    assert cfg.processes == [0, 1, 2, 3]
    assert cfg.text == before.replace("<process>0 1 2 3 4 5 6 7</process>", "<process>0 1 2 3</process>")


def test_set_parallel_one_removes_process_and_communicator():
    cfg = DimrConfig.load(SRC)
    cfg.set_parallel(1)
    assert cfg.processes is None
    assert cfg.flow_component.mpi_communicator is None
    assert cfg.text == _without_parallel_lines()
    # 其餘內容（註解、命名空間）保留
    assert "<!--<control>" in cfg.text and 'xmlns="http://schemas.deltares.nl/dimr"' in cfg.text


def test_set_parallel_invalid():
    with pytest.raises(ValueError):
        DimrConfig.load(SRC).set_parallel(0)


def test_detects_other_components():
    text = SRC.read_bytes().decode("utf-8").replace(
        "</dimrConfig>",
        '  <component name="RTC">\r\n    <library>FBCTools_BMI</library>\r\n    <workingDir>rtc</workingDir>\r\n'
        '    <inputFile>.</inputFile>\r\n  </component>\r\n</dimrConfig>',
    )
    cfg = DimrConfig(text)
    assert [c.name for c in cfg.other_components] == ["RTC"]
    assert cfg.flow_component.name == "NWT_KL"
