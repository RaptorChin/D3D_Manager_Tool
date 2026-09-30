"""D-Flow 模式檔案管理系統 v2.0（Flet 版）程式入口。

畫面架構：主頁面以 3 張卡片選擇工作區（docs/UI_PLAN.md §1）。
  ① 模型建置：ui/build_workspace.py（v1.2.1 全部功能）
  ② 執行模擬、③ 檢視成果：v2.0 先顯示「規劃中」，依里程碑 M2 以後逐步開放

執行（在專案資料夾）：python app.py
打包：flet pack app.py -n D3D_Manager_Tool -i assets/icon.ico --add-data "assets;assets" --hidden-import cftime netCDF4.utils
舊版 CustomTkinter 介面：python app_ctk.py（確認 v2.0 穩定後移除）
"""
import flet as ft

from core.git_control import GitModelManager
from ui import dialogs
from ui import theme as t
from ui.build_workspace import BuildWorkspace
from ui.home import build_home
from ui.runtime import install_thread_safe_update
from ui.workspace import TabSpec, WorkspaceSpec, WorkspaceView


def make_specs(build: BuildWorkspace) -> list[WorkspaceSpec]:
    return [
        WorkspaceSpec(
            key="build", no="①", title="模型建置", icon=ft.Icons.ARCHITECTURE_ROUNDED, accent=t.ACCENT_BUILD,
            status=f"v{t.APP_VERSION}",
            desc="版本控管 Delta Shell 專案：存檔點、時光機、推送到遠端伺服器",
            bullets=["建置快照與時光機", "推送／下載遠端備份", "版本歷史查詢"],
            info_bar=build.info_bar(),
            tabs=[
                TabSpec("本機建置", ft.Icons.CAMERA_ALT_ROUNDED, build.tab_local()),
                TabSpec("推送到遠端", ft.Icons.CLOUD_UPLOAD_ROUNDED, build.tab_push()),
                TabSpec("版本歷史", ft.Icons.HISTORY_ROUNDED, build.tab_history()),
                TabSpec("模型總覽", ft.Icons.LAYERS_ROUNDED, None, "docs/SPEC_build_module.md B1",
                        ["MDU 關鍵參數與模擬時段", "引用檔清單與是否存在", "網格規模、結構物統計"]),
            ],
        ),
        WorkspaceSpec(
            key="run", no="②", title="執行模擬", icon=ft.Icons.PLAY_CIRCLE_ROUNDED, accent=t.ACCENT_RUN,
            status="開發中",
            desc="DIMR 匯出資料夾：預檢擋錯、分割、MPI 平行計算與進度監控",
            bullets=["執行前預檢（E01～W09）", "一鍵分割與執行", "進度監控與批次佇列"],
            tabs=[
                TabSpec("情境設定", ft.Icons.TUNE_ROUNDED, None, "docs/SPEC_run_module.md P5",
                        ["選擇格網雨量 nc，預覽時間與空間範圍", "自動調整 RefDate / TStart / TStop、.ext、.fou",
                         "預覽差異 → 備份 → 套用 → 自動預檢"]),
                TabSpec("預檢", ft.Icons.FACT_CHECK_ROUNDED, None, "docs/SPEC_run_module.md P3",
                        ["執行前檢查雨量時間範圍、引用檔、分割狀態等 E01～E09 錯誤", "W01～W09 警告與一鍵修正"]),
                TabSpec("執行與監控", ft.Icons.MONITOR_HEART_ROUNDED, None, "docs/SPEC_run_module.md P2、P4",
                        ["自動偵測 Delft3D 安裝、一鍵分割與 MPI 執行", "進度條、剩餘時間、平均 Δt、Log"]),
                TabSpec("批次佇列", ft.Icons.QUEUE_ROUNDED, None, "docs/SPEC_run_module.md P5",
                        ["加入多場雨量事件依序執行", "程式重開可續跑，完成後產生彙總表"]),
            ],
        ),
        WorkspaceSpec(
            key="results", no="③", title="檢視成果", icon=ft.Icons.INSIGHTS_ROUNDED, accent=t.ACCENT_RESULTS,
            status="構想中",
            desc="判定模擬是否有效，統計淹水成果並與其他情境比較",
            bullets=["結果檢核與判定報告", "淹水深度分級統計", "時序圖與情境比較"],
            tabs=[
                TabSpec("結果檢核", ft.Icons.VERIFIED_ROUNDED, None, "docs/SPEC_run_module.md P4",
                        ["R01～R06：雨量、抽水站、質量平衡、fou、計算完整、map 合併", "總判定：有效／可疑／無效"]),
                TabSpec("淹水統計", ft.Icons.WATER_ROUNDED, None, "docs/SPEC_results_module.md V1",
                        ["最大淹水深度分級面積", "匯出 CSV／GIS 格式"]),
                TabSpec("時序圖", ft.Icons.SHOW_CHART_ROUNDED, None, "docs/SPEC_results_module.md V2",
                        ["測站水位／水深／雨量", "抽水站流量對照 capacity"]),
                TabSpec("情境比較", ft.Icons.COMPARE_ARROWS_ROUNDED, None, "docs/SPEC_results_module.md V3",
                        ["多場事件彙總表", "兩情境最大淹水深度差異"]),
            ],
        ),
    ]


def main(page: ft.Page):
    install_thread_safe_update(page)  # 背景執行緒的畫面更新（進度條等）才會即時顯示
    page.title = t.APP_NAME
    page.window.icon = str(t.assets_dir() / "icon.ico")
    page.window.width = 1180
    page.window.height = 860
    page.window.min_width = 1000
    page.window.min_height = 700
    page.bgcolor = t.BG
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(font_family=t.FONT)
    page.padding = 24

    GitModelManager.ensure_global_safe_directory()

    body = ft.Container(expand=True)
    home_identity = ft.Text("", size=13, color=t.MUTED)
    views: dict[str, WorkspaceView] = {}

    def sync_identity(text: str):
        home_identity.value = text  # 主頁右上角也顯示 Git 身分

    build = BuildWorkspace(page, on_identity_changed=sync_identity)
    specs = make_specs(build)

    def show_home():
        body.content = build_home(specs, open_workspace, home_identity)
        page.update()

    def open_workspace(key: str):
        if key not in views:
            spec = next(s for s in specs if s.key == key)
            views[key] = WorkspaceView(spec, specs, show_home, open_workspace, page)
        body.content = views[key].control
        page.update()

    async def close_window():
        try:
            await page.window.close()  # 等同按視窗右上角的 ✕
        except RuntimeError:
            pass  # 視窗關閉後連線隨即中斷（Session closed），屬正常情況

    def quit_app(e):
        dialogs.confirm(
            page, "結束程式", "確定要結束程式嗎？",
            on_yes=lambda: page.run_task(close_window),
            yes_text="結束", no_text="取消", danger=True,
        )

    # 所有畫面共用：右下角「結束」按鈕（沿用 v1.x 的位置與紅色）
    footer = ft.Row(
        [t.pill_button("結束", ft.Icons.POWER_SETTINGS_NEW_ROUNDED, t.DANGER, on_click=quit_app)],
        alignment=ft.MainAxisAlignment.END,
    )
    page.add(body, footer)
    show_home()
    build.check_identity_on_startup()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(t.assets_dir()))
