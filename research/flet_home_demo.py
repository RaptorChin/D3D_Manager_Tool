"""
Flet 主頁面＋三大工作區框架雛形（2026-09-29 研究用）

主頁面以 3 個大圖示選擇工作：
  ① 模型建置：本機建置（時光機、建置快照）／推送到遠端／版本歷史／模型總覽（規劃中）
  ② 執行模擬：情境設定（規劃中）／預檢／執行與監控／批次佇列（規劃中）
  ③ 檢視成果：結果檢核／淹水統計／時序圖（規劃中）／情境比較（規劃中）

純畫面框架，未串接任何真實邏輯；畫面上的數字與清單都是「範例資料」。

安裝：pip install flet==0.86.5
執行（在專案資料夾）：
  python research/flet_home_demo.py              開啟主頁面
  python research/flet_home_demo.py run 2        直接開「執行模擬」的第 3 個分頁（截圖用）

注意：依 flet==0.86.5 的 API 撰寫；版本不同時請先用 inspect.signature() 核對（見 docs/UI_PLAN.md §5）。
"""
import sys

import flet as ft

# ── 配色 ───────────────────────────────────────────
BG = "#0f1420"
CARD = "#1a2033"
CARD_HI = "#20283f"
FIELD = "#232a44"
BORDER = "#2a3350"
TEXT = "#e6ecff"
MUTED = "#8592b0"

BLUE = "#2f6fed"
GREEN = "#22a55e"
RED = "#e5484d"
ORANGE = "#f0ad4e"
GRAY = "#5a5a5a"

# 三個工作區的定義：代表色、圖示、分頁（名稱, 圖示, 是否規劃中）
WORKSPACES = {
    "build": {
        "no": "①",
        "title": "模型建置",
        "icon": ft.Icons.ARCHITECTURE_ROUNDED,
        "accent": "#3ba7ff",
        "desc": "版本控管 Delta Shell 專案：存檔點、時光機、推送到遠端伺服器",
        "bullets": ["建置快照與時光機", "推送／下載遠端備份", "版本歷史查詢"],
        "status": "已完成 v1.2.1",
        "tabs": [
            ("本機建置", ft.Icons.CAMERA_ALT_ROUNDED, False),
            ("推送到遠端", ft.Icons.CLOUD_UPLOAD_ROUNDED, False),
            ("版本歷史", ft.Icons.HISTORY_ROUNDED, False),
            ("模型總覽", ft.Icons.LAYERS_ROUNDED, True),
        ],
    },
    "run": {
        "no": "②",
        "title": "執行模擬",
        "icon": ft.Icons.PLAY_CIRCLE_ROUNDED,
        "accent": ORANGE,
        "desc": "DIMR 匯出資料夾：預檢擋錯、分割、MPI 平行計算與進度監控",
        "bullets": ["執行前預檢（E01～W09）", "一鍵分割與執行", "進度監控與批次佇列"],
        "status": "規格已定，開發中",
        "tabs": [
            ("情境設定", ft.Icons.TUNE_ROUNDED, True),
            ("預檢", ft.Icons.FACT_CHECK_ROUNDED, False),
            ("執行與監控", ft.Icons.MONITOR_HEART_ROUNDED, False),
            ("批次佇列", ft.Icons.QUEUE_ROUNDED, True),
        ],
    },
    "results": {
        "no": "③",
        "title": "檢視成果",
        "icon": ft.Icons.INSIGHTS_ROUNDED,
        "accent": "#34d399",
        "desc": "判定模擬是否有效，統計淹水成果並與其他情境比較",
        "bullets": ["結果檢核與判定報告", "淹水深度分級統計", "時序圖與情境比較"],
        "status": "構想中",
        "tabs": [
            ("結果檢核", ft.Icons.VERIFIED_ROUNDED, False),
            ("淹水統計", ft.Icons.WATER_ROUNDED, False),
            ("時序圖", ft.Icons.SHOW_CHART_ROUNDED, True),
            ("情境比較", ft.Icons.COMPARE_ARROWS_ROUNDED, True),
        ],
    },
}


# ── 共用小元件 ─────────────────────────────────────
def card(content, padding=18, expand=False):
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=CARD,
        border_radius=14,
        border=ft.Border.all(1, BORDER),
        expand=expand,
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


