"""git_control 遠端位址處理（2026-09-29 修正：開頭少了 \\\\ 的內網路徑被當成網址，推送時 LFS 報 missing protocol）"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from core.git_control import GitModelManager as G

BS = "\\"


@pytest.mark.parametrize("raw, expected", [
    # 正確的 UNC
    (BS * 2 + r"fileserver\proj\Models(Git control)\Model(10m)", "//fileserver/proj/Models(Git control)/Model(10m)"),
    # 開頭少了 \\（本次錯誤的原因）
    (r"fileserver\Models(Git control)\Model(10m)", "//fileserver/Models(Git control)/Model(10m)"),
    # 開頭只有一個 \
    (BS + r"fileserver\Models\Model", "//fileserver/Models/Model"),
    # 前後有引號或空白
    ('  "' + BS * 2 + r'srv\share\p"  ', "//srv/share/p"),
    # 本機磁碟、網址維持原本規則
    (r"D:\repos\model", "D:/repos/model"),
    ("https://github.com/u/p.git", "https://github.com/u/p.git"),
    ("git@github.com:u/p.git", "git@github.com:u/p.git"),
    ("//srv/share/p", "//srv/share/p"),
])
def test_normalize_remote_url(raw, expected):
    normalized = G.normalize_remote_url(raw)
    assert normalized == expected
    is_fs = not expected.startswith(("https:", "git@"))
    assert G.is_filesystem_remote(normalized) is is_fs


def _unc_available(path: Path) -> bool:
    return os.path.isdir(BS * 2 + "localhost" + BS + path.drive[0] + "$" + BS)


@pytest.mark.skipif(not shutil.which("git") or not shutil.which("git-lfs"), reason="需要 Git 與 Git LFS")
def test_push_heals_unc_remote_missing_leading_slashes(tmp_path, monkeypatch):
    """重現實際錯誤：origin 存成「localhost\\C$\\...」（少了 \\\\），推送應自動修正並成功"""
    if not _unc_available(tmp_path):
        pytest.skip("此電腦無法以 \\\\localhost\\C$ 存取本機（需系統管理共用）")
    for k, v in {"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "test",
                 "GIT_COMMITTER_EMAIL": "t@t"}.items():
        monkeypatch.setenv(k, v)

    proj = tmp_path / "proj"
    (proj / "M.dsproj_data" / "input").mkdir(parents=True)
    (proj / "M.dsproj").write_text("dsproj")
    (proj / "M.dsproj_data" / "input" / "M.mdu").write_text("[time]\nTStop = 1\n")
    share = tmp_path / "share"
    share.mkdir()

    mgr = G(str(proj))
    mgr.do_initial_setup(lambda text, pct: None)

    broken = "localhost" + BS + share.drive[0] + "$" + BS + str(share)[3:]   # 少了開頭的 \\
    subprocess.run(["git", "remote", "add", "origin", broken], cwd=proj, check=True)

    warning = mgr.push_with_progress(lambda text, pct: None)

    assert warning is None
    assert (share / G.REMOTE_HISTORY_DIRNAME / "HEAD").exists()
    assert (share / "M.dsproj").exists()
    assert (share / "M.dsproj_data" / "input" / "M.mdu").exists()
    assert mgr.get_remote_url().startswith("//localhost/")


def test_missing_network_share_gives_friendly_message(tmp_path):
    """共用資料夾名稱打錯（WinError 67）時，顯示中文說明而非原始系統錯誤"""
    if not _unc_available(tmp_path):
        pytest.skip("此電腦無法以 \\localhost 存取網路路徑")
    mgr = G(str(tmp_path))
    with pytest.raises(Exception) as info:
        mgr.ensure_filesystem_remote("//localhost/NoSuchShare_D3DTest/proj")
    msg = str(info.value)
    assert "找不到網路共用資料夾" in msg
    assert BS * 2 + "localhost" + BS + "NoSuchShare_D3DTest" in msg
    assert "瀏覽" in msg
