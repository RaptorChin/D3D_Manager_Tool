"""對話框：訊息、確認、進度視窗。

背景工作一律以 page.run_thread() 啟動；在該執行緒中修改元件後呼叫 page.update()。
（背景執行緒的 page.update() 由 ui/runtime.py 排進事件迴圈，畫面才會即時更新。）
"""
from __future__ import annotations

from typing import Callable

import flet as ft

from . import theme as t

_KIND = {
    "info": (ft.Icons.INFO_ROUNDED, t.ACCENT_BUILD),
    "success": (ft.Icons.CHECK_CIRCLE_ROUNDED, t.SUCCESS),
    "warning": (ft.Icons.WARNING_ROUNDED, t.WARNING),
    "error": (ft.Icons.ERROR_ROUNDED, t.DANGER),
}


def _body(message: str) -> ft.Control:
    # 高度依內容而定；訊息很長時由 AlertDialog(scrollable=True) 負責捲動
    return ft.Container(content=ft.Text(message, size=14, color=t.TEXT, selectable=True), width=520)


def alert(page: ft.Page, title: str, message: str, kind: str = "info", on_close: Callable | None = None):
    """單一按鈕的訊息框（取代 messagebox.showinfo / showwarning / showerror）"""
    icon, color = _KIND.get(kind, _KIND["info"])

    def close(e):
        page.pop_dialog()
        if on_close:
            on_close()

    dlg = ft.AlertDialog(
        modal=True,
        icon=ft.Icon(icon, color=color, size=36),
        title=ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
        content=_body(message),
        scrollable=True,
        actions=[t.pill_button("確定", ft.Icons.CHECK_ROUNDED, t.PRIMARY, on_click=close)],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.show_dialog(dlg)


def confirm(
    page: ft.Page,
    title: str,
    message: str,
    on_yes: Callable,
    on_no: Callable | None = None,
    yes_text: str = "確定",
    no_text: str = "取消",
    danger: bool = False,
):
    """是／否確認框（取代 messagebox.askyesno）；按下後才執行 on_yes / on_no"""

    def yes(e):
        page.pop_dialog()
        on_yes()

    def no(e):
        page.pop_dialog()
        if on_no:
            on_no()

    dlg = ft.AlertDialog(
        modal=True,
        icon=ft.Icon(ft.Icons.WARNING_ROUNDED if danger else ft.Icons.HELP_ROUNDED,
                     color=t.DANGER if danger else t.ACCENT_BUILD, size=36),
        title=ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
        content=_body(message),
        scrollable=True,
        actions=[
            ft.TextButton(no_text, on_click=no),
            t.pill_button(yes_text, ft.Icons.CHECK_ROUNDED, t.DANGER if danger else t.PRIMARY, on_click=yes),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.show_dialog(dlg)


class ProgressDialog:
    """長時間工作的進度視窗（取代 v1.x 的 open_local_processing_dialog）。

    用法（在背景執行緒中）：
        pd = ProgressDialog(page, "📦 專案初始化")
        pd.show()
        task_func(pd.update)     # update(text, pct)，pct 可為 None
        pd.close()
    """

    def __init__(self, page: ft.Page, title: str, subtitle: str = ""):
        self.page = page
        self.status = ft.Text("準備處理...", size=14, color=t.TEXT)
        self.pct = ft.Text("0%", size=14, color=t.ACCENT_BUILD, weight=ft.FontWeight.BOLD)
        self.bar = ft.ProgressBar(value=0, bar_height=8, border_radius=4, color=t.ACCENT_BUILD, bgcolor=t.FIELD)
        items = []
        if subtitle:
            items.append(t.caption(subtitle))
        items += [self.status, self.pct, self.bar]
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(ft.Column(items, spacing=10, tight=True), width=520),
        )

    def show(self):
        self.page.show_dialog(self.dialog)

    def update(self, text: str, pct=None):
        self.status.value = text if len(text) <= 90 else text[:87] + "..."
        if pct is not None:
            pct = min(max(float(pct), 0), 100)
            self.bar.value = pct / 100
            self.pct.value = f"{int(pct)}%"
        self.page.update()

    def close(self):
        self.page.pop_dialog()


def run_with_progress(
    page: ft.Page,
    title: str,
    task: Callable[[Callable], object],
    on_success: Callable[[object], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    subtitle: str = "",
):
    """在背景執行緒執行 task(update)，期間顯示進度視窗；完成後關閉並呼叫 on_success(回傳值)。
    失敗時關閉視窗並顯示錯誤訊息，再呼叫 on_error(錯誤文字)。"""
    pd = ProgressDialog(page, title, subtitle)
    pd.show()

    def worker():
        try:
            result = task(pd.update)
        except Exception as ex:  # noqa: BLE001 — 所有錯誤都要回報給使用者
            err = str(ex).strip() or repr(ex)
            pd.close()
            alert(page, "處理失敗", err, "error", on_close=(lambda: on_error(err)) if on_error else None)
            return
        pd.close()
        if on_success:
            on_success(result)

    page.run_thread(worker)
