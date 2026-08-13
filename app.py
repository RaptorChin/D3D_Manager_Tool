import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
import re

from core.git_control import GitModelManager
from core.d3d_parser import MduParser
from core.d3d_runner import run_delft3d

ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue")

# 暫時隱藏「情境參數設定」「執行模擬」（目前僅使用建置與備份）
SHOW_SCENARIO_AND_RUN_TABS = False  

class D3DManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🌊 D-Flow FM 模式檔案管理系統")
        self.root.geometry("950x800")
        
        self.repo_path = ""
        self.mdu_files = []
        self.git_mgr = None
        self.mdu_data = None
        
        self.setup_ui()

    def setup_ui(self):
        font_title = ctk.CTkFont(family="微軟正黑體", size=14, weight="bold")
        font_normal = ctk.CTkFont(family="微軟正黑體", size=13)
        font_code = ctk.CTkFont(family="Consolas", size=12)

        frame_top = ctk.CTkFrame(self.root, corner_radius=10)
        frame_top.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(frame_top, text="工作資料夾:", font=font_title).pack(side="left", padx=10, pady=10)
        self.path_var = ctk.StringVar()
        ctk.CTkEntry(frame_top, textvariable=self.path_var, width=350, font=font_normal, state="readonly").pack(side="left", padx=5)
        
        ctk.CTkButton(frame_top, text="📂 瀏覽本機", font=font_normal, command=self.load_project, width=100).pack(side="left", padx=5)
        ctk.CTkButton(frame_top, text="📥 從雲端下載 (Clone)", font=font_normal, fg_color="#2B7A0B", hover_color="#1E5607", command=self.open_clone_dialog, width=150).pack(side="left", padx=5)
        ctk.CTkButton(frame_top, text="狀態檢查", font=font_normal, fg_color="#5A5A5A", hover_color="#404040", command=self.init_git, width=100).pack(side="left", padx=5)

        frame_history = ctk.CTkFrame(self.root, corner_radius=10)
        frame_history.pack(fill="x", padx=15, pady=5)
        
        history_top = ctk.CTkFrame(frame_history, fg_color="transparent")
        history_top.pack(fill="x", padx=10, pady=(10, 0))
        
        ctk.CTkLabel(history_top, text="⏳ 時光機 (切換版本):", font=font_title).pack(side="left")
        self.branch_combo = ctk.CTkComboBox(history_top, width=250, font=font_normal, command=self.on_branch_select)
        self.branch_combo.pack(side="left", padx=10)
        
        ctk.CTkButton(history_top, text="重新整理", font=font_normal, width=80, fg_color="#5A5A5A", hover_color="#404040", command=self.refresh_branches).pack(side="left", padx=5)
        ctk.CTkButton(history_top, text="恢復至此版本", font=font_normal, width=120, fg_color="#D9534F", hover_color="#C9302C", command=self.restore_version).pack(side="left", padx=10)

        history_bottom = ctk.CTkFrame(frame_history, fg_color="transparent")
        history_bottom.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(history_bottom, text="📝 版本說明:", font=font_title, text_color="gray").pack(side="left", anchor="nw")
        self.branch_desc_var = ctk.StringVar(value="請選擇版本以查看說明...")
        ctk.CTkLabel(history_bottom, textvariable=self.branch_desc_var, font=font_normal, text_color="#3498DB", justify="left", wraplength=700).pack(side="left", padx=10, anchor="nw")

        frame_mdu = ctk.CTkFrame(self.root, corner_radius=10)
        frame_mdu.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(frame_mdu, text="選擇主控檔 (.mdu):", font=font_title).pack(side="left", padx=10, pady=10)
        self.mdu_combo = ctk.CTkComboBox(frame_mdu, width=400, font=font_normal, command=self.on_mdu_select)
        self.mdu_combo.pack(side="left", padx=5)

        self.tabview = ctk.CTkTabview(self.root, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        self.tab1 = self.tabview.add('📸 模型建置快照')
        if SHOW_SCENARIO_AND_RUN_TABS:
            self.tab2 = self.tabview.add('📝 情境參數設定')
            self.tab3 = self.tabview.add('▶️ 執行模擬')
        self.tab4 = self.tabview.add('☁️ 遠端伺服器備份')

        self.tstop_var = ctk.StringVar()
        self.setup_tab4(font_title, font_normal)
        self.setup_tab1(font_title, font_normal)
        if SHOW_SCENARIO_AND_RUN_TABS:
            self.setup_tab2(font_title, font_normal)
            self.setup_tab3(font_title, font_normal, font_code)

        frame_bottom = ctk.CTkFrame(self.root, fg_color="transparent")
        frame_bottom.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkButton(
            frame_bottom,
            text="結束",
            font=font_title,
            width=100,
            fg_color="#D9534F",
            hover_color="#C9302C",
            command=self.quit_app,
        ).pack(side="right")

    def quit_app(self):
        self.root.destroy()

    def on_branch_select(self, choice=None):
        if not self.git_mgr: return
        selected = self.branch_combo.get()
        if selected:
            desc = self.git_mgr.get_branch_info(selected)
            self.branch_desc_var.set(desc)

    # 🌟 重新設計的核心載入流程
    def load_project(self):
        folder = filedialog.askdirectory()
        if not folder: return
        
        self.repo_path = folder
        self.path_var.set(folder)
        self.git_mgr = GitModelManager(folder)

        # 情境一：完全沒建立過 Git
        if not self.git_mgr.is_initialized():
            ans = messagebox.askyesno("尚未初始化", "此資料夾尚未建立 Git 版本控制。\n\n是否要立即初始化並拍下初始快照？\n(若專案檔案龐大可能需要一至數分鐘時間)")
            if ans:
                self.open_local_processing_dialog("📦 專案初始化", self.git_mgr.do_initial_setup)
            else:
                self._post_load_project() # 跳過，直接讀取檔案
                
        # 情境二：已經建立過，但有修改忘記存檔
        elif self.git_mgr.has_uncommitted_changes():
            ans = messagebox.askyesno("發現未儲存變更", "系統發現此專案內有尚未儲存的檔案變動。\n\n是否要在載入前，自動將這些變動儲存成新的快照？")
            if ans:
                self.open_local_processing_dialog("💾 自動儲存變更", self.git_mgr.do_auto_commit)
            else:
                self._post_load_project() # 跳過，直接讀取檔案
                
        # 情境三：一切乾淨，直接載入
        else:
            self._post_load_project()

    # 🌟 本機任務專用的彈出進度條視窗
    def open_local_processing_dialog(self, title, task_func):
        win = ctk.CTkToplevel(self.root)
        win.title(title)
        win.geometry("550x200")
        win.grab_set()

        status_label = ctk.CTkLabel(win, text="準備處理...", font=("微軟正黑體", 14, "bold"))
        status_label.pack(pady=(30, 10))

        pct_label = ctk.CTkLabel(win, text="0%", text_color="#3498DB", font=("Arial", 14, "bold"))
        pct_label.pack()

        progress_bar = ctk.CTkProgressBar(win, width=450)
        progress_bar.set(0)
        progress_bar.pack(pady=10)

        def update_ui(text, pct):
            def _update():
                status_label.configure(text=text)
                if pct is not None:
                    progress_bar.set(pct / 100.0)
                    pct_label.configure(text=f"{pct}%")
            self.root.after(0, _update)

        def _thread_task():
            try:
                task_func(update_ui) # 執行背景作業
                self.root.after(0, win.destroy)
                self.root.after(0, self._post_load_project) # 成功後接續載入介面
            except Exception as e:
                err = str(e).strip() or repr(e)
                def _fail(msg=err):
                    messagebox.showerror("處理失敗", msg, parent=win)
                    win.destroy()
                    self._post_load_project() # 就算失敗也把介面載出來
                self.root.after(0, _fail)

        threading.Thread(target=_thread_task, daemon=True).start()

    def _post_load_project(self):
        """讀取檔案與更新畫面的最終步驟"""
        self.refresh_branches()
        remote_url = self.git_mgr.get_remote_url()
        self.github_url.delete(0, "end")
        if remote_url:
            self.github_url.insert(0, remote_url)

        # 🌟 智慧優化搜尋：跳過 output 等垃圾資料夾，避免介面卡死
        mdu_list = []
        for root_dir, dirs, files in os.walk(self.repo_path):
            # 讓程式不去挖 output 資料夾與隱藏檔
            dirs[:] = [d for d in dirs if d.lower() != "output" and not d.startswith("DFM_OUTPUT_") and d != ".git"]
            for f in files:
                if f.endswith(".mdu"):
                    mdu_list.append(os.path.join(root_dir, f))
                    
        self.mdu_files = mdu_list
        if self.mdu_files:
            self.mdu_combo.configure(values=self.mdu_files)
            self.mdu_combo.set(self.mdu_files[0])
            self.on_mdu_select(None)
        else:
            self.mdu_combo.configure(values=[])
            self.mdu_combo.set('')

    def refresh_branches(self):
        if self.git_mgr:
            branches = self.git_mgr.get_all_branches()
            self.branch_combo.configure(values=branches)
            if branches:
                current = self.git_mgr.get_current_branch()
                selected = current if current in branches else branches[0]
                self.branch_combo.set(selected)
                self.on_branch_select(selected)

    def restore_version(self):
        if not self.git_mgr: return
        selected_version = self.branch_combo.get()
        if not selected_version: return
        confirm = messagebox.askyesno("⚠️ 時光倒流確認", f"確定要將專案恢復到【{selected_version}】嗎？\n\n資料夾內的設定檔將瞬間被替換成該版本的內容！")
        if confirm:
            try:
                msg = self.git_mgr.switch_branch(selected_version)
                messagebox.showinfo("成功", msg)
                self.on_mdu_select(None) 
            except Exception as e:
                messagebox.showerror("切換失敗", str(e))

    def on_mdu_select(self, choice=None):
        selected_mdu = self.mdu_combo.get()
        if selected_mdu and os.path.exists(selected_mdu):
            self.mdu_data = MduParser.read_mdu(selected_mdu)
            current_tstop = self.mdu_data['time'].get('Tstop', '86400') if 'time' in self.mdu_data else '86400'
            if hasattr(self, "tstop_var"):
                self.tstop_var.set(current_tstop)

    def init_git(self):
        if self.git_mgr:
            try:
                msg = self.git_mgr.init_repo()
                messagebox.showinfo("狀態", msg)
            except Exception as e:
                messagebox.showerror("錯誤", str(e))

    def setup_tab1(self, font_title, font_normal):
        ctk.CTkLabel(self.tab1, text="建置標籤 (例如 v1.0-base):", font=font_title).pack(anchor="w", padx=20, pady=(20, 5))
        self.build_ver = ctk.CTkEntry(self.tab1, width=300, font=font_normal)
        self.build_ver.pack(anchor="w", padx=20)
        ctk.CTkLabel(self.tab1, text="建置內容說明:", font=font_title).pack(anchor="w", padx=20, pady=(20, 5))
        self.build_desc = ctk.CTkTextbox(self.tab1, height=100, width=500, font=font_normal)
        self.build_desc.pack(anchor="w", padx=20)
        ctk.CTkButton(self.tab1, text="💾 儲存建置進度", font=font_title, command=self.save_snapshot, fg_color="#0275D8").pack(anchor="w", padx=20, pady=20)

    def save_snapshot(self):
        if not self.git_mgr: return
        try:
            self.git_mgr.create_scenario_branch(f"build/{self.build_ver.get()}")
            msg = self.git_mgr.commit_scenario_changes(self.build_desc.get("1.0", "end").strip())
            messagebox.showinfo("儲存狀態", f"操作完成！\n{msg}")
            self.refresh_branches() 
        except Exception as e:
            messagebox.showerror("錯誤", str(e))

    def setup_tab2(self, font_title, font_normal):
        ctk.CTkLabel(self.tab2, text="情境名稱:", font=font_title).pack(anchor="w", padx=20, pady=(15, 5))
        self.scen_name = ctk.CTkEntry(self.tab2, width=300, font=font_normal)
        self.scen_name.pack(anchor="w", padx=20)
        ctk.CTkLabel(self.tab2, text="情境內容說明:", font=font_title).pack(anchor="w", padx=20, pady=(15, 5))
        self.scen_desc = ctk.CTkTextbox(self.tab2, height=80, width=500, font=font_normal)
        self.scen_desc.insert("end", "測試新邊界條件與時間")
        self.scen_desc.pack(anchor="w", padx=20)
        ctk.CTkLabel(self.tab2, text="模擬時間 Tstop (秒):", font=font_title).pack(anchor="w", padx=20, pady=(15, 5))
        self.tstop_var = ctk.StringVar()
        ctk.CTkEntry(self.tab2, textvariable=self.tstop_var, width=300, font=font_normal).pack(anchor="w", padx=20)
        ctk.CTkButton(self.tab2, text="💾 生成情境分支並修改 MDU", font=font_title, command=self.save_scenario, fg_color="#0275D8").pack(anchor="w", padx=20, pady=20)

    def save_scenario(self):
        if not self.git_mgr or not self.mdu_data: return
        try:
            self.git_mgr.create_scenario_branch(f"scenario/{self.scen_name.get()}")
            if 'time' not in self.mdu_data:
                self.mdu_data.add_section('time')
            self.mdu_data['time']['Tstop'] = self.tstop_var.get()
            MduParser.write_mdu(self.mdu_data, self.mdu_combo.get())
            user_desc = self.scen_desc.get("1.0", "end").strip()
            msg = self.git_mgr.commit_scenario_changes(user_desc)
            messagebox.showinfo("成功", f"情境 {self.scen_name.get()} 已更新！\n{msg}")
            self.refresh_branches()
        except Exception as e:
            messagebox.showerror("錯誤", str(e))

    def setup_tab3(self, font_title, font_normal, font_code):
        ctk.CTkLabel(self.tab3, text="d_hydro.exe 絕對路徑:", font=font_title).pack(anchor="w", padx=20, pady=(15, 5))
        self.exe_path = ctk.CTkEntry(self.tab3, width=600, font=font_normal)
        self.exe_path.insert(0, r"C:\Program Files\Deltares\Delft3D FM Suite 2023.01\x64\dflow2d3d\bin\d_hydro.exe")
        self.exe_path.pack(anchor="w", padx=20)
        ctk.CTkButton(self.tab3, text="🔥 開始執行模擬", font=font_title, command=self.run_simulation, fg_color="#F0AD4E", hover_color="#EC971F").pack(anchor="w", padx=20, pady=15)
        self.log_text = ctk.CTkTextbox(self.tab3, height=250, font=font_code, fg_color="#1E1E1E", text_color="#00FF00")
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def run_simulation(self):
        mdu_path = self.mdu_combo.get()
        exe = self.exe_path.get()
        if not mdu_path or not os.path.exists(exe): return
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "模式啟動中...\n")
        threading.Thread(target=self._run_process_thread, args=(mdu_path, exe), daemon=True).start()

    def _run_process_thread(self, mdu_path, exe):
        try:
            proc = run_delft3d(mdu_path, exe)
            while True:
                output = proc.stdout.readline()
                if output == '' and proc.poll() is not None: break
                if output:
                    self.log_text.insert("end", output)
                    self.log_text.see("end") 
            if proc.poll() == 0:
                messagebox.showinfo("完成", "模擬順利完成！")
            else:
                messagebox.showerror("錯誤", f"異常終止，代碼: {proc.poll()}")
        except Exception as e:
            messagebox.showerror("執行錯誤", str(e))

    def setup_tab4(self, font_title, font_normal):
        ctk.CTkLabel(
            self.tab4,
            text="1. 輸入遠端儲存庫位址（GitHub HTTPS，或內網 \\\\伺服器\\共用資料夾\\專案）:",
            font=font_title,
        ).pack(anchor="w", padx=20, pady=(20, 5))
        self.github_url = ctk.CTkEntry(self.tab4, width=560, font=font_normal)
        self.github_url.pack(anchor="w", padx=20)
        ctk.CTkButton(self.tab4, text="🔗 綁定遠端路徑", font=font_normal, command=self.bind_github).pack(
            anchor="w", padx=20, pady=10
        )

        ctk.CTkLabel(self.tab4, text="2. 將 .dsproj / .dsproj_data 與版本紀錄推送到遠端:", font=font_title).pack(
            anchor="w", padx=20, pady=(20, 5)
        )
        ctk.CTkButton(
            self.tab4,
            text="🚀 開始推送到遠端伺服器",
            font=font_title,
            fg_color="#2B7A0B",
            hover_color="#1E5607",
            command=self.open_push_dialog,
        ).pack(anchor="w", padx=20)
        ctk.CTkLabel(
            self.tab4,
            text=(
                "💡 僅推送 Delta Shell 執行檔：*.dsproj 與 *.dsproj_data。\n"
                "   內網會把 Git 追蹤與上述檔案放在同一個遠端資料夾。"
            ),
            font=font_normal,
            text_color="gray",
            justify="left",
        ).pack(anchor="w", padx=20, pady=10)

    def bind_github(self):
        if not self.git_mgr:
            return
        url = self.github_url.get().strip()
        if not url:
            return messagebox.showwarning("警告", "請先填寫路徑！")
        try:
            msg = self.git_mgr.set_remote_url(url)
            # 把正規化後的路徑回填到輸入框
            normalized = self.git_mgr.get_remote_url()
            if normalized:
                self.github_url.delete(0, "end")
                self.github_url.insert(0, normalized)
            messagebox.showinfo("成功", msg)
        except Exception as e:
            messagebox.showerror("錯誤", str(e))

    def open_push_dialog(self):
        if not self.git_mgr:
            return
        if not self.git_mgr.get_remote_url():
            return messagebox.showwarning("警告", "請先綁定遠端路徑後再推送。")

        push_win = ctk.CTkToplevel(self.root)
        push_win.title("🚀 遠端上傳作業中")
        push_win.geometry("560x240")
        push_win.grab_set()

        ctk.CTkLabel(
            push_win,
            text="正在推送版本，並把模式執行檔寫入遠端資料夾...",
            font=("微軟正黑體", 14, "bold"),
        ).pack(pady=(20, 10))
        pct_label = ctk.CTkLabel(push_win, text="0%", text_color="#3498DB", font=("Arial", 14, "bold"))
        pct_label.pack()

        progress_bar = ctk.CTkProgressBar(push_win, width=480)
        progress_bar.set(0)
        progress_bar.pack(pady=10)

        status_label = ctk.CTkLabel(
            push_win, text="準備檢查大檔與連線...", text_color="gray", font=("微軟正黑體", 12)
        )
        status_label.pack()

        def update_ui(text, pct):
            def _update():
                status_label.configure(text=text[:75] + "..." if len(text) > 75 else text)
                if pct is not None:
                    progress_bar.set(min(max(pct, 0), 100) / 100.0)
                    pct_label.configure(text=f"{int(pct)}%")

            self.root.after(0, _update)

        def _push_task():
            try:
                self.git_mgr.push_with_progress(update_ui)
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "上傳成功 🎉",
                        "已推送 Git 版本，並將 .dsproj 與 .dsproj_data 寫入同一個遠端資料夾。",
                        parent=push_win,
                    ),
                )
                self.root.after(0, push_win.destroy)
            except Exception as e:
                err = str(e)
                self.root.after(0, lambda: messagebox.showerror("上傳失敗", err, parent=push_win))
                self.root.after(0, push_win.destroy)

        threading.Thread(target=_push_task, daemon=True).start()

    def open_clone_dialog(self):
        clone_win = ctk.CTkToplevel(self.root)
        clone_win.title("📥 從遠端下載專案 (Clone)")
        clone_win.geometry("600x350")
        clone_win.grab_set()

        ctk.CTkLabel(
            clone_win,
            text="1. 輸入 GitHub 網址 或 內網共用資料夾（例如 \\\\伺服器\\共用\\NWT_TM）:",
            font=("微軟正黑體", 13, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(
            clone_win,
            text="內網只同步 .dsproj / .dsproj_data；會依目前版本新增「.1-Pull」版本，說明為 Pull from server。",
            font=("微軟正黑體", 11),
            text_color="gray",
        ).pack(anchor="w", padx=20, pady=(0, 5))
        url_entry = ctk.CTkEntry(clone_win, width=500)
        url_entry.pack(padx=20, anchor="w")

        ctk.CTkLabel(clone_win, text="2. 選擇儲存到本機的資料夾:", font=("微軟正黑體", 13, "bold")).pack(anchor="w", padx=20, pady=(15,5))
        path_frame = ctk.CTkFrame(clone_win, fg_color="transparent")
        path_frame.pack(fill="x", padx=20)
        dest_var = ctk.StringVar()
        ctk.CTkEntry(path_frame, textvariable=dest_var, width=400, state='readonly').pack(side="left")
        def browse_dest():
            folder = filedialog.askdirectory()
            if folder: dest_var.set(folder)
        ctk.CTkButton(path_frame, text="瀏覽", width=80, command=browse_dest).pack(side="left", padx=10)

        pct_label = ctk.CTkLabel(clone_win, text="0%", text_color="#3498DB", font=("Arial", 12, "bold"))
        progress_bar = ctk.CTkProgressBar(clone_win, width=500)
        progress_bar.set(0)
        status_label = ctk.CTkLabel(clone_win, text="等待開始...", text_color="gray", font=("微軟正黑體", 11))

        def start_clone():
            url = url_entry.get().strip()
            dest = dest_var.get().strip()
            if not url or not dest:
                return messagebox.showwarning("警告", "請填寫路徑與目標資料夾！", parent=clone_win)
            if not os.path.isdir(dest):
                try:
                    os.makedirs(dest, exist_ok=True)
                except Exception as e:
                    return messagebox.showerror("錯誤", f"無法使用本機資料夾：\n{e}", parent=clone_win)

            btn_start.configure(state="disabled")
            pct_label.pack(pady=(15,0))
            progress_bar.pack(pady=5)
            status_label.pack()

            threading.Thread(target=self._clone_thread_task, args=(url, dest, clone_win, btn_start, progress_bar, pct_label, status_label), daemon=True).start()

        btn_start = ctk.CTkButton(clone_win, text="🚀 開始下載", fg_color="#2B7A0B", hover_color="#1E5607", command=start_clone)
        btn_start.pack(pady=20)

    def _clone_thread_task(self, url, final_path, clone_win, btn_start, progress_bar, pct_label, status_label):
        def update_ui(text, pct):
            def _update():
                status_label.configure(text=text[:70] + "..." if len(text)>70 else text)
                if pct is not None:
                    progress_bar.set(pct / 100.0) 
                    pct_label.configure(text=f"{pct}%")
            self.root.after(0, _update)

        try:
            new_version = GitModelManager.clone_repo(url, final_path, update_ui)
            def _success():
                extra = f"\n\n新版本：{new_version}\n說明：Pull from server" if new_version else ""
                messagebox.showinfo(
                    "下載完成 🎉",
                    f"已同步執行檔至：\n{final_path}{extra}",
                    parent=clone_win,
                )
                clone_win.destroy()
                self.repo_path = final_path
                self.path_var.set(final_path)
                self.git_mgr = GitModelManager(final_path)
                self._post_load_project()
            self.root.after(0, _success)
        except Exception as e:
            err = str(e).strip() or repr(e)
            def _fail(msg=err):
                messagebox.showerror("下載失敗", msg, parent=clone_win)
                btn_start.configure(state="normal")
            self.root.after(0, _fail)

if __name__ == "__main__":
    root = ctk.CTk()
    app = D3DManagerApp(root)
    root.mainloop()
