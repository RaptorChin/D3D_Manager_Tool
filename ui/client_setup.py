"""第一次啟動時準備 Flet 畫面引擎（flet.exe 與 Flutter 執行檔，約 100 MB、壓縮後 42 MB）。

為什麼不直接包進 exe：畫面引擎佔掉打包檔的七成，包進去 exe 會超過 60 MB。
v2.0.0-beta2 起改成 exe 只放程式本身，畫面引擎第一次啟動時才準備，之後每次直接使用：

  1. 已解壓在 %USERPROFILE%\\.flet\\client\\flet-desktop-full-<版本>\\ → 直接使用（Flet 本身就會找這裡）
  2. exe 旁邊有 flet-windows.zip → 解壓後使用（不需上網，適合無法連外的電腦）
  3. 都沒有 → 詢問使用者後，從本專案 GitHub Release 下載 flet-windows.zip

flet-windows.zip 由 build_exe.py --client 產生（已換成本程式的圖示與名稱），
上傳到 Release「flet-runtime-<Flet 版本>」。升級 Flet 時要重新產生並上傳。
"""
from __future__ import annotations

import ctypes
import shutil
import sys
import tempfile
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Callable

import flet_desktop.version

FLET_VERSION = flet_desktop.version.version
ARCHIVE_NAME = "flet-windows.zip"
RUNTIME_TAG = f"flet-runtime-{FLET_VERSION}"
DOWNLOAD_URL = (
    f"https://github.com/RaptorChin/D3D_Manager_Tool/releases/download/{RUNTIME_TAG}/{ARCHIVE_NAME}"
)
APPROX_SIZE_MB = 42

# Windows MessageBox 參數
_MB_OK, _MB_OKCANCEL = 0x0, 0x1
_MB_ICONERROR, _MB_ICONINFORMATION = 0x10, 0x40
_MB_TOPMOST = 0x40000
_IDOK = 1


def client_cache_dir() -> Path:
    """Flet 找畫面引擎的位置（與 flet_desktop.ensure_client_cached 相同規則；Windows 固定 full 版）"""
    return Path.home() / ".flet" / "client" / f"flet-desktop-full-{FLET_VERSION}"


def is_client_ready(cache_dir: Path | None = None) -> bool:
    cache_dir = cache_dir or client_cache_dir()
    return (cache_dir / "flet" / "flet.exe").is_file()


def local_archive() -> Path | None:
    """exe（或原始碼執行時的專案資料夾）旁邊的 flet-windows.zip"""
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    path = base / ARCHIVE_NAME
    return path if path.is_file() else None


def extract_client(archive: Path, cache_dir: Path | None = None) -> Path:
    """解壓到暫存資料夾，確認內容正確後再改名成正式位置，避免解壓到一半被當成可用。"""
    cache_dir = cache_dir or client_cache_dir()
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = cache_dir.parent / f"{cache_dir.name}.{uuid.uuid4().hex[:8]}"
    try:
        with zipfile.ZipFile(archive) as zf:
            for name in zf.namelist():  # 防止壓縮檔內含 ..\ 之類跳出資料夾的路徑
                target = (temp_dir / name).resolve()
                if not target.is_relative_to(temp_dir.resolve()):
                    raise ValueError(f"壓縮檔內含不安全的路徑：{name}")
            zf.extractall(temp_dir)
        if not is_client_ready(temp_dir):
            raise ValueError(f"{archive.name} 內容不正確（找不到 flet\\flet.exe）")
        try:
            temp_dir.rename(cache_dir)
        except OSError:
            if not is_client_ready(cache_dir):  # 同時開了兩個程式、另一個已先完成時不算失敗
                raise
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return cache_dir


def download_archive(url: str = DOWNLOAD_URL) -> Path:
    """下載到系統暫存資料夾；使用 Windows 的 Proxy 與憑證設定（urllib 預設行為）"""
    dest = Path(tempfile.gettempdir()) / f"{ARCHIVE_NAME}.{uuid.uuid4().hex[:8]}"
    try:
        with urllib.request.urlopen(url, timeout=60) as response, open(dest, "wb") as f:
            shutil.copyfileobj(response, f, length=1024 * 1024)
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    return dest


def _message_box(text: str, flags: int) -> int:
    from ui.theme import APP_NAME

    return ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, flags | _MB_TOPMOST)


def ensure_client(
    ask: Callable[[str], bool] | None = None,
    notify_error: Callable[[str], None] | None = None,
    download: Callable[[], Path] = download_archive,
    cache_dir: Path | None = None,
    archive: Path | None = None,
) -> bool:
    """確保畫面引擎可用。回傳 False 代表使用者取消或準備失敗，程式應直接結束。
    ask / notify_error / download / cache_dir / archive 可替換，方便測試。"""
    cache_dir = cache_dir or client_cache_dir()
    if is_client_ready(cache_dir):
        return True

    ask = ask or (lambda text: _message_box(text, _MB_OKCANCEL | _MB_ICONINFORMATION) == _IDOK)
    notify_error = notify_error or (lambda text: _message_box(text, _MB_OK | _MB_ICONERROR))

    archive = archive or local_archive()
    downloaded = None
    try:
        if archive is None:
            if not ask(
                "第一次在這台電腦開啟本程式，需要先下載畫面元件"
                f"（約 {APPROX_SIZE_MB} MB，只需要下載一次）。\n\n"
                "按「確定」開始下載，完成後程式會自動開啟，約需 1～2 分鐘，請稍候。\n"
                "下載期間不會顯示視窗，請勿重複開啟程式。"
            ):
                return False
            archive = downloaded = download()
        extract_client(archive, cache_dir)
        return True
    except Exception as error:
        notify_error(
            f"畫面元件準備失敗：\n{error}\n\n"
            "可改用手動方式：\n"
            f"1. 用瀏覽器下載 {DOWNLOAD_URL}\n"
            f"2. 把下載的 {ARCHIVE_NAME} 放在本程式（.exe）的同一個資料夾\n"
            "3. 重新開啟本程式"
        )
        return False
    finally:
        if downloaded is not None:
            downloaded.unlink(missing_ok=True)


if __name__ == "__main__":  # 手動測試：python -m ui.client_setup
    print("畫面引擎位置：", client_cache_dir(), "（已就緒）" if is_client_ready() else "（尚未準備）")
    sys.exit(0 if ensure_client() else 1)
