"""打包需要的圖示檔存在，且 ui 模組不會被 core 引用（core 不得依賴 UI）"""
from pathlib import Path

from PIL import Image

from ui import theme

ROOT = Path(__file__).resolve().parent.parent


def test_icon_assets_exist():
    assets = theme.assets_dir()
    ico = assets / "icon.ico"
    png = assets / "icon.png"
    assert ico.exists() and png.exists()
    sizes = Image.open(ico).info.get("sizes")
    assert (16, 16) in sizes and (256, 256) in sizes
    assert Image.open(png).mode == "RGBA"   # 四角透明


def test_core_does_not_import_ui():
    for py in (ROOT / "core").rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for banned in ("import flet", "from ui", "import ui", "customtkinter", "import tkinter"):
            assert banned not in text, f"{py.name} 不可引用 UI 套件（{banned}）"
