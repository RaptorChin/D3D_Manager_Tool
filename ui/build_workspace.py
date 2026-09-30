"""① 模型建置工作區（UI_PLAN.md §1.3）：v1.2.1 的所有功能，行為不變，只換成 Flet 畫面。

對照 app_ctk.py（v1.2.1）：
- 共用資訊列 ← 工作資料夾列、Git 身分列（瀏覽本機、從雲端下載、狀態檢查、設定 Git 身分）
- 本機建置   ← 時光機列 ＋「📸 模型建置快照」
- 推送到遠端 ← 「☁️ 遠端伺服器備份」
- 版本歷史   ← 「📜 版本歷史」
v1.2.1 的「選擇主控檔 (.mdu)」只供隱藏中的舊分頁使用，不搬移（UI_PLAN.md §4）。

core/git_control.py 不做任何修改。
"""
from __future__ import annotations

import os
from typing import Callable

import flet as ft

from core.git_control import GitModelManager

from . import dialogs
from . import theme as t

NO_FOLDER = "(尚未選擇工作資料夾)"
DESC_PLACEHOLDER = "請選擇版本以查看說明..."


class BuildWorkspace:
    def __init__(self, page: ft.Page, on_identity_changed: Callable[[str], None]):
        self.page = page
        self.on_identity_changed = on_identity_changed
        self.repo_path = ""
        self.git_mgr: GitModelManager | None = None
        self.history_git_mgr: GitModelManager | None = None
        self.picker = ft.FilePicker()  # 在頁面執行期間建立即自動註冊

        # ── 共用資訊列元件 ──
        self.path_text = ft.Text(NO_FOLDER, size=14, color=t.TEXT, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
        self.identity_text = ft.Text("", size=14, color=t.LINK)

        # ── 本機建置 ──
        self.branch_dd = t.dropdown([], width=300, on_select=self.on_branch_select)
        self.branch_desc = ft.Text(DESC_PLACEHOLDER, size=13, color=t.LINK, selectable=True)
        self.build_ver = t.text_field("建置標籤（例如 v1.0-base）")
        self.build_desc = t.text_field("建置內容說明", multiline=True)

        # ── 推送到遠端 ──
        self.remote_field = t.text_field("遠端位址", hint=r"https://github.com/使用者/專案.git 或 \\伺服器\共用資料夾\專案",
                                         expand=True)

        # ── 版本歷史 ──
        self.history_path_text = ft.Text("(尚未指定，預設為目前專案資料夾)", size=14, color=t.TEXT, selectable=True)
        self.history_dd = t.dropdown([], width=300, on_select=self.on_history_branch_select)
        self.history_list = ft.Column(spacing=0)
        self._set_history_message("請先在上方指定要查詢的資料夾（預設為目前專案資料夾）。")

        self.refresh_identity()

    # ════════════════════════════════════════════
    # 畫面
    # ════════════════════════════════════════════
    def info_bar(self) -> ft.Control:
        return t.card(
            ft.Row(
                [
                    ft.Icon(ft.Icons.FOLDER_ROUNDED, color=t.ACCENT_BUILD, size=22),
                    ft.Column([t.caption("工作資料夾（Delta Shell 專案）"), self.path_text], spacing=2, expand=True),
                    ft.Column([t.caption("Git 身分"), self.identity_text], spacing=2),
                    ft.IconButton(ft.Icons.SETTINGS_ROUNDED, tooltip="設定 Git 身分",
                                  on_click=lambda e: self.open_identity_dialog()),
                    t.pill_button("瀏覽本機", ft.Icons.FOLDER_OPEN_ROUNDED, t.PRIMARY, on_click=self.browse_local),
                    t.pill_button("從雲端下載", ft.Icons.CLOUD_DOWNLOAD_ROUNDED, t.SUCCESS,
                                  on_click=lambda e: self.open_clone_dialog()),
                    t.outline_button("狀態檢查", ft.Icons.FACT_CHECK_ROUNDED, on_click=self.check_status),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=14,
        )

    def tab_local(self) -> ft.Control:
        time_machine = t.card(
            ft.Column(
                [
                    t.section_title("時光機（切換版本）", ft.Icons.HOURGLASS_BOTTOM_ROUNDED, t.WARNING),
                    ft.Row(
                        [
                            self.branch_dd,
                            ft.IconButton(ft.Icons.REFRESH_ROUNDED, tooltip="重新整理",
                                          on_click=lambda e: self.refresh_branches()),
                        ],
                        spacing=8,
                    ),
                    ft.Row([t.pill_button("恢復至此版本", ft.Icons.RESTORE_ROUNDED, t.DANGER, on_click=self.restore_version)]),
                    ft.Row(
                        [ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=14, color=t.MUTED), t.caption("版本說明：")],
                        spacing=6,
                    ),
                    self.branch_desc,
                ],
                spacing=12,
            ),
            expand=True,
        )
        snapshot = t.card(
            ft.Column(
                [
                    t.section_title("儲存建置快照", ft.Icons.CAMERA_ALT_ROUNDED, t.ACCENT_BUILD),
                    t.caption("把目前的修改存成一個新版本（build/…）；只記錄 .dsproj 與 .dsproj_data"),
                    self.build_ver,
                    self.build_desc,
                    ft.Row([t.pill_button("儲存建置進度", ft.Icons.SAVE_ROUNDED, t.PRIMARY, on_click=self.save_snapshot)]),
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            expand=True,
        )
        return ft.Row([time_machine, snapshot], spacing=14, vertical_alignment=ft.CrossAxisAlignment.START)

    def tab_push(self) -> ft.Control:
        bind = t.card(
            ft.Column(
                [
                    t.section_title("1. 綁定遠端路徑", ft.Icons.LINK_ROUNDED, t.ACCENT_BUILD),
                    t.caption("GitHub HTTPS，或內網 \\\\伺服器\\共用資料夾\\專案（開頭必須是兩個反斜線；資料夾不存在會自動建立）"),
                    t.caption("💡 內網路徑建議按「瀏覽」直接選取，避免打錯；可在選取視窗中按「新增資料夾」建立專案資料夾。"),
                    ft.Row(
                        [
                            self.remote_field,
                            t.outline_button("瀏覽", ft.Icons.FOLDER_OPEN_ROUNDED, on_click=self.browse_remote),
                            t.pill_button("綁定遠端路徑", ft.Icons.LINK_ROUNDED, t.PRIMARY, on_click=self.bind_remote),
                        ],
                        spacing=10,
                    ),
                ],
                spacing=12,
            )
        )
        push = t.card(
            ft.Column(
                [
                    t.section_title("2. 推送到遠端伺服器", ft.Icons.CLOUD_UPLOAD_ROUNDED, t.ACCENT_BUILD),
                    t.caption("依序：更新規則 → 上傳 LFS 大檔 → 推送版本紀錄 → 寫入 .dsproj / .dsproj_data"),
                    ft.Row([t.pill_button("開始推送到遠端伺服器", ft.Icons.ROCKET_LAUNCH_ROUNDED, t.SUCCESS,
                                          on_click=self.push)]),
                    t.caption("💡 僅推送 Delta Shell 執行檔：*.dsproj 與 *.dsproj_data。"
                              "內網會把 Git 追蹤與上述檔案放在同一個遠端資料夾。"),
                ],
                spacing=12,
            )
        )
        return ft.Column([bind, push], spacing=14)

    def tab_history(self) -> ft.Control:
        return t.card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column([t.caption("查詢資料夾"), self.history_path_text], spacing=2, expand=True),
                            t.outline_button("瀏覽...", ft.Icons.FOLDER_OPEN_ROUNDED, on_click=self.browse_history),
                            t.outline_button("使用遠端備份路徑", ft.Icons.CLOUD_ROUNDED,
                                             on_click=lambda e: self.use_remote_backup_for_history()),
                            t.outline_button("回到目前專案", ft.Icons.UNDO_ROUNDED,
                                             on_click=lambda e: self.use_current_project_for_history()),
                        ],
                        spacing=10,
                    ),
                    ft.Row(
                        [
                            ft.Text("選擇版次（分支）：", color=t.MUTED),
                            self.history_dd,
                            ft.IconButton(ft.Icons.REFRESH_ROUNDED, tooltip="重新整理",
                                          on_click=lambda e: self.refresh_commit_history()),
                        ],
                        spacing=8,
                    ),
                    self.history_list,
                ],
                spacing=14,
            ),
            expand=True,
        )

    # ════════════════════════════════════════════
    # Git 身分
    # ════════════════════════════════════════════
    def refresh_identity(self):
        name, email = GitModelManager.get_global_user_identity()
        if name and email:
            text = f"{name}  <{email}>"
        elif name or email:
            text = f"{name or '(未設定名稱)'}  <{email or '(未設定信箱)'}>"
        else:
            text = "尚未設定（儲存版本前請先設定）"
        self.identity_text.value = text
        self.on_identity_changed(text)

    def open_identity_dialog(self, force_prompt: bool = False):
        tip = (
            "第一次使用 Git 請先設定身分，之後建立的版本都會署名為此名稱與信箱。\n"
            "此設定寫入本機全域（git config --global），與目前專案無關。"
            if force_prompt else "可隨時修改本機全域的 Git 使用者名稱與信箱。"
        )
        name, email = GitModelManager.get_global_user_identity()
        name_field = t.text_field("使用者名稱", name or "", hint="例如：王小明")
        email_field = t.text_field("電子郵件", email or "", hint="例如：wang@company.com")
        error = ft.Text("", color=t.DANGER, size=13)

        def save(e):
            try:
                msg = GitModelManager.set_global_user_identity(name_field.value or "", email_field.value or "")
            except Exception as ex:  # noqa: BLE001
                error.value = str(ex)
                self.page.update()
                return
            self.page.pop_dialog()
            self.refresh_identity()
            dialogs.alert(self.page, "設定完成", msg, "success")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚙️ 設定 Git 身分", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                ft.Column([t.caption(tip), name_field, email_field, error], spacing=12, tight=True), width=480
            ),
            actions=[
                ft.TextButton("稍後再說" if force_prompt else "取消", on_click=lambda e: self.page.pop_dialog()),
                t.pill_button("儲存設定", ft.Icons.SAVE_ROUNDED, t.PRIMARY, on_click=save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dlg)

    def check_identity_on_startup(self):
        if not GitModelManager.is_global_user_configured():
            self.open_identity_dialog(force_prompt=True)

    # ════════════════════════════════════════════
    # 開啟工作資料夾（v1.2.1 load_project 的三種情境）
    # ════════════════════════════════════════════
    async def browse_local(self, e):
        folder = await self.picker.get_directory_path(dialog_title="選擇 Delta Shell 專案所在的資料夾")
        if folder:
            self.page.run_thread(self.load_project, folder)

    def load_project(self, folder: str):
        self._set_repo(folder)
        self.page.update()
        mgr = self.git_mgr

        def process(title, task):
            dialogs.run_with_progress(self.page, title, task,
                                      on_success=lambda _: self.post_load_project(),
                                      on_error=lambda _: self.post_load_project())  # 失敗也要把畫面載出來

        # 情境一：完全沒建立過 Git
        if not mgr.is_initialized():
            dialogs.confirm(
                self.page, "尚未初始化",
                "此資料夾尚未建立 Git 版本控制。\n\n是否要立即初始化並拍下初始快照？\n（若專案檔案龐大可能需要一至數分鐘時間）",
                on_yes=lambda: process("📦 專案初始化", mgr.do_initial_setup),
                on_no=lambda: self.page.run_thread(self.post_load_project),
                yes_text="立即初始化", no_text="先不要",
            )
        # 情境二：已建立過，但有修改忘記存檔
        elif mgr.has_uncommitted_changes():
            dialogs.confirm(
                self.page, "發現未儲存變更",
                "系統發現此專案內有尚未儲存的檔案變動。\n\n是否要在載入前，自動將這些變動儲存成新的快照？",
                on_yes=lambda: process("💾 自動儲存變更", mgr.do_auto_commit),
                on_no=lambda: self.page.run_thread(self.post_load_project),
                yes_text="自動儲存", no_text="不用",
            )
        # 情境三：一切乾淨，直接載入
        else:
            self.post_load_project()

    def _set_repo(self, folder: str):
        self.repo_path = folder
        self.path_text.value = folder
        self.path_text.tooltip = folder  # 路徑太長被省略時，滑鼠移上去可看完整路徑
        self.git_mgr = GitModelManager(folder)

    def post_load_project(self):
        """讀取版本清單與更新畫面的最終步驟"""
        self.refresh_branches(update=False)
        self.set_history_folder(self.repo_path, update=False)
        remote = self.git_mgr.get_remote_url() if self.git_mgr else ""
        self.remote_field.value = remote or ""
        self.page.update()

    def _require_project(self) -> bool:
        if self.git_mgr:
            return True
        dialogs.alert(self.page, "尚未選擇工作資料夾", "請先按「瀏覽本機」選擇 Delta Shell 專案資料夾，或「從雲端下載」。", "warning")
        return False

    def check_status(self, e):
        if not self._require_project():
            return
        try:
            dialogs.alert(self.page, "狀態", self.git_mgr.init_repo(), "success")
        except Exception as ex:  # noqa: BLE001
            dialogs.alert(self.page, "錯誤", str(ex), "error")

    # ════════════════════════════════════════════
    # 時光機
    # ════════════════════════════════════════════
    def refresh_branches(self, update: bool = True):
        branches = self.git_mgr.get_all_branches() if self.git_mgr else []
        if branches:
            current = self.git_mgr.get_current_branch()
            t.set_dropdown_options(self.branch_dd, branches, current if current in branches else branches[0])
            self.branch_desc.value = self.git_mgr.get_branch_info(self.branch_dd.value)
        else:
            t.set_dropdown_options(self.branch_dd, [], None)
            self.branch_desc.value = DESC_PLACEHOLDER
        if update:
            self.page.update()

    def on_branch_select(self, e):
        if self.git_mgr and self.branch_dd.value:
            self.branch_desc.value = self.git_mgr.get_branch_info(self.branch_dd.value)
            self.page.update()

    def restore_version(self, e):
        if not self._require_project():
            return
        selected = self.branch_dd.value
        if not selected:
            return

        def do_restore():
            try:
                msg = self.git_mgr.switch_branch(selected)
            except Exception as ex:  # noqa: BLE001
                dialogs.alert(self.page, "切換失敗", str(ex), "error")
                return
            self.refresh_branches(update=False)
            self.refresh_commit_history(update=False)
            dialogs.alert(self.page, "成功", msg, "success")

        dialogs.confirm(
            self.page, "⚠️ 時光倒流確認",
            f"確定要將專案恢復到【{selected}】嗎？\n\n資料夾內的設定檔將瞬間被替換成該版本的內容！\n"
            "（目前尚未存檔的修改可能會遺失，建議先儲存建置快照）",
            on_yes=lambda: self.page.run_thread(do_restore),
            yes_text="恢復至此版本", danger=True,
        )

    # ════════════════════════════════════════════
    # 建置快照
    # ════════════════════════════════════════════
    def save_snapshot(self, e):
        if not self._require_project():
            return
        ver = (self.build_ver.value or "").strip()
        if not ver:
            dialogs.alert(self.page, "缺少建置標籤", "請先填寫建置標籤（例如 v1.0-base）。", "warning")
            return
        desc = (self.build_desc.value or "").strip()
        mgr = self.git_mgr

        def task(update):
            update("正在建立版本分支...", 20)
            mgr.create_scenario_branch(f"build/{ver}")
            update("正在套用 LFS 規則並寫入版本庫...", 50)
            msg = mgr.commit_scenario_changes(desc)
            update("完成！", 100)
            return msg

        def done(msg):
            self.refresh_branches(update=False)
            self.refresh_commit_history(update=False)
            dialogs.alert(self.page, "儲存狀態", f"操作完成！\n{msg}", "success")

        dialogs.run_with_progress(self.page, "💾 儲存建置進度", task, on_success=done)

    # ════════════════════════════════════════════
    # 遠端：綁定、推送、下載
    # ════════════════════════════════════════════
    async def browse_remote(self, e):
        folder = await self.picker.get_directory_path(
            dialog_title="選擇遠端（內網共用）資料夾，例如 \\\\伺服器\\共用資料夾\\專案名稱"
        )
        if folder:
            self.remote_field.value = folder
            self.page.update()

    def bind_remote(self, e):
        if not self._require_project():
            return
        url = (self.remote_field.value or "").strip()
        if not url:
            dialogs.alert(self.page, "警告", "請先填寫路徑！", "warning")
            return
        try:
            msg = self.git_mgr.set_remote_url(url)
        except Exception as ex:  # noqa: BLE001
            dialogs.alert(self.page, "錯誤", str(ex), "error")
            return
        normalized = self.git_mgr.get_remote_url()
        if normalized:
            self.remote_field.value = normalized  # 回填正規化後的路徑
        dialogs.alert(self.page, "成功", msg, "success")

    def push(self, e):
        if not self._require_project():
            return
        if not self.git_mgr.get_remote_url():
            dialogs.alert(self.page, "警告", "請先綁定遠端路徑後再推送。", "warning")
            return

        def done(push_warning):
            if push_warning:
                dialogs.alert(
                    self.page, "⚠️ 執行檔已複製，但版本紀錄推送失敗",
                    "已將 .dsproj 與 .dsproj_data 複製到遠端資料夾，"
                    "但 Git 版本紀錄推送失敗，這次的變更歷程「不會」同步到遠端！\n\n"
                    f"[詳細原因]\n{push_warning}\n\n"
                    "常見原因：遠端資料夾內已存在非此工具管理的舊檔案，"
                    "導致 Git 檢出版本時被拒絕覆蓋。請確認遠端路徑或聯絡管理員後再重新推送。",
                    "warning",
                )
            else:
                dialogs.alert(self.page, "上傳成功 🎉",
                              "已推送 Git 版本，並將 .dsproj 與 .dsproj_data 寫入同一個遠端資料夾。", "success")
            self.refresh_commit_history()

        dialogs.run_with_progress(
            self.page, "🚀 遠端上傳作業中", self.git_mgr.push_with_progress, on_success=done,
            subtitle="正在推送版本，並把模式執行檔寫入遠端資料夾...",
        )

    def open_clone_dialog(self):
        url_field = t.text_field("GitHub 網址 或 內網共用資料夾", hint=r"例如 \\伺服器\共用\NWT_TM")
        dest_text = ft.Text("(尚未選擇)", size=14, color=t.TEXT, selectable=True)
        dest = {"path": ""}
        status = ft.Text("", size=12, color=t.MUTED)
        pct = ft.Text("", size=13, color=t.ACCENT_BUILD, weight=ft.FontWeight.BOLD)
        bar = ft.ProgressBar(value=0, bar_height=8, border_radius=4, color=t.SUCCESS, bgcolor=t.FIELD, visible=False)

        async def browse(e):
            folder = await self.picker.get_directory_path(dialog_title="選擇儲存到本機的資料夾")
            if folder:
                dest["path"] = folder
                dest_text.value = folder
                self.page.update()

        def update(text, p):
            status.value = text if len(text) <= 80 else text[:77] + "..."
            if p is not None:
                bar.value = min(max(float(p), 0), 100) / 100
                pct.value = f"{int(p)}%"
            self.page.update()

        def worker(url, final_path):
            try:
                new_version = GitModelManager.clone_repo(url, final_path, update)
            except Exception as ex:  # noqa: BLE001
                status.value = f"❌ 下載失敗：{str(ex).strip() or repr(ex)}"
                status.color = t.DANGER
                start_btn.disabled = False
                self.page.update()
                return
            extra = ""
            if new_version:
                desc = GitModelManager(final_path).get_branch_info(new_version).strip()
                extra = f"\n\n新版本：{new_version}\n說明：{desc or 'Pull from server'}"
            self.page.pop_dialog()
            self._set_repo(final_path)
            self.post_load_project()
            dialogs.alert(self.page, "下載完成 🎉", f"已同步執行檔至：\n{final_path}{extra}", "success")

        def start(e):
            url = (url_field.value or "").strip()
            final_path = dest["path"]
            if not url or not final_path:
                status.value, status.color = "請填寫路徑與目標資料夾！", t.WARNING
                self.page.update()
                return
            if not os.path.isdir(final_path):
                try:
                    os.makedirs(final_path, exist_ok=True)
                except Exception as ex:  # noqa: BLE001
                    status.value, status.color = f"無法使用本機資料夾：{ex}", t.DANGER
                    self.page.update()
                    return
            start_btn.disabled = True
            bar.visible = True
            status.value, status.color = "等待開始...", t.MUTED
            self.page.update()
            self.page.run_thread(worker, url, final_path)

        start_btn = t.pill_button("開始下載", ft.Icons.ROCKET_LAUNCH_ROUNDED, t.SUCCESS, on_click=start)
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("📥 從遠端下載專案 (Clone)", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                ft.Column(
                    [
                        ft.Text("1. 輸入 GitHub 網址 或 內網共用資料夾", weight=ft.FontWeight.BOLD),
                        t.caption("內網只同步 .dsproj / .dsproj_data；會依目前版本新增「.1-Pull」版本，"
                                  "說明為 Pull from server 加上當下日期時間。"),
                        url_field,
                        ft.Text("2. 選擇儲存到本機的資料夾", weight=ft.FontWeight.BOLD),
                        ft.Row([ft.Container(dest_text, expand=True),
                                t.outline_button("瀏覽", ft.Icons.FOLDER_OPEN_ROUNDED, on_click=browse)]),
                        pct, bar, status,
                    ],
                    spacing=10,
                    tight=True,
                ),
                width=560,
            ),
            actions=[ft.TextButton("關閉", on_click=lambda e: self.page.pop_dialog()), start_btn],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dlg)

    # ════════════════════════════════════════════
    # 版本歷史
    # ════════════════════════════════════════════
    async def browse_history(self, e):
        folder = await self.picker.get_directory_path(dialog_title="選擇要查詢版本歷史的資料夾（例如遠端伺服器備份路徑）")
        if folder:
            self.page.run_thread(self.set_history_folder, folder)

    def use_current_project_for_history(self):
        if not self.repo_path:
            dialogs.alert(self.page, "警告", "尚未載入任何專案資料夾。", "warning")
            return
        self.page.run_thread(self.set_history_folder, self.repo_path)

    def use_remote_backup_for_history(self):
        url = (self.remote_field.value or "").strip()
        if not url:
            dialogs.alert(self.page, "警告", "請先在「推送到遠端」分頁輸入並綁定遠端路徑。", "warning")
            return
        if not GitModelManager.is_filesystem_remote(url):
            dialogs.alert(self.page, "警告", "此功能僅支援內網共用資料夾路徑；GitHub 等網址請改用「瀏覽」選擇本機下載後的資料夾。", "warning")
            return
        path = GitModelManager.filesystem_remote_to_path(url)
        if not os.path.isdir(path):
            dialogs.alert(self.page, "錯誤", f"找不到遠端資料夾：\n{path}", "error")
            return
        self.page.run_thread(self.set_history_folder, path)

    def set_history_folder(self, folder: str, update: bool = True):
        self.history_path_text.value = folder
        self.history_git_mgr = GitModelManager(GitModelManager.resolve_git_root(folder))
        self.refresh_commit_history(update=update)

    def refresh_commit_history(self, update: bool = True):
        mgr = self.history_git_mgr
        if not mgr:
            t.set_dropdown_options(self.history_dd, [], None)
            self._set_history_message("請先在上方指定要查詢的資料夾。")
        else:
            branches = mgr.get_all_branches()
            if not branches:
                t.set_dropdown_options(self.history_dd, [], None)
                self._set_history_message("尚無任何版次紀錄。")
            else:
                latest = mgr.get_latest_branch()
                t.set_dropdown_options(self.history_dd, branches, latest if latest in branches else branches[0])
                self._render_commits()
        if update:
            self.page.update()

    def on_history_branch_select(self, e):
        self._render_commits()
        self.page.update()

    def _render_commits(self):
        mgr, branch = self.history_git_mgr, self.history_dd.value
        if not mgr or not branch:
            return
        commits = mgr.get_commit_log(branch)
        if not commits:
            self._set_history_message(f"「{branch}」尚無提交紀錄。")
            return
        rows = [t.caption(f"📌 版次「{branch}」共 {len(commits)} 筆紀錄（新到舊）")]
        for c in commits:
            rows.append(ft.Container(
                content=ft.Row(
                    [
                        ft.Text(c["hash"], size=12, color=t.LINK, font_family=t.FONT_CODE, width=80),
                        ft.Text(c["date"], size=12, color=t.MUTED, width=150),
                        ft.Text(c["author"], size=12, color=t.TEXT, width=110, tooltip=c.get("email", "")),
                        ft.Text(c["message"], size=13, color=t.TEXT, expand=True, selectable=True),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                border=ft.Border.only(bottom=ft.BorderSide(1, t.BORDER)),
            ))
        self.history_list.controls = rows

    def _set_history_message(self, text: str):
        self.history_list.controls = [ft.Container(t.caption(text), padding=12)]