def label_value(label, value, value_color=TEXT, expand=False):
    return ft.Column(
        [ft.Text(label, size=12, color=MUTED), ft.Text(value, size=14, color=value_color)],
        spacing=2,
        expand=expand,
    )


def section_title(text, icon, accent):
    return ft.Row(
        [ft.Icon(icon, color=accent, size=20), ft.Text(text, size=15, weight=ft.FontWeight.BOLD, color="#ffffff")],
        spacing=8,
    )


def field(label, value="", multiline=False, width=None, expand=False):
    return ft.TextField(
        label=label,
        value=value,
        multiline=multiline,
        min_lines=3 if multiline else None,
        border_radius=10,
        filled=True,
        bgcolor=FIELD,
        width=width,
        expand=expand,
    )


def dropdown(value, options, width=260):
    return ft.Dropdown(
        width=width,
        value=value,
        options=[ft.dropdown.Option(o) for o in options],
        border_radius=10,
        bgcolor=FIELD,
        border=ft.Border.all(1, BORDER),
    )


def planned_placeholder(title, spec_ref, lines):
    """規劃中的分頁：顯示預計內容，不放可操作元件"""
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.CONSTRUCTION_ROUNDED, size=48, color=MUTED),
                ft.Text(f"「{title}」規劃中", size=18, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Text(f"規格：{spec_ref}", size=12, color=MUTED),
                ft.Container(height=6),
                *[ft.Text(f"•  {line}", size=13, color=MUTED) for line in lines],
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
        padding=30,
    )


# ── ① 模型建置 的內容 ────────────────────────────────
def build_header():
    """工作區頂部：所有分頁共用的專案資訊（工作資料夾＋Git 身分）"""
    return card(
        ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER_ROUNDED, color="#3ba7ff", size=22),
                label_value("工作資料夾（Delta Shell 專案）", "D:/Models/範例專案", expand=True),
                label_value("Git 身分", "王小明 <wang@example.com>", "#7fd0ff"),
                ft.IconButton(ft.Icons.SETTINGS_ROUNDED, tooltip="設定 Git 身分"),
                pill_button("瀏覽本機", ft.Icons.FOLDER_OPEN_ROUNDED, BLUE),
                pill_button("從雲端下載", ft.Icons.CLOUD_DOWNLOAD_ROUNDED, GREEN),
                outline_button("狀態檢查", ft.Icons.FACT_CHECK_ROUNDED),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
    )


