import subprocess
import os
import re
import shutil
from datetime import datetime

# GitHub / 多數遠端的硬性上限約 100MB；超過此值且未走 LFS 會被拒絕
LARGE_FILE_SOFT_MB = 50
LARGE_FILE_HARD_MB = 90


class GitModelManager:
    def __init__(self, repo_path):
        self.repo_path = repo_path

    @staticmethod
    def _no_window_flags():
        return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    @staticmethod
    def get_global_user_identity():
        """讀取全域 Git 使用者名稱與信箱，回傳 (name, email)。"""
        name, email = "", ""
        flags = GitModelManager._no_window_flags()
        try:
            r = subprocess.run(
                ["git", "config", "--global", "--get", "user.name"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=flags,
            )
            if r.returncode == 0:
                name = (r.stdout or "").strip()
        except Exception:
            pass
        try:
            r = subprocess.run(
                ["git", "config", "--global", "--get", "user.email"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=flags,
            )
            if r.returncode == 0:
                email = (r.stdout or "").strip()
        except Exception:
            pass
        return name, email

    @staticmethod
    def is_global_user_configured():
        """全域 user.name 與 user.email 是否皆已設定。"""
        name, email = GitModelManager.get_global_user_identity()
        return bool(name) and bool(email)

    @staticmethod
    def set_global_user_identity(name, email):
        """寫入全域 Git 使用者名稱與信箱。"""
        name = (name or "").strip()
        email = (email or "").strip()
        if not name or not email:
            raise Exception("使用者名稱與信箱皆不可空白。")
        flags = GitModelManager._no_window_flags()
        for key, value in (("user.name", name), ("user.email", email)):
            result = subprocess.run(
                ["git", "config", "--global", key, value],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=flags,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip()
                raise Exception(f"無法設定 {key}：\n{detail or '(無 Git 輸出)'}")
        return f"已設定全域身分：{name} <{email}>"

    def is_initialized(self):
        """檢查資料夾是否已經建立過 Git 版本控制"""
        return os.path.exists(os.path.join(self.repo_path, ".git"))

    def has_uncommitted_changes(self):
        """檢查資料夾內是否有未存檔的變更"""
        try:
            check = subprocess.run(
                "git status --porcelain",
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                shell=True,
            )
            return bool(check.stdout.strip())
        except Exception:
            return False

    def do_initial_setup(self, update_callback):
        """首次初始化：先寫入忽略/LFS 規則，再加入檔案，避免大檔直接進一般 Git"""
        update_callback("正在建立設定檔 (.gitignore / .gitattributes)...", 10)
        self.create_lfs_and_ignore_rules()

        update_callback("正在初始化 Git 儲存庫...", 20)
        self._run_git(["init"])

        update_callback("正在設定 LFS 大型檔案追蹤...", 30)
        self._ensure_lfs_installed()

        update_callback("正在掃描大型檔案並套用 LFS...", 40)
        self._auto_track_oversized_files()

        update_callback("正在加入 .dsproj 與 .dsproj_data（僅執行所需檔案）...", 55)
        self._stage_dsproj_only()

        update_callback("正在建立初始快照...", 85)
        try:
            self._run_git(["commit", "-m", "Auto Initial commit: Cleaned & Slim Model"])
        except Exception:
            pass

        try:
            self._run_git(["branch", "-M", "main"])
        except Exception:
            pass
        update_callback("初始化完成！", 100)

    def do_auto_commit(self, update_callback):
        """載入前自動儲存未提交變更"""
        update_callback("正在更新 LFS / 忽略規則...", 15)
        self.create_lfs_and_ignore_rules()
        self._ensure_lfs_installed()

        update_callback("正在掃描大型檔案並套用 LFS...", 30)
        self._auto_track_oversized_files()

        update_callback("正在掃描 .dsproj / .dsproj_data 變更...", 50)
        self._stage_dsproj_only()

        update_callback("正在建立版本快照...", 80)
        try:
            self._run_git(["commit", "-m", "Auto Save: 載入前自動儲存未提交之變更"])
        except Exception:
            pass

        update_callback("儲存完成！", 100)

    def create_lfs_and_ignore_rules(self):
        gitignore_path = os.path.join(self.repo_path, ".gitignore")
        ignore_content = """# 只版本控制 Delft3D Delta Shell 執行所需檔案
# 忽略其餘所有檔案（含獨立 .mdu、output、快取等）
*
!*/
!.gitignore
!.gitattributes

# ✅ 專案檔
!*.dsproj
!**/*.dsproj

# ✅ 專案資料夾（執行所需輸入皆在此）
!*.dsproj_data/
!*.dsproj_data/**
!**/*.dsproj_data/
!**/*.dsproj_data/**
"""
        try:
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write(ignore_content)
        except Exception:
            pass

        gitattr_path = os.path.join(self.repo_path, ".gitattributes")
        attr_content = """# 以 Git LFS 接管 Delft3D 常見大型輸入檔，避免超過遠端檔案大小限制
*.xyz filter=lfs diff=lfs merge=lfs -text
*.pol filter=lfs diff=lfs merge=lfs -text
*.pli filter=lfs diff=lfs merge=lfs -text
*.pliz filter=lfs diff=lfs merge=lfs -text
*.bc filter=lfs diff=lfs merge=lfs -text
*.bct filter=lfs diff=lfs merge=lfs -text
*.tim filter=lfs diff=lfs merge=lfs -text
*_net.nc filter=lfs diff=lfs merge=lfs -text
*_ini.nc filter=lfs diff=lfs merge=lfs -text
*.grd filter=lfs diff=lfs merge=lfs -text
*.dep filter=lfs diff=lfs merge=lfs -text
*.enc filter=lfs diff=lfs merge=lfs -text
*.asc filter=lfs diff=lfs merge=lfs -text
*.tif filter=lfs diff=lfs merge=lfs -text
*.tiff filter=lfs diff=lfs merge=lfs -text
*.sqlite filter=lfs diff=lfs merge=lfs -text
"""
        try:
            with open(gitattr_path, "w", encoding="utf-8") as f:
                f.write(attr_content)
        except Exception:
            pass

    @staticmethod
    def _is_dsproj_rel(rel_path):
        """是否為 Delta Shell 執行所需路徑（.dsproj 或 .dsproj_data 內）"""
        rel = (rel_path or "").replace("\\", "/").lstrip("./")
        if rel in (".gitignore", ".gitattributes"):
            return True
        name = os.path.basename(rel)
        if name.endswith(".dsproj") and not name.endswith(".dsproj_data"):
            return True
        return any(part.endswith(".dsproj_data") for part in rel.split("/"))

    def _find_dsproj_items(self):
        """找出本機 .dsproj 檔與 .dsproj_data 資料夾（相對路徑）"""
        items = []
        for root_dir, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d != ".git" and not d.startswith(".")]
            rel_root = os.path.relpath(root_dir, self.repo_path)
            for d in list(dirs):
                if d.endswith(".dsproj_data"):
                    rel = d if rel_root == "." else os.path.join(rel_root, d)
                    items.append(rel.replace("\\", "/"))
            for name in files:
                if name.endswith(".dsproj") and not name.endswith(".dsproj_data"):
                    rel = name if rel_root == "." else os.path.join(rel_root, name)
                    items.append(rel.replace("\\", "/"))
        return items

    def _stage_dsproj_only(self):
        """只把 .dsproj / .dsproj_data 納入 Git，並取消追蹤其餘檔案"""
        tracked = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=self.repo_path,
            capture_output=True,
        )
        extra = []
        if tracked.returncode == 0:
            for raw in tracked.stdout.split(b"\0"):
                if not raw:
                    continue
                rel = raw.decode("utf-8", errors="replace").replace("\\", "/")
                if not self._is_dsproj_rel(rel):
                    extra.append(rel)
        for i in range(0, len(extra), 40):
            chunk = extra[i : i + 40]
            subprocess.run(
                ["git", "rm", "-r", "--cached", "--ignore-unmatch", "--"] + chunk,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

        to_add = [".gitignore", ".gitattributes"] + self._find_dsproj_items()
        existing = [p for p in to_add if os.path.exists(os.path.join(self.repo_path, p.replace("/", os.sep)))]
        if not any(self._is_dsproj_rel(p) and p not in (".gitignore", ".gitattributes") for p in existing):
            raise Exception(
                "工作資料夾內找不到 .dsproj 或 .dsproj_data。\n"
                "請確認已開啟 Delta Shell 專案根目錄後再儲存／推送。"
            )
        for i in range(0, len(existing), 40):
            self._run_git(["add", "--"] + existing[i : i + 40])

    def init_repo(self):
        if not self.is_initialized():
            self._run_git(["init"])
            self.create_lfs_and_ignore_rules()
            self._ensure_lfs_installed()
            return "✅ 已初始化 Git，並啟用 LFS 大型檔案追蹤。"
        self.create_lfs_and_ignore_rules()
        self._ensure_lfs_installed()
        return "✅ 狀態檢查完畢：Git 儲存庫安全，LFS 規則已更新。"

    def _ensure_lfs_installed(self):
        if not shutil.which("git-lfs") and not self._lfs_available():
            raise Exception(
                "本機未安裝 Git LFS。\n"
                "Delft3D 網格/地形檔常超過 100MB，沒有 LFS 會無法推送到遠端。\n"
                "請先安裝：https://git-lfs.com/ 或執行 `git lfs install` 所屬套件。"
            )
        try:
            self._run_git(["lfs", "install", "--local"])
        except Exception:
            try:
                self._run_git(["lfs", "install"])
            except Exception:
                pass

        # 降低大檔推送被緩衝區截斷的機率
        for key, value in (
            ("http.postBuffer", "524288000"),
            ("http.lowSpeedLimit", "0"),
            ("http.lowSpeedTime", "999999"),
            ("lfs.concurrenttransfers", "4"),
        ):
            try:
                self._run_git(["config", key, value])
            except Exception:
                pass

    def _lfs_available(self):
        try:
            result = subprocess.run(
                "git lfs version",
                cwd=self.repo_path or os.getcwd(),
                capture_output=True,
                text=True,
                shell=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _auto_track_oversized_files(self):
        """掃描超過門檻的檔案；若尚未被 LFS 規則涵蓋，以完整相對路徑追加追蹤"""
        attr_path = os.path.join(self.repo_path, ".gitattributes")
        existing = ""
        if os.path.exists(attr_path):
            with open(attr_path, "r", encoding="utf-8") as f:
                existing = f.read()

        extra_paths = []
        for root_dir, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d != ".git" and not d.startswith(".")]
            for name in files:
                path = os.path.join(root_dir, name)
                rel = os.path.relpath(path, self.repo_path).replace("\\", "/")
                if not self._is_dsproj_rel(rel):
                    continue
                try:
                    size_mb = os.path.getsize(path) / (1024 * 1024)
                except OSError:
                    continue
                if size_mb < LARGE_FILE_SOFT_MB:
                    continue
                # 已由通用規則涵蓋者略過（稍後以 check-attr 再確認亦可）
                if f"{rel} filter=lfs" in existing:
                    continue
                extra_paths.append(rel)

        if not extra_paths:
            return

        # 只幫「目前沒有 filter=lfs」的路徑加規則
        need_attr = []
        try:
            for i in range(0, len(extra_paths), 40):
                chunk = extra_paths[i : i + 40]
                result = subprocess.run(
                    ["git", "check-attr", "filter", "--"] + chunk,
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                for line in (result.stdout or "").splitlines():
                    parts = [p.strip() for p in line.split(":")]
                    if len(parts) >= 3 and parts[2] != "lfs":
                        need_attr.append(parts[0].replace("\\", "/"))
        except Exception:
            need_attr = list(extra_paths)

        if not need_attr:
            return

        with open(attr_path, "a", encoding="utf-8") as f:
            f.write("\n# 自動偵測之大型檔案（依路徑追蹤）\n")
            for rel in sorted(set(need_attr)):
                f.write(f"{rel} filter=lfs diff=lfs merge=lfs -text\n")

        try:
            self._run_git(["add", "--renormalize", "."])
        except Exception:
            pass

    def find_oversized_non_lfs_files(self):
        """找出超過硬性門檻、且 .gitattributes 未套用 LFS filter 的檔案"""
        risky = []
        candidates = []
        for root_dir, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d != ".git" and not d.startswith(".")]
            for name in files:
                path = os.path.join(root_dir, name)
                rel = os.path.relpath(path, self.repo_path).replace("\\", "/")
                if not self._is_dsproj_rel(rel):
                    continue
                try:
                    size_mb = os.path.getsize(path) / (1024 * 1024)
                except OSError:
                    continue
                if size_mb < LARGE_FILE_HARD_MB:
                    continue
                candidates.append((rel, round(size_mb, 1)))

        if not candidates:
            return []

        lfs_map = {}
        paths = [c[0] for c in candidates]
        try:
            for i in range(0, len(paths), 40):
                chunk = paths[i : i + 40]
                result = subprocess.run(
                    ["git", "check-attr", "filter", "--"] + chunk,
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                for line in (result.stdout or "").splitlines():
                    parts = [p.strip() for p in line.split(":")]
                    if len(parts) >= 3:
                        lfs_map[parts[0].replace("\\", "/")] = parts[2]
        except Exception:
            pass

        for rel, mb in candidates:
            if lfs_map.get(rel, "") != "lfs":
                risky.append((rel, mb))
        return risky

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
                shell=True,
            )
            if result.returncode != 0:
                error_detail = result.stderr.strip() or result.stdout.strip()
                if "nothing to commit" in error_detail.lower() or "working tree clean" in error_detail.lower():
                    return "目前檔案沒有變動，無需重複儲存。"
                raise Exception(f"\n[執行指令]: {command_str}\n[詳細原因]: {error_detail}")
            return result.stdout.strip()
        except Exception as e:
            raise Exception(f"無法順利呼叫 Git！\n系統訊息: {str(e)}")

    def get_current_branch(self):
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            name = (result.stdout or "").strip()
            if result.returncode == 0 and name and name != "HEAD":
                return name
        except Exception:
            pass
        branches = self.get_all_branches()
        return branches[0] if branches else "main"

    @staticmethod
    def next_pull_version_name(current_name):
        """前一版號加上 .1-Pull；若已是 .N-Pull 則 N+1"""
        current_name = (current_name or "main").strip() or "main"
        match = re.match(r"^(.*)\.(\d+)-Pull$", current_name)
        if match:
            return f"{match.group(1)}.{int(match.group(2)) + 1}-Pull"
        return f"{current_name}.1-Pull"

    @staticmethod
    def make_pull_commit_message(description="Pull from server"):
        """Pull 補充說明：原文後面加上本機日期與時間"""
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        base = (description or "Pull from server").strip() or "Pull from server"
        return f"{base} {stamp}"

    def create_pull_version(self, description="Pull from server"):
        """新增 pull 版本分支，說明為 Pull from server 加上當下日期時間"""
        current = self.get_current_branch()
        name = self.next_pull_version_name(current)
        existing = set(self.get_all_branches())
        while name in existing:
            name = self.next_pull_version_name(name)
        self._run_git(["checkout", "-b", name])
        try:
            self._ensure_lfs_installed()
            self._auto_track_oversized_files()
        except Exception:
            pass
        self._stage_dsproj_only()
        message = self.make_pull_commit_message(description)
        self._run_git(["commit", "--allow-empty", "-m", message])
        return name

    def get_all_branches(self):
        try:
            result = subprocess.run(
                "git branch",
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                shell=True,
            )
            if result.returncode != 0:
                return ["main"]
            branches = []
            for line in result.stdout.split("\n"):
                if line.strip():
                    clean_name = line.replace("*", "").strip()
                    branches.append(clean_name)
            return branches
        except Exception:
            return ["main"]

    def get_branch_info(self, branch_name):
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%B", branch_name],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return "無說明紀錄"
        except Exception:
            return "無法取得說明"

    def switch_branch(self, branch_name):
        try:
            self._run_git(["stash"])
        except Exception:
            pass
        self._run_git(["checkout", branch_name])
        return f"🔄 已成功將專案資料夾恢復至 `{branch_name}` 版本的狀態！"

    def create_scenario_branch(self, branch_name):
        branches = self.get_all_branches()
        if branch_name in branches:
            self._run_git(["checkout", branch_name])
            return f"👉 已切換至現有情境: {branch_name}"
        self._run_git(["checkout", "-b", branch_name])
        return f"✨ 已建立並切換至新情境: {branch_name}"

    def commit_scenario_changes(self, description):
        self.create_lfs_and_ignore_rules()
        self._ensure_lfs_installed()
        self._auto_track_oversized_files()
        self._stage_dsproj_only()
        self._run_git(["commit", "--allow-empty", "-m", description])
        return "已成功將進度與說明寫入版本庫！"

    @staticmethod
    def normalize_remote_url(url):
        """將內網 UNC / 本機路徑轉成 Git 可用的遠端位址"""
        url = (url or "").strip().strip('"')
        if not url:
            return url

        # 已是 http(s) / git / ssh / file 協定
        if re.match(r"^(https?|git|ssh|file):", url, re.I):
            return url
        if url.startswith("git@"):
            return url

        # UNC：\\server\share\path  →  //server/share/path（Git for Windows 可接受）
        if url.startswith("\\\\"):
            return url.replace("\\", "/")

        # 本機磁碟路徑：D:\repos\model.git
        if re.match(r"^[A-Za-z]:[\\/]", url):
            return url.replace("\\", "/")

        return url

    @staticmethod
    def is_filesystem_remote(url):
        if not url:
            return False
        if re.match(r"^(https?|git|ssh):", url, re.I) or url.startswith("git@"):
            return False
        if url.lower().startswith("file:"):
            return True
        if url.startswith("//") or url.startswith("\\\\"):
            return True
        if re.match(r"^[A-Za-z]:[\\/]", url):
            return True
        return False

    @staticmethod
    def filesystem_remote_to_path(url):
        """把 file:// 或 //server/... 轉回 os 可建立目錄的路徑"""
        path = url
        if path.lower().startswith("file:///"):
            path = path[8:]
        elif path.lower().startswith("file://"):
            path = path[7:]
        path = path.replace("/", "\\") if os.name == "nt" else path
        return path

    @staticmethod
    def _to_git_path(path):
        """Git for Windows 較吃正斜線路徑，UNC 也較穩定"""
        return os.path.normpath(path).replace("\\", "/")

    @staticmethod
    def _is_dot_git_named_path(path):
        """資料夾名稱以 .git 結尾（例如 NWT_LK.git）→ Git 會當成裸庫目錄本身"""
        name = os.path.basename(str(path).rstrip("\\/"))
        return name.lower().endswith(".git") and name.lower() != ".git"

    @staticmethod
    def _is_bare_repo(path):
        """裸庫：根目錄有 HEAD/objects，但沒有 .git 子目錄"""
        if os.path.isdir(os.path.join(path, ".git")):
            return False
        return os.path.isfile(os.path.join(path, "HEAD")) and os.path.isdir(
            os.path.join(path, "objects")
        )

    def _restore_inner_git_to_bare(self, path):
        """若先前誤把裸庫轉成 xxx.git/.git/，把內容搬回根目錄還原成裸庫"""
        inner = os.path.join(path, ".git")
        if not os.path.isdir(inner):
            return False
        if not os.path.isfile(os.path.join(inner, "HEAD")):
            return False
        if os.path.isfile(os.path.join(path, "HEAD")):
            return False
        for name in list(os.listdir(inner)):
            src = os.path.join(inner, name)
            dst = os.path.join(path, name)
            if os.path.exists(dst):
                continue
            shutil.move(src, dst)
        try:
            shutil.rmtree(inner, ignore_errors=True)
        except OSError:
            pass
        return True

    def _run_git_at(self, git_dir, args, work_tree=None):
        cmd = ["git", "--git-dir", self._to_git_path(git_dir)]
        if work_tree:
            cmd += ["--work-tree", self._to_git_path(work_tree)]
        cmd += args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def _configure_working_remote(self, path):
        git_dir = os.path.join(path, ".git")
        for key, value in (
            ("core.bare", "false"),
            ("receive.denyCurrentBranch", "updateInstead"),
        ):
            result = self._run_git_at(git_dir, ["config", key, value], work_tree=path)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip()
                raise Exception(f"無法設定遠端工作區：\n{path}\n{detail}")

    def _ensure_bare_repo(self, path):
        os.makedirs(path, exist_ok=True)
        if self._is_dot_git_named_path(path):
            self._restore_inner_git_to_bare(path)
        if self._is_bare_repo(path):
            return
        result = subprocess.run(
            ["git", "init", "--bare", self._to_git_path(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise Exception(f"無法在遠端路徑建立裸儲存庫：\n{path}\n{detail}")

    def ensure_filesystem_remote(self, remote_url):
        """內網遠端：Git 追蹤與 .dsproj 執行檔都放在同一個資料夾"""
        if not self.is_filesystem_remote(remote_url):
            return
        path = self.filesystem_remote_to_path(remote_url)
        os.makedirs(path, exist_ok=True)

        if self._is_dot_git_named_path(path) or self._is_bare_repo(path):
            self._ensure_bare_repo(path)
            return

        git_dir = os.path.join(path, ".git")
        if not os.path.isdir(git_dir):
            result = subprocess.run(
                ["git", "init", "-b", "main", self._to_git_path(path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                result = subprocess.run(
                    ["git", "init", self._to_git_path(path)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip()
                raise Exception(f"無法在遠端路徑建立儲存庫：\n{path}\n{detail}")

        self._configure_working_remote(path)

    def _list_dsproj_runtime_files(self):
        """列出本機要同步到遠端的執行檔（.dsproj 與 .dsproj_data 內所有檔案）"""
        files = []
        for root_dir, dirs, filenames in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d != ".git"]
            rel_root = os.path.relpath(root_dir, self.repo_path)
            rel_root_posix = "." if rel_root == "." else rel_root.replace("\\", "/")
            in_data = rel_root_posix != "." and any(
                part.endswith(".dsproj_data") for part in rel_root_posix.split("/")
            )
            for name in filenames:
                rel = name if rel_root == "." else os.path.join(rel_root, name)
                rel_posix = rel.replace("\\", "/")
                if name.endswith(".dsproj") and not name.endswith(".dsproj_data"):
                    files.append(rel)
                elif in_data and self._is_dsproj_rel(rel_posix):
                    files.append(rel)
        return files

    def _same_file_snapshot(self, src, dst):
        try:
            if not os.path.isfile(dst):
                return False
            ss, ds = os.stat(src), os.stat(dst)
            return ss.st_size == ds.st_size and int(ss.st_mtime) == int(ds.st_mtime)
        except OSError:
            return False

    def deploy_runnable_files(self, remote_url, progress_callback=None):
        """把 .dsproj 與 .dsproj_data 複製到「同一個」遠端資料夾（與 Git 追蹤並存）"""
        remote_path = self.filesystem_remote_to_path(remote_url)
        os.makedirs(remote_path, exist_ok=True)
        files = self._list_dsproj_runtime_files()
        if not files:
            raise Exception(
                "找不到 .dsproj 或 .dsproj_data 內的檔案，無法推送模式執行檔。"
            )

        total = len(files)
        copied = 0
        skipped = 0
        for i, rel in enumerate(files):
            src = os.path.join(self.repo_path, rel)
            dst = os.path.join(remote_path, rel)
            if not os.path.isfile(src):
                skipped += 1
                continue
            os.makedirs(os.path.dirname(dst) or remote_path, exist_ok=True)
            if self._same_file_snapshot(src, dst):
                skipped += 1
                continue
            size_mb = os.path.getsize(src) / (1024 * 1024)
            if progress_callback:
                pct = 70 + int(((i + 1) / max(total, 1)) * 28)
                name = rel.replace("\\", "/")
                if size_mb >= 5:
                    progress_callback(f"正在寫入執行檔 ({i + 1}/{total}): {name} ({size_mb:.1f} MB)", pct)
                elif i % 20 == 0:
                    progress_callback(f"正在寫入執行檔 ({i + 1}/{total})...", pct)
            shutil.copy2(src, dst)
            copied += 1

        return copied, skipped, total

    def set_remote_url(self, remote_url):
        remote_url = self.normalize_remote_url(remote_url)
        if not remote_url:
            raise Exception("遠端路徑不可為空白")

        if self.is_filesystem_remote(remote_url):
            self.ensure_filesystem_remote(remote_url)

        check = subprocess.run(
            "git remote",
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            shell=True,
        )
        extra = self._filesystem_bind_hint(remote_url)
        if "origin" in (check.stdout or ""):
            self._run_git(["remote", "set-url", "origin", remote_url])
            return f"✅ 已更新遠端連結：\n{remote_url}{extra}"
        self._run_git(["remote", "add", "origin", remote_url])
        return f"✅ 已綁定遠端連結：\n{remote_url}{extra}"

    def _filesystem_bind_hint(self, remote_url):
        if not self.is_filesystem_remote(remote_url):
            return ""
        git_path = self.filesystem_remote_to_path(remote_url)
        return (
            f"\n\n推送後會把 Git 追蹤與模式執行檔放在同一個資料夾：\n{git_path}\n"
            "僅包含 .dsproj 與 .dsproj_data。"
        )

    def get_remote_url(self):
        try:
            result = subprocess.run(
                "git config --get remote.origin.url",
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                shell=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return ""
        except Exception:
            return ""

    def prepare_for_push(self, progress_callback=None, require_lfs=True):
        """推送前：更新規則、提交變更；GitHub 才強制 LFS 大檔檢查"""
        if progress_callback:
            progress_callback("更新 .gitignore / LFS 規則...", 5)
        self.create_lfs_and_ignore_rules()
        if require_lfs:
            self._ensure_lfs_installed()
            self._auto_track_oversized_files()
        else:
            try:
                self._ensure_lfs_installed()
                self._auto_track_oversized_files()
            except Exception:
                pass

        if progress_callback:
            progress_callback("檢查並暫存 .dsproj / .dsproj_data...", 12)
        self._stage_dsproj_only()
        if self.has_uncommitted_changes():
            try:
                self._run_git(["commit", "-m", "Auto Save: 推送前自動提交 Delta Shell 專案變更"])
            except Exception:
                pass

        if not require_lfs:
            return

        risky = self.find_oversized_non_lfs_files()
        if risky:
            preview = "\n".join(f"  - {p} ({mb} MB)" for p, mb in risky[:8])
            more = f"\n  ... 另有 {len(risky) - 8} 個檔案" if len(risky) > 8 else ""
            raise Exception(
                "偵測到超過約 90MB 且尚未轉成 LFS 指標的檔案，直接推送很可能被遠端拒絕。\n"
                "請確認已安裝 Git LFS，或將這些檔案加入 .gitattributes 後重新提交。\n\n"
                f"{preview}{more}"
            )

    def push_with_progress(self, progress_callback):
        remote = self.get_remote_url()
        if not remote:
            raise Exception("尚未綁定遠端路徑，請先在「遠端伺服器備份」分頁輸入並綁定。")

        filesystem = self.is_filesystem_remote(remote)
        self.prepare_for_push(progress_callback, require_lfs=not filesystem)
        if filesystem:
            progress_callback("檢查／建立內網工作資料夾...", 15)
            self.ensure_filesystem_remote(remote)

        if not filesystem:
            progress_callback("正在上傳 LFS 大型檔案...", 20)
            self._run_stream_command(
                ["git", "lfs", "push", "--all", "origin"],
                progress_callback,
                base_pct=20,
                span=40,
            )

        progress_callback("正在推送版本紀錄與分支...", 55 if filesystem else 65)
        try:
            self._run_stream_command(
                ["git", "push", "-u", "origin", "--all", "--progress"],
                progress_callback,
                base_pct=55 if filesystem else 65,
                span=15 if filesystem else 35,
            )
        except Exception as e:
            # 內網資料夾仍可直接複製執行檔；版本紀錄失敗再一併提示
            if not filesystem:
                raise
            progress_callback(f"版本紀錄推送警告（仍會複製執行檔）: {str(e)[:60]}", 68)

        if filesystem:
            dest = self.filesystem_remote_to_path(remote)
            progress_callback(f"正在寫入 .dsproj / .dsproj_data 至：{dest}", 70)
            copied, skipped, total = self.deploy_runnable_files(remote, progress_callback)
            progress_callback(
                f"已寫入 {copied} 個執行檔（略過未變更 {skipped} / 共 {total}）",
                99,
            )

        progress_callback("上傳完成！", 100)

    def _run_stream_command(self, command, progress_callback, base_pct=0, span=100):
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
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            buffer = ""
            full_log = []
            while True:
                char = process.stdout.read(1)
                if not char and process.poll() is not None:
                    break
                if char in ("\r", "\n"):
                    if buffer.strip():
                        text = buffer.strip()
                        full_log.append(text)
                        match = re.search(r"(\d+)%", text)
                        if match:
                            local = int(match.group(1))
                            pct = int(base_pct + (local / 100.0) * span)
                        else:
                            pct = None
                        progress_callback(text, pct)
                        buffer = ""
                else:
                    buffer += char
            process.wait()
            if process.returncode != 0:
                error_msg = "\n".join(full_log[-20:])
                raise Exception(self._friendly_push_error(process.returncode, error_msg))
        except Exception as e:
            if "執行上傳時發生錯誤" in str(e) or "檔案過大" in str(e) or "Git 返回" in str(e):
                raise
            raise Exception(f"執行上傳時發生錯誤:\n{str(e)}")

    @staticmethod
    def _friendly_push_error(returncode, error_msg):
        lower = error_msg.lower()
        hints = []
        if "exceeds" in lower and ("100" in lower or "mb" in lower):
            hints.append(
                "遠端拒絕：有檔案超過大小限制。請確認該副檔名已列入 Git LFS，"
                "並重新提交後再推送（歷史中若已含大檔，可能需 git lfs migrate）。"
            )
        if "lfs" in lower and ("batch" in lower or "lock" in lower or "unsupported" in lower):
            hints.append(
                "此遠端可能不支援 LFS HTTP API。若目標是內網共用資料夾，"
                "請直接綁定該資料夾路徑；程式會把可執行的模式檔複製過去。"
            )
        if "denyCurrentBranch" in error_msg or "checked out branch" in lower:
            hints.append(
                "遠端是一般工作區且拒絕更新目前分支。程式會改設 "
                "receive.denyCurrentBranch=updateInstead，請再推送一次。"
            )
        if "rejected" in lower or "non-fast-forward" in lower:
            hints.append("遠端分支有較新內容。若確定要以本機覆蓋，請先與管理員確認後再強制推送。")
        if "could not read username" in lower or "authentication" in lower:
            hints.append("遠端需要帳號驗證，請先在系統完成 Git 登入或改用內網共用資料夾路徑。")

        hint_block = ("\n\n[建議]\n" + "\n".join(f"- {h}" for h in hints)) if hints else ""
        return (
            f"Git 返回代碼: {returncode}\n\n"
            f"[詳細伺服器拒絕原因]:\n{error_msg}{hint_block}"
        )

    @staticmethod
    def _copy_dsproj_between(src_root, dest_root, progress_callback=None, base_pct=50, span=40):
        files = []
        for root_dir, dirs, filenames in os.walk(src_root):
            dirs[:] = [d for d in dirs if d != ".git"]
            rel_root = os.path.relpath(root_dir, src_root)
            rel_root_posix = "." if rel_root == "." else rel_root.replace("\\", "/")
            in_data = rel_root_posix != "." and any(
                part.endswith(".dsproj_data") for part in rel_root_posix.split("/")
            )
            for name in filenames:
                rel = name if rel_root == "." else os.path.join(rel_root, name)
                rel_posix = rel.replace("\\", "/")
                if name.endswith(".dsproj") and not name.endswith(".dsproj_data"):
                    files.append(rel)
                elif in_data and GitModelManager._is_dsproj_rel(rel_posix):
                    files.append(rel)

        total = len(files)
        copied = 0
        for i, rel in enumerate(files):
            src = os.path.join(src_root, rel)
            dst = os.path.join(dest_root, rel)
            if not os.path.isfile(src):
                continue
            os.makedirs(os.path.dirname(dst) or dest_root, exist_ok=True)
            if progress_callback and (i % 15 == 0 or os.path.getsize(src) > 5 * 1024 * 1024):
                pct = base_pct + int(((i + 1) / max(total, 1)) * span)
                shown = rel.replace("\\", "/")
                progress_callback(f"複製執行檔 ({i + 1}/{total}): {shown}", pct)
            shutil.copy2(src, dst)
            copied += 1
        return copied, total

    @staticmethod
    def _clone_filesystem(url, target_path, progress_callback):
        """只拉 .dsproj / .dsproj_data；不複製遠端 .git，改在本機 Git 新增 pull 紀錄"""
        src = GitModelManager.filesystem_remote_to_path(url)
        if not os.path.isdir(src):
            raise Exception(f"找不到遠端資料夾：\n{src}\n請確認內網路徑可存取。")

        os.makedirs(target_path, exist_ok=True)
        progress_callback("正在複製 .dsproj / .dsproj_data...", 20)
        copied, total = GitModelManager._copy_dsproj_between(
            src, target_path, progress_callback, base_pct=20, span=55
        )
        if copied == 0 and total == 0:
            raise Exception(
                f"遠端找不到 .dsproj 或 .dsproj_data。\n路徑：{src}"
            )

        progress_callback("正在建立本機 pull 版本...", 80)
        mgr = GitModelManager(target_path)
        if not mgr.is_initialized():
            mgr._run_git(["init"])
            mgr.create_lfs_and_ignore_rules()
            try:
                mgr._run_git(["branch", "-M", "main"])
            except Exception:
                pass
        else:
            mgr.create_lfs_and_ignore_rules()

        origin = GitModelManager.normalize_remote_url(url)
        check = subprocess.run(
            "git remote",
            cwd=target_path,
            capture_output=True,
            text=True,
            shell=True,
        )
        if "origin" in (check.stdout or ""):
            mgr._run_git(["remote", "set-url", "origin", origin])
        else:
            mgr._run_git(["remote", "add", "origin", origin])

        version = mgr.create_pull_version("Pull from server")
        progress_callback(f"同步完成（執行檔 {copied}/{total}），新版本：{version}", 100)
        return version

    @staticmethod
    def clone_repo(url, target_path, progress_callback):
        try:
            if GitModelManager.is_filesystem_remote(url):
                return GitModelManager._clone_filesystem(url, target_path, progress_callback)

            clone_url = GitModelManager.normalize_remote_url(url)
            os.makedirs(target_path, exist_ok=True)
            dest_git = os.path.join(target_path, ".git")
            no_window = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            existing = [n for n in os.listdir(target_path) if n not in (".", "..")]

            if os.path.isdir(dest_git):
                progress_callback("本機資料夾已有 Git，正在 pull...", 20)
                subprocess.run(
                    ["git", "remote", "remove", "origin"],
                    cwd=target_path,
                    capture_output=True,
                    creationflags=no_window,
                )
                add = subprocess.run(
                    ["git", "remote", "add", "origin", clone_url],
                    cwd=target_path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=no_window,
                )
                if add.returncode != 0:
                    subprocess.run(
                        ["git", "remote", "set-url", "origin", clone_url],
                        cwd=target_path,
                        capture_output=True,
                        creationflags=no_window,
                    )
                pull = subprocess.run(
                    ["git", "pull", "--ff-only", "origin"],
                    cwd=target_path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=no_window,
                )
                if pull.returncode != 0:
                    fetch = subprocess.run(
                        ["git", "fetch", "origin"],
                        cwd=target_path,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=no_window,
                    )
                    checkout = subprocess.run(
                        ["git", "checkout", "-f", "-B", "main", "origin/main"],
                        cwd=target_path,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=no_window,
                    )
                    if fetch.returncode != 0 or checkout.returncode != 0:
                        detail = (
                            (pull.stderr or pull.stdout or "")
                            + "\n"
                            + (checkout.stderr or checkout.stdout or fetch.stderr or "")
                        ).strip()
                        raise Exception(f"Pull 失敗：\n{detail or '(無 Git 輸出)'}")
                progress_callback("正在下載 LFS 大型檔案...", 95)
                subprocess.run(
                    ["git", "lfs", "pull"],
                    cwd=target_path,
                    capture_output=True,
                    creationflags=no_window,
                )
                progress_callback("下載完成！", 100)
                return

            if existing:
                progress_callback("正在把遠端內容拉進現有資料夾...", 15)
                init = subprocess.run(
                    ["git", "init", target_path],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=no_window,
                )
                if init.returncode != 0:
                    raise Exception(f"無法在本機資料夾初始化 Git：\n{(init.stderr or init.stdout or '').strip()}")
                subprocess.run(
                    ["git", "remote", "add", "origin", clone_url],
                    cwd=target_path,
                    capture_output=True,
                    creationflags=no_window,
                )
                fetch = subprocess.run(
                    ["git", "fetch", "--progress", "origin"],
                    cwd=target_path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=no_window,
                )
                checkout = subprocess.run(
                    ["git", "checkout", "-f", "-B", "main", "origin/main"],
                    cwd=target_path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=no_window,
                )
                if checkout.returncode != 0:
                    checkout = subprocess.run(
                        ["git", "checkout", "-f", "-B", "master", "origin/master"],
                        cwd=target_path,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=no_window,
                    )
                if fetch.returncode != 0 or checkout.returncode != 0:
                    detail = ((fetch.stderr or fetch.stdout or "") + "\n" + (checkout.stderr or checkout.stdout or "")).strip()
                    raise Exception(f"無法拉下遠端內容：\n{detail or '(無 Git 輸出)'}")
                progress_callback("正在下載 LFS 大型檔案...", 95)
                subprocess.run(
                    ["git", "lfs", "pull"],
                    cwd=target_path,
                    capture_output=True,
                    creationflags=no_window,
                )
                progress_callback("下載完成！", 100)
                return

            command = ["git", "clone", "--progress", clone_url, target_path]
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            buffer = ""
            full_log = []
            while True:
                char = process.stdout.read(1)
                if not char and process.poll() is not None:
                    break
                if char in ("\r", "\n"):
                    if buffer.strip():
                        text = buffer.strip()
                        full_log.append(text)
                        match = re.search(r"(\d+)%", text)
                        pct = int(match.group(1)) if match else None
                        progress_callback(text, pct)
                        buffer = ""
                else:
                    buffer += char
            if buffer.strip():
                full_log.append(buffer.strip())
            process.wait()
            if process.returncode != 0:
                error_msg = "\n".join(full_log[-15:]) or "(無 Git 輸出)"
                raise Exception(
                    f"Clone 失敗，代碼: {process.returncode}\n\n[詳細原因]:\n{error_msg}"
                )

            progress_callback("正在下載 LFS 大型檔案...", 95)
            lfs_pull = subprocess.run(
                ["git", "lfs", "pull"],
                cwd=target_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if lfs_pull.returncode != 0:
                detail = (lfs_pull.stderr or lfs_pull.stdout or "").strip()
                if detail and "not a git repository" not in detail.lower():
                    progress_callback(f"LFS pull 警告: {detail[:80]}", 98)
            progress_callback("下載完成！", 100)
            return None
        except Exception as e:
            msg = str(e).strip() or repr(e)
            raise Exception(f"執行 Clone 時發生錯誤:\n{msg}")
