import subprocess
import os
import re

class GitModelManager:
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.auto_init()

    def create_lfs_and_ignore_rules(self):
        gitignore_path = os.path.join(self.repo_path, ".gitignore")
        if not os.path.exists(gitignore_path):
            ignore_content = """# D-Flow FM 專案自動生成之 Git 排除規則
# ⛔ 排除模擬產生的巨大結果檔 (Outputs)
*_map.nc
*_his.nc
*_rst.nc
*_runtimings.nc
*_waq.nc
*.dia
*.log
*.bak
*.tmp
*.err
"""
            try:
                with open(gitignore_path, "w", encoding="utf-8") as f:
                    f.write(ignore_content)
            except Exception: pass

        gitattr_path = os.path.join(self.repo_path, ".gitattributes")
        if not os.path.exists(gitattr_path):
            attr_content = """# 啟用 Git LFS 來接管超過 100MB 的核心輸入檔 (Inputs)
*.xyz filter=lfs diff=lfs merge=lfs -text
*.pol filter=lfs diff=lfs merge=lfs -text
*_net.nc filter=lfs diff=lfs merge=lfs -text
*.grd filter=lfs diff=lfs merge=lfs -text
*.dep filter=lfs diff=lfs merge=lfs -text
"""
            try:
                with open(gitattr_path, "w", encoding="utf-8") as f:
                    f.write(attr_content)
            except Exception: pass

    def auto_init(self):
        if not os.path.exists(self.repo_path): return
        self.create_lfs_and_ignore_rules()
        if not os.path.exists(os.path.join(self.repo_path, ".git")):
            self._run_git(["init"])
            try:
                self._run_git(["lfs", "install"])
            except Exception: pass
            
        check_status = subprocess.run("git status --porcelain", cwd=self.repo_path, capture_output=True, text=True, shell=True)
        if check_status.stdout.strip():
            self._run_git(["add", "."])
            try: self._run_git(["commit", "-m", "Auto Initial commit: Base Model with LFS"])
            except Exception: pass 
            try: self._run_git(["branch", "-M", "main"])
            except Exception: pass

    def _run_git(self, args):
        command_str = subprocess.list2cmdline(["git"] + args)
        try:
            result = subprocess.run(
                command_str, 
                cwd=self.repo_path, 
                capture_output=True, 
                text=True, 
                encoding="utf-8",
                errors="replace",
                shell=True
            )
            if result.returncode != 0:
                error_detail = result.stderr.strip() or result.stdout.strip()
                if "nothing to commit" in error_detail.lower() or "working tree clean" in error_detail.lower():
                    return "目前檔案沒有變動，無需重複儲存。"
                raise Exception(f"\n[執行指令]: {command_str}\n[詳細原因]: {error_detail}")
            return result.stdout.strip()
        except Exception as e:
            raise Exception(f"無法順利呼叫 Git！\n系統訊息: {str(e)}")

    def init_repo(self):
        self.auto_init()
        return "✅ LFS 大型檔案追蹤已啟動，Git 儲存庫已處於安全狀態！"

    def get_all_branches(self):
        try:
            result = subprocess.run("git branch", cwd=self.repo_path, capture_output=True, text=True, shell=True)
            if result.returncode != 0: return ["main"]
            branches = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    clean_name = line.replace('*', '').strip()
                    branches.append(clean_name)
            return branches
        except Exception: return ["main"]

    def get_branch_info(self, branch_name):
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%B", branch_name], 
                cwd=self.repo_path, capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return "無說明紀錄"
        except Exception: return "無法取得說明"

    def switch_branch(self, branch_name):
        try: self._run_git(["stash"])
        except Exception: pass
        self._run_git(["checkout", branch_name])
        return f"🔄 已成功將專案資料夾恢復至 `{branch_name}` 版本的狀態！"

    def create_scenario_branch(self, branch_name):
        branches = self.get_all_branches()
        if branch_name in branches:
            self._run_git(["checkout", branch_name])
            return f"👉 已切換至現有情境: {branch_name}"
        else:
            self._run_git(["checkout", "-b", branch_name])
            return f"✨ 已建立並切換至新情境: {branch_name}"

    def commit_scenario_changes(self, description):
        self._run_git(["add", "."])
        self._run_git(["commit", "--allow-empty", "-m", description])
        return f"已成功將進度與說明寫入版本庫！"
        
    def set_remote_url(self, github_url):
        check = subprocess.run("git remote", cwd=self.repo_path, capture_output=True, text=True, shell=True)
        if "origin" in check.stdout:
            self._run_git(["remote", "set-url", "origin", github_url])
            return "✅ 已更新 GitHub 遠端連結"
        else:
            self._run_git(["remote", "add", "origin", github_url])
            return "✅ 已綁定新的 GitHub 遠端連結"

    # 🌟 新增：自動讀取本機紀錄的 GitHub 網址
    def get_remote_url(self):
        """取得目前綁定的 GitHub 遠端網址"""
        try:
            result = subprocess.run(
                "git config --get remote.origin.url", 
                cwd=self.repo_path, capture_output=True, text=True, shell=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return ""
        except Exception: 
            return ""

    def push_with_progress(self, progress_callback):
        command = ["git", "push", "-u", "origin", "--all", "-f", "--progress"]
        try:
            process = subprocess.Popen(
                command,
                cwd=self.repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, 
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            buffer = ""
            while True:
                char = process.stdout.read(1)
                if not char and process.poll() is not None:
                    break
                if char in ('\r', '\n'):
                    if buffer.strip():
                        text = buffer.strip()
                        match = re.search(r'(\d+)%', text)
                        pct = int(match.group(1)) if match else None
                        progress_callback(text, pct)
                        buffer = ""
                else:
                    buffer += char
                    
            process.wait()
            if process.returncode != 0:
                raise Exception(f"上傳失敗，Git 返回代碼: {process.returncode}")
        except Exception as e:
            raise Exception(f"執行上傳時發生錯誤:\n{str(e)}")

    @staticmethod
    def clone_repo(url, target_path, progress_callback):
        command = ["git", "clone", "--progress", url, target_path]
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            buffer = ""
            while True:
                char = process.stdout.read(1)
                if not char and process.poll() is not None:
                    break
                if char in ('\r', '\n'):
                    if buffer.strip():
                        text = buffer.strip()
                        match = re.search(r'(\d+)%', text)
                        pct = int(match.group(1)) if match else None
                        progress_callback(text, pct)
                        buffer = ""
                else:
                    buffer += char
                    
            process.wait()
            if process.returncode != 0:
                raise Exception(f"Clone 失敗，代碼: {process.returncode}")
        except Exception as e:
            raise Exception(f"執行 Clone 時發生錯誤:\n{str(e)}")