def build_tab_local(accent):
    time_machine = card(
        ft.Column(
            [
                section_title("時光機（切換版本）", ft.Icons.HOURGLASS_BOTTOM_ROUNDED, ORANGE),
                ft.Row(
                    [
                        dropdown("build/v1.0.1", ["build/v1.0.1", "build/v1.0", "build/v1.0.1.1-Pull", "main"]),
                        ft.IconButton(ft.Icons.REFRESH_ROUNDED, tooltip="重新整理"),
                        pill_button("恢復至此版本", ft.Icons.RESTORE_ROUNDED, RED),
                    ],
                    spacing=8,
                ),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=14, color=MUTED),
                        ft.Text("版本說明：更新排水分區下水道資料", size=13, color="#7fd0ff"),
                    ],
                    spacing=6,
                ),
            ],
            spacing=12,
        ),
        expand=True,
    )
    snapshot = card(
        ft.Column(
            [
                section_title("儲存建置快照", ft.Icons.CAMERA_ALT_ROUNDED, accent),
                ft.Text("把目前的修改存成一個新版本（build/…）", size=12, color=MUTED),
                field("建置標籤（例如 v1.0-base）"),
                field("建置內容說明", multiline=True),
                ft.Row([pill_button("儲存建置進度", ft.Icons.SAVE_ROUNDED, BLUE)]),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        expand=True,
    )
    return ft.Row([time_machine, snapshot], spacing=14, vertical_alignment=ft.CrossAxisAlignment.START)


def build_tab_push(accent):
    bind = card(
        ft.Column(
            [
                section_title("1. 綁定遠端路徑", ft.Icons.LINK_ROUNDED, accent),
                ft.Text("GitHub HTTPS，或內網 \\\\伺服器\\共用資料夾\\專案", size=12, color=MUTED),
                ft.Row(
                    [
                        field("遠端位址", r"\\伺服器\共用資料夾\範例專案", expand=True),
                        pill_button("綁定", ft.Icons.LINK_ROUNDED, BLUE),
                    ],
                    spacing=10,
                ),
            ],
            spacing=12,
        )
    )
    push = card(
        ft.Column(
            [
                section_title("2. 推送到遠端伺服器", ft.Icons.CLOUD_UPLOAD_ROUNDED, accent),
                ft.Text("依序：更新規則 → 上傳 LFS 大檔 → 推送版本紀錄 → 寫入 .dsproj / .dsproj_data", size=12, color=MUTED),
                ft.Row([pill_button("開始推送", ft.Icons.ROCKET_LAUNCH_ROUNDED, GREEN)]),
                ft.Text("正在寫入執行檔 (132/418)：NWT_KL.dsproj_data/FlowFM_net.nc (286.4 MB)　［範例］", size=12, color=MUTED),
                ft.ProgressBar(value=0.72, bar_height=8, border_radius=4, color=GREEN, bgcolor=FIELD),
            ],
            spacing=12,
        )
    )
    return ft.Column([bind, push], spacing=14)


def build_tab_history(accent):
    commits = [
        ("a1b2c3d", "2026-08-27 14:42", "王小明", "更新排水分區下水道資料"),
        ("9f8e7d6", "2026-08-20 10:15", "王小明", "Auto Save: 載入前自動儲存未提交之變更"),
        ("5c4b3a2", "2026-08-18 16:03", "同事A", "調整河川出口邊界水位"),
        ("1a2b3c4", "2026-08-13 09:30", "王小明", "Auto Initial commit: Cleaned & Slim Model"),
    ]
    rows = []
    for h, date, who, msg in commits:
        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(h, size=12, color="#7fd0ff", font_family="Consolas", width=70),
                        ft.Text(date, size=12, color=MUTED, width=120),
                        ft.Text(who, size=12, color=TEXT, width=70),
                        ft.Text(msg, size=13, color=TEXT, expand=True),
                    ],
                    spacing=12,
                ),
                padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
            )
        )
    return card(
        ft.Column(
            [
                ft.Row(
                    [
                        label_value("查詢資料夾", "D:/Models/範例專案", expand=True),
                        outline_button("瀏覽", ft.Icons.FOLDER_OPEN_ROUNDED),
                        outline_button("使用遠端備份路徑", ft.Icons.CLOUD_ROUNDED),
                    ],
                    spacing=10,
                ),
                ft.Row([ft.Text("版次：", color=MUTED), dropdown("build/v1.0.1", ["build/v1.0.1", "build/v1.0", "main"])]),
                ft.Column(rows, spacing=0),
            ],
            spacing=14,
        ),
        expand=True,
    )


