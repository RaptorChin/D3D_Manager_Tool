"""第一次啟動準備畫面引擎（ui/client_setup.py）：不連網、不跳真的對話框，一律用 tmp_path 模擬"""
import zipfile

from ui import client_setup as cs


def make_archive(path, with_exe=True, extra=None):
    with zipfile.ZipFile(path, "w") as zf:
        if with_exe:
            zf.writestr("flet/flet.exe", b"fake exe")
        zf.writestr("flet/data/app.so", b"fake data")
        for name, data in (extra or {}).items():
            zf.writestr(name, data)
    return path


def never_ask(text):
    raise AssertionError("不應該詢問使用者")


def test_ready_cache_does_nothing(tmp_path):
    cache = tmp_path / "flet-desktop-full-x"
    (cache / "flet").mkdir(parents=True)
    (cache / "flet" / "flet.exe").write_bytes(b"x")
    assert cs.ensure_client(ask=never_ask, download=lambda: never_ask(""), cache_dir=cache)


def test_local_archive_extracted_without_asking(tmp_path):
    cache = tmp_path / "client" / "flet-desktop-full-x"
    archive = make_archive(tmp_path / "flet-windows.zip")
    assert cs.ensure_client(ask=never_ask, cache_dir=cache, archive=archive)
    assert cs.is_client_ready(cache)
    assert (cache / "flet" / "data" / "app.so").read_bytes() == b"fake data"
    assert [p.name for p in cache.parent.iterdir()] == [cache.name]  # 暫存資料夾已清掉


def test_download_after_user_agrees_and_temp_file_removed(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "local_archive", lambda: None)  # exe 旁邊沒有 zip
    cache = tmp_path / "client" / "flet-desktop-full-x"
    downloaded = make_archive(tmp_path / "download.tmp")
    asked = []
    ok = cs.ensure_client(ask=lambda text: asked.append(text) or True, download=lambda: downloaded,
                          cache_dir=cache)
    assert ok and len(asked) == 1 and "42 MB" in asked[0]
    assert cs.is_client_ready(cache)
    assert not downloaded.exists()


def test_user_cancels_download(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "local_archive", lambda: None)
    cache = tmp_path / "flet-desktop-full-x"
    assert not cs.ensure_client(ask=lambda text: False, download=lambda: never_ask(""), cache_dir=cache)
    assert not cache.exists()


def test_bad_archive_reports_error_and_leaves_no_cache(tmp_path):
    cache = tmp_path / "client" / "flet-desktop-full-x"
    archive = make_archive(tmp_path / "flet-windows.zip", with_exe=False)
    errors = []
    assert not cs.ensure_client(ask=never_ask, notify_error=errors.append, cache_dir=cache, archive=archive)
    assert "flet.exe" in errors[0] and cs.DOWNLOAD_URL in errors[0]
    assert not cache.exists() and list(cache.parent.iterdir()) == []


def test_unsafe_path_in_archive_rejected(tmp_path):
    cache = tmp_path / "client" / "flet-desktop-full-x"
    archive = make_archive(tmp_path / "evil.zip", extra={"../../evil.txt": b"x"})
    errors = []
    assert not cs.ensure_client(ask=never_ask, notify_error=errors.append, cache_dir=cache, archive=archive)
    assert "不安全" in errors[0]
    assert not (tmp_path / "evil.txt").exists()


def test_download_failure_reports_manual_steps(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "local_archive", lambda: None)

    def fail():
        raise OSError("連線逾時")

    errors = []
    assert not cs.ensure_client(ask=lambda text: True, notify_error=errors.append, download=fail,
                                cache_dir=tmp_path / "c")
    assert "連線逾時" in errors[0] and "同一個資料夾" in errors[0]


def test_cache_dir_matches_flet_rule():
    """與 Flet 自己找畫面引擎的位置一致，否則解壓了 Flet 也找不到"""
    import flet_desktop

    assert cs.client_cache_dir() == getattr(flet_desktop, "__get_client_storage_dir")()
