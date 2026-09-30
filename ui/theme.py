"""共用配色、字型與小元件（依 docs/UI_PLAN.md §1）。

注意 Flet 0.86.5 的 API 與舊文件差很多（踩坑表見 UI_PLAN.md §6）：
- 8 碼色碼是 #AARRGGBB，半透明請用 ft.Colors.with_opacity()
- 中文不要用 italic（微軟正黑體沒有斜體，會變形）
"""
from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

APP_NAME = "D-Flow 模式檔案管理系統"
APP_VERSION = "2.0.0"

FONT = "Microsoft JhengHei"
FONT_CODE = "Consolas"

# ── 配色 ───────────────────────────────────────────
BG = "#0f1420"
CARD = "#1a2033"
CARD_HI = "#20283f"
FIELD = "#232a44"
BORDER = "#2a3350"
TEXT = "#e6ecff"
MUTED = "#8592b0"
LINK = "#7fd0ff"

# 按鈕語意色（沿用 v1.x 的色彩語意：藍＝一般、綠＝下載/推送、紅＝危險、灰＝次要）
PRIMARY = "#2f6fed"
SUCCESS = "#22a55e"
DANGER = "#e5484d"
WARNING = "#f0ad4e"
SECONDARY = "#5a5a5a"

# 三大工作區代表色
ACCENT_BUILD = "#3ba7ff"
ACCENT_RUN = "#f0ad4e"
ACCENT_RESULTS = "#34d399"


def assets_dir() -> Path:
    """assets 資料夾：原始碼執行時在專案根目錄；flet pack 打包後在 PyInstaller 的暫存解壓目錄"""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets"


# ── 小元件 ─────────────────────────────────────────
def card(content, padding=18, expand=False):
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=CARD,
        border_radius=14,
        border=ft.Border.all(1, BORDER),
        expand=expand,
    )


def pill_button(text, icon, bgcolor=PRIMARY, on_click=None, disabled=False):
    return ft.Button(
        content=text,
        icon=icon,
        bgcolor=bgcolor,
        color="#ffffff",
        disabled=disabled,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            elevation=0,
        ),
        on_click=on_click,
    )


def outline_button(text, icon, on_click=None):
    return ft.OutlinedButton(
        content=text,
        icon=icon,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=on_click,
    )


def badge(text, color):
    return ft.Container(
        content=ft.Text(text, size=11, color=color, weight=ft.FontWeight.W_600),
        padding=ft.Padding.symmetric(horizontal=10, vertical=3),
        border_radius=20,
        border=ft.Border.all(1, color),
    )


def section_title(text, icon, accent):
    return ft.Row(
        [ft.Icon(icon, color=accent, size=20), ft.Text(text, size=15, weight=ft.FontWeight.BOLD, color="#ffffff")],
        spacing=8,
    )


def caption(text):
    return ft.Text(text, size=12, color=MUTED)


def text_field(label, value="", multiline=False, width=None, expand=False, hint=None):
    return ft.TextField(
        label=label,
        value=value,
        hint_text=hint,
        multiline=multiline,
        min_lines=3 if multiline else None,
        max_lines=6 if multiline else None,
        border_radius=10,
        filled=True,
        bgcolor=FIELD,
        width=width,
        expand=expand,
    )


def dropdown(options, value=None, width=280, on_select=None, hint="(請先選擇工作資料夾)"):
    return ft.Dropdown(
        width=width,
        value=value,
        hint_text=hint,
        options=[ft.dropdown.Option(o) for o in options],
        border_radius=10,
        bgcolor=FIELD,
        border=ft.Border.all(1, BORDER),
        on_select=on_select,
    )


def set_dropdown_options(dd: ft.Dropdown, options: list[str], value: str | None):
    dd.options = [ft.dropdown.Option(o) for o in options]
    dd.value = value