# ── ② 執行模擬 的內容 ────────────────────────────────
def run_header():
    return card(
        ft.Row(
            [
                ft.Icon(ft.Icons.MEMORY_ROUNDED, color=ORANGE, size=22),
                ft.Column(
                    [
                        ft.Text("Delft3D 安裝", size=12, color=MUTED),
                        dropdown("Delft3D FM Suite 2026.02 1D2D", ["Delft3D FM Suite 2026.02 1D2D"], width=280),
                    ],
                    spacing=4,
                ),
                label_value("DIMR 資料夾", "D:/Models/範例專案(10m)/DIMR", expand=True),
                outline_button("瀏覽", ft.Icons.FOLDER_OPEN_ROUNDED),
                ft.Column(
                    [ft.Text("核心數", size=12, color=MUTED), dropdown("8", ["1", "2", "4", "6", "8"], width=90)],
                    spacing=4,
                ),
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
    )


def run_action_bar(stage):
    """預檢／分割／執行／停止：依狀態啟用或停用（此雛形固定顯示）"""
    return ft.Row(
        [
            pill_button("預檢", ft.Icons.FACT_CHECK_ROUNDED, BLUE),
            pill_button("分割", ft.Icons.CONTENT_CUT_ROUNDED, GRAY),
            pill_button("開始執行", ft.Icons.PLAY_ARROW_ROUNDED, ORANGE if stage == "ready" else GRAY),
            pill_button("停止", ft.Icons.STOP_ROUNDED, RED if stage == "running" else GRAY),
        ],
        spacing=10,
    )


def run_tab_preflight(accent):
    icons = {
        "error": (ft.Icons.ERROR_ROUNDED, RED),
        "warning": (ft.Icons.WARNING_ROUNDED, ORANGE),
        "info": (ft.Icons.INFO_ROUNDED, "#3ba7ff"),
    }
    findings = [
        ("error", "E01", "NWT_KL_bnd.ext", "雨量檔時間 06-04 10:00～06-05 10:00 未涵蓋模擬時段 06-05 00:00～06-06 00:00"),
        ("error", "E05", "Maxima.fou", "wd 的 tstart/tstop（0～21600）不在模擬時段內"),
        ("warning", "W04", "NWT_KL.mdu", "NcFormat = 4：計算中無法讀取 his/map"),
        ("warning", "W05", "NWT_KL.mdu", "StatsInterval 空白：無法顯示進度"),
        ("info", "I01", "—", "模擬時段 2021-06-05 00:00～06-06 00:00（24 h），網格 1,000,000 格"),
    ]
    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("", size=12)),
            ft.DataColumn(ft.Text("代碼", size=12, color=MUTED)),
            ft.DataColumn(ft.Text("檔案", size=12, color=MUTED)),
            ft.DataColumn(ft.Text("訊息", size=12, color=MUTED)),
        ],
        rows=[
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Icon(icons[lv][0], color=icons[lv][1], size=18)),
                    ft.DataCell(ft.Text(code, size=12, color=icons[lv][1], weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f, size=12, color=TEXT)),
                    ft.DataCell(ft.Text(msg, size=12, color=TEXT)),
                ]
            )
            for lv, code, f, msg in findings
        ],
        heading_row_height=36,
        data_row_min_height=36,
        column_spacing=18,
    )
    fix = card(
        ft.Column(
            [
                section_title("建議修正（E05）", ft.Icons.LIGHTBULB_ROUNDED, ORANGE),
                ft.Text("將 Maxima.fou 各行的 tstart / tstop 改為 -1（代表整個模擬時段）。", size=13, color=TEXT),
                ft.Row(
                    [
                        pill_button("一鍵修正（先備份）", ft.Icons.AUTO_FIX_HIGH_ROUNDED, BLUE),
                        ft.Checkbox(label="我了解風險，仍要執行"),
                    ],
                    spacing=16,
                ),
            ],
            spacing=10,
        ),
        padding=14,
    )
    summary = ft.Row(
        [badge("2 個錯誤", RED), badge("2 個警告", ORANGE), badge("1 則資訊", "#3ba7ff"), ft.Text("［範例資料］", size=11, color=MUTED)],
        spacing=8,
    )
    return ft.Column([run_action_bar("blocked"), summary, card(table, padding=6), fix], spacing=12)


