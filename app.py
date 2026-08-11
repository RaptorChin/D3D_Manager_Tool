import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import glob
import threading
import re

# 匯入核心模組
from core.git_control import GitModelManager
from core.d3d_parser import MduParser
from core.d3d_runner import run_delft3d

# 設定 CustomTkinter 的外觀風格與主題
ctk.set_appearance_mode("System")  # 支援 "System" (隨系統切換), "Dark", "Light"
ctk.set_default_color_theme("blue")  # 支援 "blue", "green", "dark-blue"

class D3DManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🌊 D-Flow FM 視窗版管理系統 (現代化介面)")
        self.root.geometry("950x800")
        
        self.repo_path = ""
        self.mdu_files = []
        self.git_mgr = None
        self.mdu_data = None
        
        self.setup_ui()

    def setup_ui(self):
        # 定義統一的字體
        font_title = ctk.CTkFont(family="微軟正黑體", size=14, weight="bold")
        font_normal = ctk.CTkFont(family="微軟正黑體", size=13)
        font_code = ctk.CTkFont(family="Consolas", size=12)

        # --- 頂部：工作區選擇 ---
        frame_top = ctk.CTkFrame(self.root, corner_radius=10)
        frame_top.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(frame_top, text="工作資料夾:", font=font_title).pack(side="left", padx=10, pady=10)
        
        self.path_var = ctk.StringVar()
        ctk.CTkEntry(frame_top, textvariable=self.path_var, width=350, font=font_normal, state="readonly").pack(side="left", padx=5)
        
        ctk.CTkButton(frame_top, text="📂 瀏覽本機", font=font_normal, command=self.load_project, width=100).pack(side="left", padx=5)
        ctk.CTkButton(frame_top, text="📥 從雲端下載 (Clone)", font=font_normal, fg_color="#2B7A0B", hover_color="#1E5607", command=self.open_clone_dialog, width=150).pack(side="left", padx=5)
        ctk.CTkButton(frame_top, text="狀態檢查", font=font_normal, fg_color="#5A5A5A", hover_color="#404040", command=self.init_git, width=100).pack(side="left", padx=5)

        # --- 🌟 時光機區塊 ---
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

        # --- MDU 檔案選擇 ---
        frame_mdu = ctk.CTkFrame(self.root, corner_radius=10)
        frame_mdu.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(frame_mdu, text="選擇主控檔 (.mdu):", font=font_title).pack(side="left", padx=10, pady=10)
        self.mdu_combo = ctk.CTkComboBox(frame_mdu, width=400, font=font_normal, command=self.on_mdu_select)
        self.mdu_combo.pack(side="left", padx=5)

        # --- 現代化分頁設定 (Tabview) ---
        self.tabview = ctk.CTkTabview(self.root, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.tab1 = self.tabview.add('📸 模型建置快照')
        self.tab2 = self.tabview.add('📝 情境參數設定')
        self.tab3 = self.tabview.add('▶️ 執行模擬')
        self.tab4 = self.tabview.add('☁️ GitHub 雲端備份')

        self.setup_tab1(font_title, font_normal)
        self.setup_tab2(font_title, font_normal)
        self.setup_tab3(font_title, font_normal, font_code)
        self.setup_tab4(font_title, font_normal)

    def on_branch_select(self, choice=None):
        if not self.git_mgr: return
        selected = self.branch_combo.get()
        if selected:
            desc = self.git_mgr.get_branch_info(selected)
            self.branch_desc_var.set(desc)

    def load_project(self):
        folder = filedialog.askdirectory()
        if folder:
            self.repo_path = folder
            self.path_var.set(folder)
            self.git_mgr = GitModelManager(folder)
            self.refresh_branches()
            
            # 自動讀取並填入該專案已綁定的 GitHub 網址
            remote_url = self.git_mgr.get_remote_url()
            self.github_url.delete(0, "end")
            if remote_url:
                self.github_url.insert(0, remote_url)

            self.mdu_files = glob.glob(os.path.join(folder, "*.mdu")) + glob.glob(os.path.join(folder, "base_model", "*.mdu"))
            if self.mdu_files:
                self.mdu_combo.configure(values=self.mdu_files)
                self.mdu_combo.set(self.mdu_files[0])
                self.on_mdu_select(self.mdu_files[0])
            else:
                self.mdu_combo.configure(values=[])
                self.mdu_combo.set('')

    def refresh_branches(self):
        if self.git_mgr:
            branches = self.git_mgr.get_all_branches()
            self.branch_combo.configure(values=branches)
            if branches:
                self.branch_combo.set(branches[0])
                self.on_branch_select(branches[0])

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
        ctk.CTkLabel(self.tab4, text="1. 輸入您的 GitHub 儲存庫網址 (HTTPS 格式):", font=font_title).pack(anchor="w", padx=20, pady=(20, 5))
        self.github_url = ctk.CTkEntry(self.tab4, width=500, font=font_normal)
        self.github_url.pack(anchor="w", padx=20)
        ctk.CTkButton(self.tab4, text="🔗 綁定 GitHub", font=font_normal, command=self.bind_github).pack(anchor="w", padx=20, pady=10)
        
        ctk.CTkLabel(self.tab4, text="2. 將本機所有的版本與設定推送到雲端:", font=font_title).pack(anchor="w", padx=20, pady=(30, 5))
        ctk.CTkButton(self.tab4, text="🚀 開始上傳備份至 GitHub", font=font_title, fg_color="#2B7A0B", hover_color="#1E5607", command=self.open_push_dialog).pack(anchor="w", padx=20)
        ctk.CTkLabel(self.tab4, text="💡 提示：如果檔案包含大型 LFS 網格檔，上傳可能需要幾分鐘，請耐心等待。", font=font_normal, text_color="gray").pack(anchor="w", padx=20, pady=10)

    def bind_github(self):
        if not self.git_mgr: return
        url = self.github_url.get().strip()
        if not url: return messagebox.showwarning("警告", "請先貼上 GitHub 網址！")
        try: messagebox.showinfo("成功", self.git_mgr.set_remote_url(url))
        except Exception as e: messagebox.showerror("錯誤", str(e))

    # --- 彈出式進度條視窗 (Push) ---
    def open_push_dialog(self):
        if not self.git_mgr: return
        
        push_win = ctk.CTkToplevel(self.root)
        push_win.title("🚀 雲端上傳作業中")
        push_win.geometry("550x220")
        push_win.grab_set() 

        ctk.CTkLabel(push_win, text="正在將專案與大型 LFS 檔案上傳至 GitHub，請稍候...", font=("微軟正黑體", 14, "bold")).pack(pady=(20,10))
        
        pct_label = ctk.CTkLabel(push_win, text="0%", text_color="#3498DB", font=("Arial", 14, "bold"))
        pct_label.pack()

        progress_bar = ctk.CTkProgressBar(push_win, width=450)
        progress_bar.set(0)
        progress_bar.pack(pady=10)

        status_label = ctk.CTkLabel(push_win, text="準備連線並計算差異...", text_color="gray", font=("微軟正黑體", 12))
        status_label.pack()

        def update_ui(text, pct):
            def _update():
                display_text = text[:70] + "..." if len(text) > 70 else text
                status_label.configure(text=display_text)
                if pct is not None:
                    progress_bar.set(pct / 100.0) # CustomTkinter bar is 0.0 to 1.0
                    pct_label.configure(text=f"{pct}%")
            self.root.after(0, _update)

        def _push_task():
            try:
                self.git_mgr.push_with_progress(update_ui)
                def _success():
                    messagebox.showinfo("上傳成功 🎉", "所有模式版本、情境與大型地形網格檔均已成功備份至 GitHub！", parent=push_win)
                    push_win.destroy()
                self.root.after(0, _success)
            except Exception as e:
                def _fail():
                    messagebox.showerror("上傳失敗", str(e), parent=push_win)
                    push_win.destroy()
                self.root.after(0, _fail)

        threading.Thread(target=_push_task, daemon=True).start()

    # --- 彈出式進度條視窗 (Clone) ---
    def open_clone_dialog(self):
        clone_win = ctk.CTkToplevel(self.root)
        clone_win.title("📥 從 GitHub 下載專案 (Clone)")
        clone_win.geometry("600x350")
        clone_win.grab_set() 

        ctk.CTkLabel(clone_win, text="1. 輸入 GitHub 網址 (.git 結尾):", font=("微軟正黑體", 13, "bold")).pack(anchor="w", padx=20, pady=(20,5))
        url_entry = ctk.CTkEntry(clone_win, width=500)
        url_entry.pack(padx=20, anchor="w")

        ctk.CTkLabel(clone_win, text="2. 選擇儲存到本機的父資料夾:", font=("微軟正黑體", 13, "bold")).pack(anchor="w", padx=20, pady=(15,5))
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
                messagebox.showwarning("警告", "請填寫網址與目標資料夾！", parent=clone_win)
                return
            repo_name = url.split("/")[-1].replace(".git", "")
            final_path = os.path.join(dest, repo_name)
            if os.path.exists(final_path):
                messagebox.showerror("錯誤", f"資料夾 '{repo_name}' 已經存在！請選擇其他空目錄。", parent=clone_win)
                return

            btn_start.configure(state="disabled")
            pct_label.pack(pady=(15,0))
            progress_bar.pack(pady=5)
            status_label.pack()

            threading.Thread(target=self._clone_thread_task, args=(url, final_path, clone_win, btn_start, progress_bar, pct_label, status_label), daemon=True).start()

        btn_start = ctk.CTkButton(clone_win, text="🚀 開始下載", fg_color="#2B7A0B", hover_color="#1E5607", command=start_clone)
        btn_start.pack(pady=20)

    def _clone_thread_task(self, url, final_path, clone_win, btn_start, progress_bar, pct_label, status_label):
        def update_ui(text, pct):
            def _update():
                status_label.configure(text=text[:70] + "..." if len(text)>70 else text)
                if pct is not None:
                    progress_bar.set(pct / 100.0) # CustomTkinter bar is 0.0 to 1.0
                    pct_label.configure(text=f"{pct}%")
            self.root.after(0, _update)

        try:
            GitModelManager.clone_repo(url, final_path, update_ui)
            def _success():
                messagebox.showinfo("下載完成 🎉", f"專案已成功下載至：\n{final_path}", parent=clone_win)
                clone_win.destroy()
                self.repo_path = final_path
                self.path_var.set(final_path)
                self.git_mgr = GitModelManager(final_path)
                self.refresh_branches()
                
                remote_url = self.git_mgr.get_remote_url()
                self.github_url.delete(0, "end")
                if remote_url:
                    self.github_url.insert(0, remote_url)

                self.mdu_files = glob.glob(os.path.join(final_path, "*.mdu")) + glob.glob(os.path.join(final_path, "base_model", "*.mdu"))
                if self.mdu_files:
                    self.mdu_combo.configure(values=self.mdu_files)
                    self.mdu_combo.set(self.mdu_files[0])
                    self.on_mdu_select(None)
            self.root.after(0, _success)
        except Exception as e:
            def _fail():
                messagebox.showerror("下載失敗", str(e), parent=clone_win)
                btn_start.configure(state="normal")
            self.root.after(0, _fail)

if __name__ == "__main__":
    root = ctk.CTk()
    app = D3DManagerApp(root)
    root.mainloop()