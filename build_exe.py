"""打包 D-Flow 模式檔案管理系統 v2.0（Flet 版）。

使用方式（在專案資料夾執行）：
    python build_exe.py            → 先跑測試，再產生 dist\\D3D_Manager_Tool.exe（約 19 MB）
    python build_exe.py --client   → 另外產生 dist\\flet-windows.zip（畫面引擎，約 42 MB）
    python build_exe.py --skip-tests

為什麼不直接用 flet pack：flet pack 會把畫面引擎（flet-windows.zip，42 MB）包進 exe，
使 exe 超過 60 MB。這裡沿用 flet pack 的做法（換掉 flet.exe 的圖示與版本資訊），
但不把畫面引擎放進 exe；程式第一次啟動時由 ui/client_setup.py 下載或解壓。

flet-windows.zip 只有升級 Flet 或更換圖示時才需要重新產生，產生後上傳到 GitHub Release
「flet-runtime-<Flet 版本>」（網址見 ui/client_setup.py 的 DOWNLOAD_URL）。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "D3D_Manager_Tool"
ICON = ROOT / "assets" / "icon.ico"

# 目前程式沒有用到、但會被 PyInstaller 一起收進去的套件（合計約 40 MB）。
# M2 開始讀雨量 NetCDF 檔時，netCDF4／numpy／cftime 要從這裡移除（exe 會再增加約 30 MB）。
EXCLUDES = ["netCDF4", "numpy", "cftime", "PIL", "tkinter", "customtkinter", "pytest", "_pytest"]


def app_version() -> str:
    sys.path.insert(0, str(ROOT))
    from ui.theme import APP_VERSION

    return APP_VERSION


def run_tests():
    print("[1/3] 執行測試...")
    if subprocess.call([sys.executable, "-m", "pytest", "-q"], cwd=ROOT) != 0:
        sys.exit("測試未通過，已停止打包。請先修正錯誤。")


def prepare_client(version: str) -> tuple[str, str]:
    """複製一份畫面引擎，換成本程式的圖示與名稱。回傳（引擎暫存資料夾, exe 用的版本資訊檔）"""
    from flet_cli.__pyinstaller.utils import copy_flet_bin
    from flet_cli.__pyinstaller.win_utils import update_flet_view_icon, update_flet_view_version_info

    print("[2/3] 準備畫面引擎（換圖示與版本資訊）...")
    temp_bin_dir = copy_flet_bin()
    if temp_bin_dir is None:
        sys.exit("找不到 Flet 畫面引擎。請先執行一次 python app.py 讓 Flet 下載後再打包。")
    flet_exe = os.path.join(temp_bin_dir, "flet", "flet.exe")
    update_flet_view_icon(flet_exe, str(ICON))
    version_file = update_flet_view_version_info(
        exe_path=flet_exe,
        product_name="D-Flow 模式檔案管理系統",
        file_description="D-Flow 模式檔案管理系統",
        product_version=version,
        file_version=f"{version}.0",
        company_name=None,
        copyright=None,
    )
    return temp_bin_dir, version_file


def zip_client(temp_bin_dir: str, dist: Path) -> Path:
    """壓成 flet-windows.zip，內部結構 flet\\flet.exe…（與 Flet 官方發佈檔相同）"""
    archive = dist / "flet-windows.zip"
    flet_dir = Path(temp_bin_dir) / "flet"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(flet_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(temp_bin_dir))
    return archive


def build_exe(version_file: str, dist: Path):
    import PyInstaller.__main__

    import flet_cli.__pyinstaller.config as hook_config

    print("[3/3] 打包 exe（約 1 分鐘）...")
    # Flet 的 PyInstaller hook 會把 hook_config.temp_bin_dir 整個收進 exe；
    # 指向空資料夾 → 不收畫面引擎（改由 ui/client_setup.py 在執行時準備）
    empty_dir = tempfile.mkdtemp(prefix="flet_no_client_")
    hook_config.temp_bin_dir = empty_dir
    work = ROOT / "build"
    shutil.rmtree(work, ignore_errors=True)
    args = [
        str(ROOT / "app.py"),
        "--noconfirm", "--noconsole", "--onefile",
        "--name", NAME,
        "--icon", str(ICON),
        "--add-data", f"{ROOT / 'assets'};assets",
        "--distpath", str(dist),
        "--workpath", str(work),
        "--specpath", str(work),
        "--version-file", version_file,
    ]
    for module in EXCLUDES:
        args += ["--exclude-module", module]
    try:
        PyInstaller.__main__.run(args)
    finally:
        shutil.rmtree(empty_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="打包 D-Flow 模式檔案管理系統")
    parser.add_argument("--client", action="store_true", help="另外產生 dist\\flet-windows.zip（畫面引擎）")
    parser.add_argument("--skip-tests", action="store_true", help="不先執行測試")
    options = parser.parse_args()

    os.chdir(ROOT)
    if not options.skip_tests:
        run_tests()
    version = app_version()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)

    temp_bin_dir, version_file = prepare_client(version)
    try:
        if options.client:
            archive = zip_client(temp_bin_dir, dist)
            print(f"畫面引擎：{archive}（{archive.stat().st_size / 1e6:.1f} MB）")
        build_exe(version_file, dist)
    finally:
        shutil.rmtree(temp_bin_dir, ignore_errors=True)
        Path(version_file).unlink(missing_ok=True)

    exe = dist / f"{NAME}.exe"
    print(f"\n完成！執行檔：{exe}（{exe.stat().st_size / 1e6:.1f} MB）")


if __name__ == "__main__":
    main()