def run_tab_monitor(accent):
    log_lines = [
        "#0: Running parallel with 8 partitions",
        "#1: Running parallel with 8 partitions",
        "** INFO   : NWT_KL-Pump-A       1 nr of structure links",
        "** INFO   : Modelinit finished",
        "NWT_KL.Update(86400.0)",
        "** INFO   : Sim. time done   :  06-05 01:00   (62.4 %)",
    ]
    progress = card(
        ft.Column(
            [
                ft.Row(
                    [
                        section_title("計算進度", ft.Icons.MONITOR_HEART_ROUNDED, accent),
                        badge("執行中", ORANGE),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.ProgressBar(value=0.62, bar_height=10, border_radius=5, color=ORANGE, bgcolor=FIELD),
                ft.Row(
                    [
                        label_value("完成", "62 %", ORANGE),
                        label_value("模擬時間", "06-05 01:00"),
                        label_value("剩餘約", "1 h 20 m"),
                        label_value("平均 Δt", "2.3 s"),
                        label_value("已用時間", "2 h 11 m"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
            ],
            spacing=12,
        )
    )
    log = ft.Container(
        content=ft.ListView(
            [ft.Text(line, size=12, color="#9be39b", font_family="Consolas") for line in log_lines],
            spacing=2,
        ),
        bgcolor="#0b0e16",
        border_radius=10,
        border=ft.Border.all(1, BORDER),
        padding=12,
        expand=True,
    )
    return ft.Column(
        [run_action_bar("running"), progress, ft.Text("Log（最後 500 行；完整 log 存於 DIMR\\run_logs\\）", size=12, color=MUTED), log],
        spacing=12,
        expand=True,
    )


# ── ③ 檢視成果 的內容 ────────────────────────────────
def results_header():
    return card(
        ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER_ROUNDED, color="#34d399", size=22),
                label_value("成果資料夾", "D:/Models/範例專案(10m)/DIMR/dflowfm/output", expand=True),
                outline_button("瀏覽", ft.Icons.FOLDER_OPEN_ROUNDED),
                ft.Column([ft.Text("總判定", size=12, color=MUTED), badge("有效", "#34d399")], spacing=4),
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
    )


def results_tab_check(accent):
    checks = [
        ("R01", "雨量有進模型", "通過", "測站時雨量與輸入比值 0.97"),
        ("R02", "分割邊界抽水站", "注意", "Pump-A 最大抽水量 = capacity × 1.08"),
        ("R03", "質量平衡", "通過", "相對誤差 0.12 %"),
        ("R04", "fou 輸出", "通過", "8 個子域皆有 wd / wl 最大值"),
        ("R05", "計算完整", "通過", "最後模擬時間 = TStop"),
        ("R06", "map 合併", "通過", "NWT_KL_merged_map.nc（12.4 GB）"),
    ]
    color = {"通過": "#34d399", "注意": ORANGE, "失敗": RED}
    rows = [
        ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(code, size=12, weight=ft.FontWeight.BOLD, color=TEXT)),
                ft.DataCell(ft.Text(name, size=12, color=TEXT)),
                ft.DataCell(badge(res, color[res])),
                ft.DataCell(ft.Text(note, size=12, color=MUTED)),
            ]
        )
        for code, name, res, note in checks
    ]
    table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text(t, size=12, color=MUTED)) for t in ("代碼", "檢核項目", "結果", "說明")],
        rows=rows,
        heading_row_height=36,
        data_row_min_height=38,
        column_spacing=24,
    )
    return ft.Column(
        [
            ft.Row(
                [
                    pill_button("重新檢核", ft.Icons.REFRESH_ROUNDED, BLUE),
                    outline_button("開啟報告 run_report.txt", ft.Icons.DESCRIPTION_ROUNDED),
                    ft.Text("［範例資料］", size=11, color=MUTED),
                ],
                spacing=10,
            ),
            card(table, padding=6),
        ],
        spacing=12,
    )


def results_tab_flood(accent):
    classes = [("0.3～0.5 m", 4.21), ("0.5～1.0 m", 2.87), ("1.0～2.0 m", 1.05), ("≥ 2.0 m", 0.18)]
    max_area = max(a for _, a in classes)
    bars = []
    for name, area in classes:
        bars.append(
            ft.Row(
                [
                    ft.Text(name, size=13, color=TEXT, width=100),
                    ft.Container(width=420 * area / max_area, height=22, bgcolor=accent, border_radius=6),
                    ft.Text(f"{area:.2f} km²", size=13, color=TEXT),
                ],
                spacing=12,
            )
        )
    stats = card(
        ft.Column(
            [
                section_title("最大淹水深度分級面積", ft.Icons.WATER_ROUNDED, accent),
                ft.Text("資料來源：fou.nc 的 wd 最大值（8 個子域）［範例資料］", size=12, color=MUTED),
                *bars,
                ft.Row(
                    [
                        label_value("淹水總面積（≥ 0.3 m）", "8.31 km²", accent),
                        label_value("最大水深", "3.42 m"),
                        label_value("發生位置（TWD97）", "X 324,180 / Y 2,775,620"),
                    ],
                    spacing=40,
                ),
            ],
            spacing=12,
        )
    )
    export = card(
        ft.Row(
            [
                section_title("匯出", ft.Icons.MAP_ROUNDED, accent),
                outline_button("CSV（網格中心點）", ft.Icons.TABLE_CHART_ROUNDED),
                outline_button("GeoTIFF", ft.Icons.MAP_ROUNDED),
                outline_button("分級統計表", ft.Icons.GRID_ON_ROUNDED),
            ],
            spacing=12,
        ),
        padding=14,
    )
    return ft.Column([stats, export], spacing=14)


