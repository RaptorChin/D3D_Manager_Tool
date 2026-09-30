"""逐行 INI 引擎：round-trip、只改一行、新增 key／區塊、編碼"""
import difflib

import pytest

from conftest import DFLOWFM_DIR, requires_model_fixtures
from core.model_files.ini_lines import IniDocument


@requires_model_fixtures
@pytest.mark.parametrize("name", [
    "NWT_KL_v1.mdu", "NWT_KL_v2.mdu", "NWT_KL_bnd.ext", "NWT_KL_meteo.bc",
    "NWT_KL_boundaryconditions1d.bc", "structures.ini",
])
def test_unmodified_save_is_byte_identical(tmp_path, name):
    src = DFLOWFM_DIR / name
    doc = IniDocument.load(src)
    out = doc.save(tmp_path / name)
    assert out.read_bytes() == src.read_bytes()


def _changed_lines(before: bytes, after: bytes) -> list[str]:
    a = before.decode("utf-8").splitlines(keepends=True)
    b = after.decode("utf-8").splitlines(keepends=True)
    return [l for l in difflib.unified_diff(a, b, n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]


def test_set_value_keeps_comment_column_and_crlf():
    text = "[time]\r\nTStop    = 122400        # Stop time\r\nTunit = S\r\n"
    doc = IniDocument(text)
    doc.set_value("TIME", "tstop", "39600")
    assert doc.to_text() == "[time]\r\nTStop    = 39600         # Stop time\r\nTunit = S\r\n"


def test_set_value_longer_than_column_keeps_one_space():
    doc = IniDocument("[a]\nKey = 1 # c\n")
    doc.set_value("a", "key", "123456789")
    assert doc.to_text() == "[a]\nKey = 123456789 # c\n"


def test_set_empty_value_with_comment():
    # MDU 常見：值空白但有註解（例如 StatsInterval）
    doc = IniDocument("[output]\nStatsInterval   =            # Interval\n")
    doc.set_value("output", "StatsInterval", "60")
    assert doc.to_text() == "[output]\nStatsInterval   = 60         # Interval\n"
    assert doc.get("output", "statsinterval") == "60"


def test_set_value_without_comment_keeps_padding_width():
    doc = IniDocument("[General]\n    fileVersion           = 1.01                \n")
    doc.set_value("general", "fileversion", "2.00")
    assert doc.to_text() == "[General]\n    fileVersion           = 2.00                \n"


def test_insert_missing_key_after_last_key_with_same_alignment():
    doc = IniDocument("[General]\r\n    fileVersion   = 1.01\r\n    fileType      = x\r\n\r\n[Other]\r\n")
    doc.set_value("general", "newKey", "abc")
    assert doc.to_text() == (
        "[General]\r\n    fileVersion   = 1.01\r\n    fileType      = x\r\n    newKey        = abc\r\n\r\n[Other]\r\n"
    )


def test_append_missing_section():
    doc = IniDocument("[a]\nx = 1")
    doc.set_value("b", "y", "2")
    assert doc.to_text() == "[a]\nx = 1\n\n[b]\ny = 2\n"


def test_duplicate_sections_by_occurrence():
    doc = IniDocument("[Boundary]\nnodeId=1\n\n[Boundary]\nnodeId=2\n")
    assert [s.get("nodeid") for s in doc.find_sections("boundary")] == ["1", "2"]
    doc.set_value("Boundary", "nodeId", "9", occurrence=1)
    assert doc.to_text() == "[Boundary]\nnodeId=1\n\n[Boundary]\nnodeId=9\n"
    with pytest.raises(KeyError):
        doc.set_value("Boundary", "nodeId", "9", occurrence=5)


def test_get_strips_inline_comment_and_missing_returns_none():
    doc = IniDocument("[a]\nKey = value   # comment\n")
    assert doc.get("A", "KEY") == "value"
    assert doc.get("a", "nothing") is None
    assert doc.get("nosection", "key") is None


def test_cp950_file_round_trip(tmp_path):
    src = tmp_path / "big5.ini"
    data = "[Structure]\r\nname = 分洪堰測試\r\n".encode("cp950")
    src.write_bytes(data)
    doc = IniDocument.load(src)
    assert doc.encoding == "cp950"
    assert doc.get("structure", "name") == "分洪堰測試"
    doc.save()
    assert src.read_bytes() == data


def test_bom_is_preserved(tmp_path):
    src = tmp_path / "bom.ini"
    data = b"\xef\xbb\xbf[a]\nx = 1\n"
    src.write_bytes(data)
    IniDocument.load(src).save()
    assert src.read_bytes() == data
