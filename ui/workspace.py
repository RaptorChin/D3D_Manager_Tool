"""工作區共同版面（UI_PLAN.md §1.2）：
🏠 回主頁＋標題＋快速切換 → 共用資訊列 → 分頁列 → 分頁內容。

每個分頁的內容只建立一次、切換時保留（輸入到一半的文字不會消失）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import flet as ft

from . import theme as t


@dataclass
class TabSpec:
    name: str
    icon: str
    content: ft.Control | None = None          # None = 規劃中
    planned_ref: str = ""                      # 規劃中分頁：規格文件位置
    planned_lines: list[str] = field(default_factory=list)

    @property
    def planned(self) -> bool:
        return self.content is None


@dataclass
class WorkspaceSpec:
    key: str
    no: str
    title: str
    icon: str
    accent: str
    status: str
    desc: str
    bullets: list[str]
    tabs: list[TabSpec]
    info_bar: ft.Control | None = None


def planned_placeholder(tab: TabSpec) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.CONSTRUCTION_ROUNDED, size=48, color=t.MUTED),
                ft.Text(f"「{tab.name}」規劃中", size=18, weight=ft.FontWeight.BOLD, color=t.TEXT),
                t.caption(f"規格：{tab.planned_ref}"),
                ft.Container(height=6),
                *[ft.Text(f"•  {line}", size=13, color=t.MUTED) for line in tab.planned_lines],
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
        padding=30,
    )


class WorkspaceView:
    """一個工作區的畫面；show_home / switch_to 由 App 提供"""

    def __init__(self, spec: WorkspaceSpec, all_specs: list[WorkspaceSpec],
                 show_home: Callable[[], None], switch_to: Callable[[str], None], page: ft.Page):
        self.page = page
        self.spec = spec
        self.all_specs = all_specs
        self.show_home = show_home
        self.switch_to = switch_to
        self.index = next((i for i, tb in enumerate(spec.tabs) if not tb.planned), 0)
        self._bodies = [tb.content or planned_placeholder(tb) for tb in spec.tabs]
        self.tab_row = ft.Row(spacing=4, scroll=ft.ScrollMode.AUTO)
        self.body = ft.Container(expand=True, padding=ft.Padding.only(top=16))
        self._render_tabs()
        self.control = self._build()

    def _build(self) -> ft.Control:
        s = self.spec
        switcher = ft.Row(
            [
                ft.IconButton(
                    w.icon,
                    icon_color=w.accent if w.key == s.key else t.MUTED,
                    tooltip=f"{w.no} {w.title}",
                    on_click=lambda e, k=w.key: self.switch_to(k),
                )
                for w in self.all_specs
            ],
            spacing=0,
        )
        top = ft.Row(
            [
                ft.Row(
                    [
                        ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="回主頁面", on_click=lambda e: self.show_home()),
                        ft.Icon(s.icon, color=s.accent, size=30),
                        ft.Text(f"{s.no} {s.title}", size=22, weight=ft.FontWeight.BOLD, color="#ffffff"),
                        t.badge(s.status, s.accent),
                    ],
                    spacing=10,
                ),
                switcher,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        tabs = ft.Column(
            [self.tab_row, ft.Divider(height=1, color=t.BORDER), self.body],
            spacing=0,
            expand=True,
        )
        items = [top]
        if s.info_bar is not None:
            items.append(s.info_bar)
        items.append(tabs)
        return ft.Column(items, spacing=14, expand=True)

    def _tab_button(self, i: int) -> ft.Control:
        tab = self.spec.tabs[i]
        selected = i == self.index
        fg = "#ffffff" if selected else t.MUTED
        items = [ft.Icon(tab.icon, size=16, color=fg), ft.Text(tab.name, size=13, color=fg)]
        if tab.planned:
            items.append(ft.Container(
                content=ft.Text("規劃中", size=10, color=t.MUTED),
                padding=ft.Padding.symmetric(horizontal=6, vertical=1),
                border_radius=8,
                border=ft.Border.all(1, t.MUTED),
            ))
        return ft.Container(
            content=ft.Row(items, spacing=6),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            bgcolor=ft.Colors.with_opacity(0.18, self.spec.accent) if selected else None,
            border=ft.Border.only(bottom=ft.BorderSide(3, self.spec.accent if selected else ft.Colors.TRANSPARENT)),
            border_radius=ft.BorderRadius.only(top_left=10, top_right=10),
            on_click=lambda e, idx=i: self.select(idx),
            ink=True,
        )

    def _render_tabs(self):
        self.tab_row.controls = [self._tab_button(i) for i in range(len(self.spec.tabs))]
        self.body.content = ft.Column([self._bodies[self.index]], expand=True, scroll=ft.ScrollMode.AUTO)

    def select(self, index: int):
        self.index = index
        self._render_tabs()
        self.page.update()