# ── 各分頁內容對照 ─────────────────────────────────
def tab_body(key, idx):
    ws = WORKSPACES[key]
    name, _, planned = ws["tabs"][idx]
    accent = ws["accent"]
    if planned:
        plans = {
            ("build", "模型總覽"): ("docs/SPEC_build_module.md B1", ["MDU 關鍵參數與模擬時段", "引用檔清單與是否存在", "網格規模、結構物統計"]),
            ("run", "情境設定"): ("docs/SPEC_run_module.md P5", ["選擇格網雨量 nc，預覽時間與空間範圍", "自動調整 RefDate / TStart / TStop、.ext、.fou", "預覽差異 → 備份 → 套用 → 自動預檢"]),
            ("run", "批次佇列"): ("docs/SPEC_run_module.md P5", ["加入多場雨量事件依序執行", "每場：套用 → 預檢 → 分割 → 執行 → 檢核", "程式重開可續跑，完成後產生彙總表"]),
            ("results", "時序圖"): ("docs/SPEC_results_module.md V2", ["測站水位／水深／雨量", "抽水站流量對照 capacity", "匯出 PNG / CSV"]),
            ("results", "情境比較"): ("docs/SPEC_results_module.md V3", ["多場事件彙總表", "兩情境最大淹水深度差異", "檢查網格一致"]),
        }
        ref, lines = plans[(key, name)]
        return planned_placeholder(name, ref, lines)
    builders = {
        ("build", 0): build_tab_local,
        ("build", 1): build_tab_push,
        ("build", 2): build_tab_history,
        ("run", 1): run_tab_preflight,
        ("run", 2): run_tab_monitor,
        ("results", 0): results_tab_check,
        ("results", 1): results_tab_flood,
    }
    return builders[(key, idx)](accent)


HEADERS = {"build": build_header, "run": run_header, "results": results_header}


