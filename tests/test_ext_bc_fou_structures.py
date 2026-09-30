"""ExtFile、BcFile、FouFile、StructuresFile：SPEC P1 驗收條件"""
from datetime import datetime

from conftest import DFLOWFM_DIR, RAIN_NC_NAME, requires_model_fixtures
from core.model_files import BcFile, ExtFile, FouFile, StructuresFile


# ── ExtFile ─────────────────────────────────────
@requires_model_fixtures
def test_ext_duplicate_blocks():
    ext = ExtFile.load(DFLOWFM_DIR / "NWT_KL_bnd.ext")
    assert len(ext.blocks_of("Boundary")) == 2
    assert len(ext.blocks_of("Meteo")) == 1
    node_ids = [b.get("nodeId") for b in ext.blocks_of("boundary")]
    assert len(set(node_ids)) == 2 and all(node_ids)   # 兩個不同的 1D 節點


@requires_model_fixtures
def test_ext_meteo_info():
    meteo = ExtFile.load(DFLOWFM_DIR / "NWT_KL_bnd.ext").meteo_blocks()[0]
    assert meteo.quantity == "rainfall"
    assert meteo.forcing_file == RAIN_NC_NAME and RAIN_NC_NAME.endswith(".nc")
    assert meteo.forcing_file_type == "netcdf"
    assert meteo.forcing_variable_name == "rainfall"   # 原檔是 `forcingVariableName = rainfall`（有空白）


@requires_model_fixtures
def test_ext_referenced_files_relative_to_base_dir(tmp_path):
    ext = ExtFile.load(DFLOWFM_DIR / "NWT_KL_bnd.ext")
    files = {(b.type, key, p.name) for b, key, p in ext.referenced_files()}
    assert files == {
        ("Boundary", "forcingFile", "NWT_KL_boundaryconditions1d.bc"),
        ("Meteo", "forcingFile", RAIN_NC_NAME),
    }
    assert all(p.parent == DFLOWFM_DIR.resolve() for _, _, p in ext.referenced_files())
    other = ExtFile.load(DFLOWFM_DIR / "NWT_KL_bnd.ext", base_dir=tmp_path)
    assert all(p.parent == tmp_path.resolve() for _, _, p in other.referenced_files())


def test_ext_commented_out_block_is_disabled():
    text = (
        "[General]\nfileVersion=2.02\n\n"
        "[Meteo]\nquantity=rainfall\nforcingFile=a.nc\n\n"
        "#[Meteo]\n#quantity=rainfall_rate\n#forcingFile=NWT_KL_meteo.bc\n\n"
        "[Boundary]\nnodeId=1\n"
    )
    ext = ExtFile(text)
    assert [(b.type, b.enabled) for b in ext.blocks] == [("Meteo", True), ("Meteo", False), ("Boundary", True)]
    assert len(ext.meteo_blocks()) == 1
    disabled = ext.meteo_blocks(include_disabled=True)[1]
    assert disabled.quantity == "rainfall_rate" and disabled.forcing_file == "NWT_KL_meteo.bc"
    assert len(ext.referenced_files()) == 1


# ── BcFile ──────────────────────────────────────
@requires_model_fixtures
def test_bc_meteo_time_range():
    bc = BcFile.load(DFLOWFM_DIR / "NWT_KL_meteo.bc")
    f = bc.forcings[0]
    assert f.name == "global" and f.is_time_series
    assert f.quantities == ["time", "rainfall_rate"]
    assert f.units == ["seconds since 2000-01-01 00:00:00", "mm day-1"]
    assert f.time_range() == (datetime(2000, 1, 1, 0, 0), datetime(2000, 1, 1, 6, 0))


@requires_model_fixtures
def test_bc_constant_forcings_have_no_time_range():
    bc = BcFile.load(DFLOWFM_DIR / "NWT_KL_boundaryconditions1d.bc")   # 縮排格式、小寫 [forcing]
    assert len(bc.forcings) == 2
    assert [f.function for f in bc.forcings] == ["constant", "constant"]
    assert all(f.time_range() is None for f in bc.forcings)
    assert bc.forcing(bc.forcings[1].name.upper()).rows == [[3.05]]   # 依名稱查詢（不分大小寫）


def test_bc_time_reference_units():
    text = (
        "[Forcing]\nname = a\nfunction = timeseries\nquantity = time\nunit = hours since 2021-06-04\n"
        "quantity = x\nunit = m\n1 0\n25 0\n"
    )
    assert BcFile(text).forcings[0].time_range() == (datetime(2021, 6, 4, 1), datetime(2021, 6, 5, 1))


# ── FouFile ─────────────────────────────────────
@requires_model_fixtures
def test_fou_old_and_new():
    old = FouFile.load(DFLOWFM_DIR / "Maxima_old.fou")
    assert (old.entry("wd").tstart, old.entry("wd").tstop) == (0, 21600)
    new = FouFile.load(DFLOWFM_DIR / "Maxima.fou")
    assert (new.entry("wd").tstart, new.entry("wd").tstop) == (-1, -1)
    assert all(e.uses_full_period for e in new.entries)
    assert [e.quantity for e in new.entries] == ["wd", "wl"]


# ── StructuresFile ──────────────────────────────
@requires_model_fixtures
def test_structures_counts_and_chinese_name():
    s = StructuresFile.load(DFLOWFM_DIR / "structures.ini")
    assert len(s.structures) == 183
    assert s.type_counts() == {"pump": 118, "orifice": 57, "bridge": 6, "weir": 2}
    # 含中文名稱的結構物要能正確讀出（不可變成亂碼）
    assert any(any("\u4e00" <= ch <= "\u9fff" for ch in (x.name or "")) for x in s.structures)


@requires_model_fixtures
def test_structures_all_constant_values():
    s = StructuresFile.load(DFLOWFM_DIR / "structures.ini")
    assert all(not x.time_series_params() for x in s.structures)
    pump = s.of_type("pump")[0]
    assert pump.get_float("capacity") is not None


def test_structures_time_series_param_detected():
    s = StructuresFile("[Structure]\nid = P1\ntype = pump\ncapacity = pump_q.bc\n")
    assert s.by_id("P1").time_series_params() == [("capacity", "pump_q.bc")]
