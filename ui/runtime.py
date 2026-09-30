"""讓背景執行緒的畫面更新即時送出。

Flet 0.86.5 的問題（2026-09-29 實測）：在 page.run_thread() 等背景執行緒呼叫 page.update()，
更新不會送到畫面，要等使用者下一次操作才一起出現——推送／初始化時進度條會完全不動。
從事件迴圈上呼叫則正常。

解法：程式啟動時替換 page.update；若目前不在事件迴圈上（背景執行緒），改用 page.run_task()
排進事件迴圈執行。show_dialog / pop_dialog 內部也會呼叫 page.update，因此一併生效。
"""
from __future__ import annotations

import asyncio

import flet as ft


def _on_event_loop() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def install_thread_safe_update(page: ft.Page):
    original_update = page.update

    def update(*controls):
        if _on_event_loop():
            return original_update(*controls)

        async def _flush():
            original_update(*controls)

        page.run_task(_flush)

    page.update = update
