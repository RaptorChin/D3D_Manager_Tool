"""主頁面（UI_PLAN.md §1.1）：以 3 張圖示卡片選擇工作區"""
from __future__ import annotations

from typing import Callable

import flet as ft

from . import theme as t
from .workspace import WorkspaceSpec


def app_title(right: ft.Control | None = None) -> ft.Control:
    return ft.Row(
        [
            ft.Row(
                [
                    ft.Image(src="icon.png", width=36, height=36),
                    ft.Text(t.APP_NAME, size=22, weight=ft.FontWeight.BOLD, color="#ffffff"),
                    ft.Container(
                        content=ft.Text(f"v{t.APP_VERSION}", size=12, color="#9fb3d9"),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                        bgcolor=t.FIELD,
                        border_radius=20,
                    ),
                ],
                spacing=10,
            ),
            right or ft.Container(),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )


def _home_card(ws: WorkspaceSpec, on_open: Callable[[str], None]) -> ft.Control:
    accent = ws.accent

    def on_hover(e):
        hovered = e.data in (True, "true")
        e.control.scale = 1.03 if hovered else 1.0
        e.control.bgcolor = t.CARD_HI if hovered else t.CARD
        e.control.border = ft.Border.all(2 if hovered else 1, accent if hovered else t.BORDER)
        e.control.page.update()

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [ft.Text(ws.no, size=22, color=accent, weight=ft.FontWeight.BOLD), t.badge(ws.status, accent)],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(content=ft.Icon(ws.icon, size=72, color=accent),
                             alignment=ft.Alignment.CENTER, padding=ft.Padding.symmetric(vertical=18)),
                ft.Text(ws.title, size=24, weight=ft.FontWeight.BOLD, color="#ffffff", text_align=ft.TextAlign.CENTER),
                ft.Text(ws.desc, size=13, color=t.MUTED, text_align=ft.TextAlign.CENTER),
                ft.Divider(height=20, color=t.BORDER),
                *[
                    ft.Row([ft.Icon(ft.Icons.CHECK_ROUNDED, size=16, color=accent), ft.Text(b, size=13, color=t.TEXT)], spacing=8)
                    for b in ws.bullets
                ],
                ft.Container(expand=True),
                ft.Row(
                    [ft.Text("進入", size=14, color=accent, weight=ft.FontWeight.W_600),
                     ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, color=accent, size=18)],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=4,
                ),
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        padding=24,
        bgcolor=t.CARD,
        border_radius=18,
        border=ft.Border.all(1, t.BORDER),
        expand=True,
        height=460,
        scale=1.0,
        animate_scale=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
        on_hover=on_hover,
        on_click=lambda e: on_open(ws.key),
    )


def build_home(specs: list[WorkspaceSpec], on_open: Callable[[str], None], identity_text: ft.Text) -> ft.Control:
    return ft.Column(
        [
            app_title(ft.Row([ft.Icon(ft.Icons.PERSON_ROUNDED, color=t.MUTED, size=18), identity_text], spacing=6)),
            ft.Container(height=30),
            ft.Text("要進行哪一項工作？", size=28, weight=ft.FontWeight.BOLD, color="#ffffff"),
            t.caption("依照 Delft3D FM 1D2D 的工作流程：建置模型 → 執行模擬 → 檢視成果"),
            ft.Container(height=20),
            ft.Row([_home_card(ws, on_open) for ws in specs], spacing=22),
        ],
        spacing=6,
        expand=True,
    )
