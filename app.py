import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import glob
import threading

from core.git_control import GitModelManager
from core.d3d_parser import MduParser
from core.d3d_runner import run_delft3d

class D3DManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🌊 D-Flow FM 視窗版管理系統")
        self.root.geometry("850x700") 
        
        self.repo_path = ""
        self.mdu_files = []
        self.git_mgr = None
        self.mdu_data = None
        
        self.setup_ui()

    def setup_ui(self):
        frame_top = tk.Frame(self.root, padx=10, pady=10)
        frame_top.pack(fill=tk.X)
        tk.Label(frame_top, text="工作資料夾:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar()
        tk.Entry(frame_top, textvariable=self.path_var, width=45, state='readonly').pack(side=tk.LEFT, padx=5)
        tk.Button(frame_top, text="📂 瀏覽本機", command=self.load_project).pack(side=tk.LEFT)
        tk.Button(frame_top, text="📥 從雲端下載 (Clone)", command=self.open_clone_dialog, bg="#d9f2d9").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_top, text="狀態檢查", command=self.init_git).pack(side=tk.LEFT, padx=5)

        frame_history = tk.Frame(self.root, padx=10, pady=5, bg="#e6f2ff")
        frame_history.pack(fill=tk.X)
        
        history_top = tk.Frame(frame_history, bg="#e6f2ff")
        history_top.pack(fill=tk.X)
        tk.Label(history_top, text="⏳ 時光機 (切換版本):", bg="#e6f2ff", font=("微軟正黑體", 10, "bold")).pack(side=tk.LEFT)
        self.branch_combo = ttk.Combobox(history_top, state="readonly", width=30)
        self.branch_combo.pack(side=tk.LEFT, padx=5)
        self.branch_combo.bind("<<ComboboxSelected>>", self.on_branch_select)
        tk.Button(history_top, text="重新整理", command=self.refresh_branches).pack(side=tk.LEFT, padx=2)
        tk.Button(history_top, text="恢復至此版本", command=self.restore_version, bg="#ffcccc").pack(side=tk.LEFT, padx=10)

        history_bottom = tk.Frame(frame_history, bg="#e6f2ff")
        history_bottom.pack(fill=tk.X, pady=(5, 0))
        tk.Label(history_bottom, text="📝 版本說明:", bg="#e6f2ff", fg="gray").pack(side=tk.LEFT, anchor=tk.NW)
        self.branch_desc_var = tk.StringVar()
        self.branch_desc_var.set("請選擇版本以查看說明...")
        tk.Label(history_bottom, textvariable=self.branch_desc_var, bg="#e6f2ff", fg="blue", justify=tk.LEFT, wraplength=650).pack(side=tk.LEFT, padx=5, anchor=tk.NW)

        frame_mdu = tk.Frame(self.root, padx=10, pady=10)
        frame_mdu.pack(fill=tk.X)
        tk.Label(frame_mdu, text="選擇主控檔 (.mdu):").pack(side=tk.LEFT)
        self.mdu_combo = ttk.Combobox(frame_mdu, state="readonly", width=47)
        self.mdu_combo.pack(side=tk.LEFT, padx=5)
        self.mdu_combo.bind("<<ComboboxSelected>>", self.on_mdu_select)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)
        self.tab3 = ttk.Frame(self.notebook)
        self.tab4 = ttk.Frame(self.notebook)

        self.notebook.add(self.tab1, text='📸 模型建置快照')
        self.notebook.add(self.tab2, text='📝 情境參數設定')
        self.notebook.add(self.tab3, text='▶️ 執行模擬')
        self.notebook.add(self.tab4, text='☁️ GitHub 雲端備份')

        self.setup_tab4() # 先建立 Tab 4，確保 github_url 元件存在
        self.setup_tab1()
        self.setup_tab2()
        self.setup_tab3()

    def on_branch_select(self, event=None):
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
            
            # 🌟 新增：自動讀取並填入該專案已綁定的 GitHub 網址
            remote_url = self.git_mgr.get_remote_url()
            self.github_url.delete(0, tk.END)
            if remote_url:
                self.github_url.insert(0, remote_url)

            self.mdu_files = glob.glob(os.path.join(folder, "*.mdu")) + glob.glob(os.path.join(folder, "base_model", "*.mdu"))
            if self.mdu_files:
                self.mdu_combo['values'] = self.mdu_files
                self.mdu_combo.current(0)
                self.on_mdu_select(None)
            else:
                self.mdu_combo['values'] = []
                self.mdu_combo.set('')

    def refresh_branches(self):
        if self.git_mgr:
            branches = self.git_mgr.get_all_branches()
            self.branch_combo['values'] = branches
            if branches:
                self.branch_combo.current(0)
                self.on_branch_select()

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

    def on_mdu_select(self, event):
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

    def setup_tab1(self):
        tk.Label(self.tab1, text="建置標籤 (例如 v1.0-base):").pack(anchor=tk.W, pady=5)
        self.build_ver = tk.Entry(self.tab1, width=30)
        self.build_ver.pack(anchor=tk.W)
        tk.Label(self.tab1, text="建置內容說明:").pack(anchor=tk.W, pady=5)
        self.build_desc = tk.Text(self.tab1, height=5, width=50)
        self.build_desc.pack(anchor=tk.W)
        tk.Button(self.tab1, text="💾 儲存建置進度", command=self.save_snapshot).pack(anchor=tk.W, pady=10)

    def save_snapshot(self):
        if not self.git_mgr: return
        try:
            self.git_mgr.create_scenario_branch(f"build/{self.build_ver.get()}")
            msg = self.git_mgr.commit_scenario_changes(self.build_desc.get("1.0", tk.END).strip())
            messagebox.showinfo("儲存狀態", f"操作完成！\n{msg}")
            self.refresh_branches() 
        except Exception as e:
            messagebox.showerror("錯誤", str(e))

    def setup_tab2(self):
        tk.Label(self.tab2, text="情境名稱:").pack(anchor=tk.W, pady=5)
        self.scen_name = tk.Entry(self.tab2, width=30)
        self.scen_name.pack(anchor=tk.W)
        tk.Label(self.tab2, text="情境內容說明:").pack(anchor=tk.W, pady=5)
        self.scen_desc = tk.Text(self.tab2, height=4, width=50)
        self.scen_desc.insert(tk.END, "測試新邊界條件與時間")
        self.scen_desc.pack(anchor=tk.W)
        tk.Label(self.tab2, text="模擬時間 Tstop (秒):").pack(anchor=tk.W, pady=5)
        self.tstop_var = tk.StringVar()
        tk.Entry(self.tab2, textvariable=self.tstop_var, width=30).pack(anchor=tk.W)
        tk.Button(self.tab2, text="💾 生成情境分支並修改 MDU", command=self.save_scenario).pack(anchor=tk.W, pady=10)

    def save_scenario(self):
        if not self.git_mgr or not self.mdu_data: return
        try:
            self.git_mgr.create_scenario_branch(f"scenario/{self.scen_name.get()}")
            if 'time' not in self.mdu_data:
                self.mdu_data.add_section('time')
            self.mdu_data['time']['Tstop'] = self.tstop_var.get()
            MduParser.write_mdu(self.mdu_data, self.mdu_combo.get())
            user_desc = self.scen_desc.get("1.0", tk.END).strip()
            msg = self.git_mgr.commit_scenario_changes(user_desc)
            messagebox.showinfo("成功", f"情境 {self.scen_name.get()} 已更新！\n{msg}")
            self.refresh_branches()
        except Exception as e:
            messagebox.showerror("錯誤", str(e))

    def setup_tab3(self):
        tk.Label(self.tab3, text="d_hydro.exe 絕對路徑:").pack(anchor=tk.W, pady=5)
        self.exe_path = tk.Entry(self.tab3, width=80)
        self.exe_path.insert(0, r"C:\Program Files\Deltares\Delft3D FM Suite 2023.01\x64\dflow2d3d\bin\d_hydro.exe")
        self.exe_path.pack(anchor=tk.W)
        tk.Button(self.tab3, text="🔥 開始執行模擬", command=self.run_simulation).pack(anchor=tk.W, pady=10)
        self.log_text = tk.Text(self.tab3, height=15, bg="black", fg="white")
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def run_simulation(self):
        mdu_path = self.mdu_combo.get()
        exe = self.exe_path.get()
        if not mdu_path or not os.path.exists(exe): return
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "模式啟動中...\n")
        threading.Thread(target=self._run_process_thread, args=(mdu_path, exe), daemon=True).start()

    def _run_process_thread(self, mdu_path, exe):
        try:
            proc = run_delft3d(mdu_path, exe)
            while True:
                output = proc.stdout.readline()
                if output == '' and proc.poll() is not None: break
                if output:
                    self.log_text.insert(tk.END, output)
                    self.log_text.see(tk.END) 
            if proc.poll() == 0:
                messagebox.showinfo("完成", "模擬順利完成！")
            else:
                messagebox.showerror("錯誤", f"異常終止，代碼: {proc.poll()}")
        except Exception as e:
            messagebox.showerror("執行錯誤", str(e))

    def setup_tab4(self):
        tk.Label(self.tab4, text="1. 輸入您的 GitHub 儲存庫網址 (HTTPS 格式):").pack(anchor=tk.W, pady=5)
        self.github_url = tk.Entry(self.tab4, width=60)
        self.github_url.pack(anchor=tk.W)
        tk.Button(self.tab4, text="🔗 綁定 GitHub", command=self.bind_github).pack(anchor=tk.W, pady=5)
        
        tk.Label(self.tab4, text="2. 將本機所有的版本與設定推送到雲端:").pack(anchor=tk.W, pady=(20, 5))
        tk.Button(self.tab4, text="🚀 開始上傳備份至 GitHub", command=self.open_push_dialog, bg="#cceeff", font=("微軟正黑體", 10, "bold")).pack(anchor=tk.W)
        tk.Label(self.tab4, text="💡 提示：如果檔案包含大型 LFS 網格檔，上傳可能需要幾分鐘，請耐心等待。", fg="gray").pack(anchor=tk.W, pady=10)

    def bind_github(self):
        if not self.git_mgr: return
        url = self.github_url.get().strip()
        if not url: return messagebox.showwarning("警告", "請先貼上 GitHub 網址！")
        try: messagebox.showinfo("成功", self.git_mgr.set_remote_url(url))
        except Exception as e: messagebox.showerror("錯誤", str(e))

    def open_push_dialog(self):
        if not self.git_mgr: return
        
        push_win = tk.Toplevel(self.root)
        push_win.title("🚀 雲端上傳作業中")
        push_win.geometry("500x200")
        push_win.grab_set() 

        tk.Label(push_win, text="正在將專案與大型 LFS 檔案上傳至 GitHub，請稍候...", font=("微軟正黑體", 11, "bold")).pack(pady=(20,10))
        
        progress_var = tk.DoubleVar()
        pct_label = tk.Label(push_win, text="0%", fg="blue", font=("Arial", 11, "bold"))
        pct_label.pack()

        progress_bar = ttk.Progressbar(push_win, variable=progress_var, maximum=100, length=400)
        progress_bar.pack(pady=10)

        status_label = tk.Label(push_win, text="準備連線並計算差異...", fg="gray", font=("微軟正黑體", 9))
        status_label.pack()

        def update_ui(text, pct):
            def _update():
                display_text = text[:70] + "..." if len(text) > 70 else text
                status_label.config(text=display_text)
                if pct is not None:
                    progress_var.set(pct)
                    pct_label.config(text=f"{pct}%")
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

    def open_clone_dialog(self):
        clone_win = tk.Toplevel(self.root)
        clone_win.title("📥 從 GitHub 下載專案 (Clone)")
        clone_win.geometry("500x300")
        clone_win.grab_set() 

        tk.Label(clone_win, text="1. 輸入 GitHub 網址 (.git 結尾):", font=("微軟正黑體", 10, "bold")).pack(anchor=tk.W, padx=20, pady=(20,5))
        url_entry = tk.Entry(clone_win, width=55)
        url_entry.pack(padx=20)

        tk.Label(clone_win, text="2. 選擇儲存到本機的父資料夾:", font=("微軟正黑體", 10, "bold")).pack(anchor=tk.W, padx=20, pady=(15,5))
        path_frame = tk.Frame(clone_win)
        path_frame.pack(fill=tk.X, padx=20)
        dest_var = tk.StringVar()
        tk.Entry(path_frame, textvariable=dest_var, width=45, state='readonly').pack(side=tk.LEFT)
        def browse_dest():
            folder = filedialog.askdirectory()
            if folder: dest_var.set(folder)
        tk.Button(path_frame, text="瀏覽", command=browse_dest).pack(side=tk.LEFT, padx=5)

        progress_var = tk.DoubleVar()
        pct_label = tk.Label(clone_win, text="0%", fg="blue", font=("Arial", 10, "bold"))
        progress_bar = ttk.Progressbar(clone_win, variable=progress_var, maximum=100, length=400)
        status_label = tk.Label(clone_win, text="等待開始...", fg="gray", font=("微軟正黑體", 9))

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

            btn_start.config(state=tk.DISABLED)
            pct_label.pack(pady=(10,0))
            progress_bar.pack(pady=5)
            status_label.pack()

            threading.Thread(target=self._clone_thread_task, args=(url, final_path, clone_win, btn_start, progress_var, pct_label, status_label), daemon=True).start()

        btn_start = tk.Button(clone_win, text="🚀 開始下載", command=start_clone, bg="#cceeff")
        btn_start.pack(pady=20)

    def _clone_thread_task(self, url, final_path, clone_win, btn_start, progress_var, pct_label, status_label):
        def update_ui(text, pct):
            def _update():
                status_label.config(text=text[:70] + "..." if len(text)>70 else text)
                if pct is not None:
                    progress_var.set(pct)
                    pct_label.config(text=f"{pct}%")
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
                
                # 🌟 新增：下載完成後，自動把剛剛下載的網址填入備份頁籤
                remote_url = self.git_mgr.get_remote_url()
                self.github_url.delete(0, tk.END)
                if remote_url:
                    self.github_url.insert(0, remote_url)

                self.mdu_files = glob.glob(os.path.join(final_path, "*.mdu")) + glob.glob(os.path.join(final_path, "base_model", "*.mdu"))
                if self.mdu_files:
                    self.mdu_combo['values'] = self.mdu_files
                    self.mdu_combo.current(0)
                    self.on_mdu_select(None)
            self.root.after(0, _success)
        except Exception as e:
            def _fail():
                messagebox.showerror("下載失敗", str(e), parent=clone_win)
                btn_start.config(state=tk.NORMAL)
            self.root.after(0, _fail)

if __name__ == "__main__":
    root = tk.Tk()
    app = D3DManagerApp(root)
    root.mainloop()