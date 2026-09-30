"""
Flet UI 雛形 - 2026-08-20 研究用範例
比照 app.py 主畫面配置（工作資料夾列、Git 身分列、時光機列、分頁卡片）
用來實測 Flet 能做出的視覺風格，純展示用，未串接任何真實邏輯。

安裝：pip install flet
執行：python research/flet_demo.py

注意：此檔案是針對當時安裝的 flet==0.86.5 版本 API 寫的（見同資料夾
新版介面研究成果彙整.md 裡的「踩坑記錄」）。若日後安裝的 flet 版本不同，
請先用 inspect.signature() 重新核對各元件的建構參數，API 很可能又變了。
"""
import flet as ft


def main(page: ft.Page):
    page.title = "D-Flow 模式檔案管理系統"
    page.window.width = 980
    page.window.height = 840
    page.bgcolor = "#0f1420"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 24
    page.theme = ft.Theme(font_family="Microsoft JhengHei")

    def card(content, padding=18):
        return ft.Container(
            content=content,
            padding=padding,
            bgcolor="#1a2033",
            border_radius=14,
            border=ft.Border.all(1, "#2a3350"),
        )

    def pill_button(text, icon, bgcolor, on_click=None):
        return ft.Button(
            content=text,
            icon=icon,
            bgcolor=bgcolor,
            color="#ffffff",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                elevation=0,
            ),
            on_click=on_click,
        )

    header = ft.Row(
        [
            ft.Row(
                [
                    ft.Icon(ft.Icons.WATER_DROP_ROUNDED, color="#3ba7ff", size=30),
                    ft.Text("D-Flow 模式檔案管理系統", size=22, weight=ft.FontWeight.BOLD, color="#ffffff"),
                ],
                spacing=10,
            ),
            ft.Container(
                content=ft.Text("v1.2", size=12, color="#9fb3d9"),
                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                bgcolor="#232a44",
                border_radius=20,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    workdir_row = card(
        ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("工作資料夾", size=12, color="#8592b0"),
                        ft.Text("D:/Models/範例專案", size=14, color="#e6ecff"),
                    ],
                    spacing=2,
                    expand=True,
                ),
                pill_button("瀏覽本機", ft.Icons.FOLDER_OPEN_ROUNDED, "#2f6fed"),
                pill_button("從雲端下載", ft.Icons.CLOUD_DOWNLOAD_ROUNDED, "#22a55e"),
                ft.OutlinedButton(
                    content="狀態檢查",
                    icon=ft.Icons.FACT_CHECK_ROUNDED,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
    )

    identity_row = card(
        ft.Row(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.PERSON_ROUNDED, color="#3ba7ff", size=20),
                        ft.Column(
                            [
                                ft.Text("Git 身分", size=12, color="#8592b0"),
                                ft.Text("王小明 <wang@example.com>", size=14, color="#7fd0ff"),
                            ],
                            spacing=2,
                        ),
                    ],
                    spacing=10,
                ),
                ft.OutlinedButton(
                    content="設定 Git 身分",
                    icon=ft.Icons.SETTINGS_ROUNDED,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
    )

    timemachine_row = card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.HOURGLASS_BOTTOM_ROUNDED, color="#f0ad4e", size=20),
                                ft.Text("時光機（切換版本）", size=14, weight=ft.FontWeight.W_600, color="#ffffff"),
                            ],
                            spacing=8,
                        ),
                        ft.Row(
                            [
                                ft.Dropdown(
                                    width=260,
                                    value="build/v1.0.1",
                                    options=[
                                        ft.dropdown.Option("build/v1.0.1"),
                                        ft.dropdown.Option("build/v1.0"),
                                        ft.dropdown.Option("build/v0.1.2-Pull"),
                                        ft.dropdown.Option("main"),
                                    ],
                                    border_radius=10,
                                    bgcolor="#232a44",
                                    border=ft.Border.all(1, "#2a3350"),
                                ),
                                ft.IconButton(ft.Icons.REFRESH_ROUNDED, tooltip="重新整理"),
                                pill_button("恢復至此版本", ft.Icons.RESTORE_ROUNDED, "#e5484d"),
                            ],
                            spacing=8,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=14, color="#8592b0"),
                        ft.Text("更新排水分區下水道資料", size=13, color="#7fd0ff"),
                    ],
                    spacing=6,
                ),
            ],
            spacing=10,
        )
    )

    def tab_content(title, subtitle, icon, accent):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row([ft.Icon(icon, color=accent, size=22), ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color="#ffffff")], spacing=10),
                    ft.Text(subtitle, size=13, color="#8592b0"),
                    ft.Container(height=12),
                    ft.TextField(label="建置標籤（例如 v1.0-base）", border_radius=10, filled=True, bgcolor="#232a44"),
                    ft.Container(height=8),
                    ft.TextField(label="建置內容說明", multiline=True, min_lines=3, border_radius=10, filled=True, bgcolor="#232a44"),
                    ft.Container(height=12),
                    pill_button("儲存建置進度", ft.Icons.SAVE_ROUNDED, "#2f6fed"),
                ],
                spacing=6,
            ),
            padding=20,
        )

    # 新版 Flet 的 Tabs 元件改成 TabBar/TabBarView 分離的寫法，這裡改用自製的分頁按鈕列
    # （純視覺展示用，不含真正切換邏輯）取代，效果一樣是三個分頁的樣式
    tab_bar = ft.Row(
        [
            ft.Container(
                content=ft.Row(
                    [ft.Icon(ft.Icons.CAMERA_ALT_ROUNDED, size=16, color="#ffffff"), ft.Text("模型建置快照", size=13, color="#ffffff")],
                    spacing=6,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                bgcolor="#2f6fed",
                border_radius=10,
            ),
            ft.Container(
                content=ft.Row(
                    [ft.Icon(ft.Icons.CLOUD_ROUNDED, size=16, color="#8592b0"), ft.Text("遠端伺服器備份", size=13, color="#8592b0")],
                    spacing=6,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            ),
            ft.Container(
                content=ft.Row(
                    [ft.Icon(ft.Icons.HISTORY_ROUNDED, size=16, color="#8592b0"), ft.Text("版本歷史", size=13, color="#8592b0")],
                    spacing=6,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            ),
        ],
        spacing=8,
    )

    tabs_card = ft.Container(
        content=ft.Column(
            [
                tab_bar,
                ft.Divider(height=1, color="#2a3350"),
                tab_content("模型建置快照", "把目前的修改存成一個新版本", ft.Icons.CAMERA_ALT_ROUNDED, "#3ba7ff"),
            ],
            spacing=0,
        ),
        bgcolor="#1a2033",
        border_radius=14,
        border=ft.Border.all(1, "#2a3350"),
        padding=14,
        expand=True,
    )

    page.add(
        ft.Column(
            [
                header,
                ft.Container(height=8),
                workdir_row,
                identity_row,
                timemachine_row,
                ft.Container(height=4),
                tabs_card,
            ],
            spacing=14,
            expand=True,
        )
    )


ft.app(target=main)