# ── 主程式 ────────────────────────────────────────
def main(page: ft.Page):
    page.title = "D-Flow 模式檔案管理系統"
    page.window.width = 1180
    page.window.height = 860
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 24
    page.theme = ft.Theme(font_family="Microsoft JhengHei")

    body = ft.Container(expand=True)

    def app_title(right=None):
        return ft.Row(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.WATER_DROP_ROUNDED, color="#3ba7ff", size=30),
                        ft.Text("D-Flow 模式檔案管理系統", size=22, weight=ft.FontWeight.BOLD, color="#ffffff"),
                        ft.Container(
                            content=ft.Text("v2.0 雛形", size=12, color="#9fb3d9"),
                            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                            bgcolor=FIELD,
                            border_radius=20,
                        ),
                    ],
                    spacing=10,
                ),
                right or ft.Container(),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    # ── 主頁面 ──
    def home_card(key):
        ws = WORKSPACES[key]
        accent = ws["accent"]

        def on_hover(e):
            hovered = e.data in (True, "true")
            e.control.scale = 1.03 if hovered else 1.0
            e.control.bgcolor = CARD_HI if hovered else CARD
            e.control.border = ft.Border.all(2 if hovered else 1, accent if hovered else BORDER)
            e.control.update()

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [ft.Text(ws["no"], size=22, color=accent, weight=ft.FontWeight.BOLD), badge(ws["status"], accent)],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(
                        content=ft.Icon(ws["icon"], size=72, color=accent),
                        alignment=ft.Alignment.CENTER,
                        padding=ft.Padding.symmetric(vertical=18),
                    ),
                    ft.Text(ws["title"], size=24, weight=ft.FontWeight.BOLD, color="#ffffff", text_align=ft.TextAlign.CENTER),
                    ft.Text(ws["desc"], size=13, color=MUTED, text_align=ft.TextAlign.CENTER),
                    ft.Divider(height=20, color=BORDER),
                    *[
                        ft.Row([ft.Icon(ft.Icons.CHECK_ROUNDED, size=16, color=accent), ft.Text(b, size=13, color=TEXT)], spacing=8)
                        for b in ws["bullets"]
                    ],
                    ft.Container(expand=True),
                    ft.Row(
                        [ft.Text("進入", size=14, color=accent, weight=ft.FontWeight.W_600), ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, color=accent, size=18)],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=4,
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            padding=24,
            bgcolor=CARD,
            border_radius=18,
            border=ft.Border.all(1, BORDER),
            expand=True,
            height=460,
            scale=1.0,
            animate_scale=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
            on_hover=on_hover,
            on_click=lambda e, k=key: show_workspace(k, first_tab(k)),
        )

    def show_home():
        body.content = ft.Column(
            [
                app_title(
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.PERSON_ROUNDED, color=MUTED, size=18),
                            ft.Text("王小明 <wang@example.com>", size=13, color=MUTED),
                        ],
                        spacing=6,
                    )
                ),
                ft.Container(height=30),
                ft.Text("要進行哪一項工作？", size=28, weight=ft.FontWeight.BOLD, color="#ffffff"),
                ft.Text("依照 Delft3D FM 1D2D 的工作流程：建置模型 → 執行模擬 → 檢視成果", size=14, color=MUTED),
                ft.Container(height=20),
                ft.Row([home_card(k) for k in WORKSPACES], spacing=22),
                ft.Container(expand=True),
                ft.Row(
                    [ft.Text("最近開啟：範例專案（模型建置，2026-09-29 14:43）", size=12, color=MUTED)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=6,
            expand=True,
        )
        page.update()

    # ── 工作區 ──
    def first_tab(key):
        return next(i for i, t in enumerate(WORKSPACES[key]["tabs"]) if not t[2])

    def tab_button(key, idx, selected):
        ws = WORKSPACES[key]
        name, icon, planned = ws["tabs"][idx]
        fg = "#ffffff" if selected else MUTED
        items = [ft.Icon(icon, size=16, color=fg), ft.Text(name, size=13, color=fg)]
        if planned:
            items.append(ft.Container(content=ft.Text("規劃中", size=10, color=MUTED), padding=ft.Padding.symmetric(horizontal=6, vertical=1), border_radius=8, border=ft.Border.all(1, MUTED)))
        return ft.Container(
            content=ft.Row(items, spacing=6),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            bgcolor=ft.Colors.with_opacity(0.18, ws["accent"]) if selected else None,
            border=ft.Border.only(bottom=ft.BorderSide(3, ws["accent"] if selected else "#00000000")),
            border_radius=ft.BorderRadius.only(top_left=10, top_right=10),
            on_click=lambda e: show_workspace(key, idx),
            ink=True,
        )

    def show_workspace(key, idx):
        ws = WORKSPACES[key]
        # 其他兩個工作區的快速切換
        switcher = ft.Row(
            [
                ft.IconButton(
                    WORKSPACES[k]["icon"],
                    icon_color=WORKSPACES[k]["accent"] if k == key else MUTED,
                    tooltip=WORKSPACES[k]["title"],
                    on_click=lambda e, k=k: show_workspace(k, first_tab(k)),
                )
                for k in WORKSPACES
            ],
            spacing=0,
        )
        top = ft.Row(
            [
                ft.Row(
                    [
                        ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="回主頁面", on_click=lambda e: show_home()),
                        ft.Icon(ws["icon"], color=ws["accent"], size=30),
                        ft.Text(f"{ws['no']} {ws['title']}", size=22, weight=ft.FontWeight.BOLD, color="#ffffff"),
                        badge(ws["status"], ws["accent"]),
                    ],
                    spacing=10,
                ),
                switcher,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        tabs = ft.Container(
            content=ft.Column(
                [
                    ft.Row([tab_button(key, i, i == idx) for i in range(len(ws["tabs"]))], spacing=4),
                    ft.Divider(height=1, color=BORDER),
                    ft.Container(content=tab_body(key, idx), padding=ft.Padding.only(top=16), expand=True),
                ],
                spacing=0,
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )
        body.content = ft.Column([top, HEADERS[key](), tabs], spacing=14, expand=True)
        page.update()

    page.add(body)

    # 命令列參數：python flet_home_demo.py run 2 → 直接開指定工作區與分頁（截圖用）
    if len(sys.argv) >= 2 and sys.argv[1] in WORKSPACES:
        show_workspace(sys.argv[1], int(sys.argv[2]) if len(sys.argv) >= 3 else first_tab(sys.argv[1]))
    else:
        show_home()


ft.run(main)
