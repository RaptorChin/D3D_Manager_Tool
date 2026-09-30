# 版本控管模組（已完成）

版本：對應程式 v1.2.1（2026-08-27）
狀態：✅ 已發佈。本文件為**現況紀錄**（as-built），修改此模組前必讀。
相關：`docs/OVERVIEW.md`、`core/git_control.py`、`ui/build_workspace.py`（v2.0 ① 模型建置工作區；v1.2.1 為 `app_ctk.py`）、
操作教學 `D-Flow模式檔案管理系統v1.2_操作教學.pptx`

---

## 0. 目標

讓不熟 Git 的模型工程師，能對 Delta Shell 專案做「存檔點、回到過去、備份到伺服器、換電腦下載」，
而不必碰指令列，也不會因大檔被遠端拒絕。

## 1. 核心設計決策（修改前務必理解原因）

| 決策 | 內容 | 原因 |
|---|---|---|
| 只追蹤執行所需檔案 | `.gitignore` 預設 `*` 忽略全部，只放行 `*.dsproj`、`*.dsproj_data/**`、`.gitignore`、`.gitattributes` | 避免 output、快取、獨立 .mdu 讓版本庫膨脹；Delta Shell 開啟專案只需要這兩項 |
| 每次存檔都強制套用規則 | `create_lfs_and_ignore_rules()` → `_auto_track_oversized_files()` → `_stage_dsproj_only()` | 使用者可能手動改過規則或加了新大檔；`_stage_dsproj_only()` 也會把不該追蹤的檔案 `rm --cached` |
| Git LFS 接管大檔 | 常見大檔副檔名（`*.xyz`、`*_net.nc`、`*.bc`、`*.tif`…）預設走 LFS；另掃描 ≥ 50 MB 的檔案以完整路徑追加規則 | GitHub 單檔上限 100 MB；推送前對 ≥ 90 MB 且非 LFS 指標的檔案提出警告 |
| 版本 = 分支 | 建置快照建立 `build/<標籤>` 分支；時光機列出所有分支 | 對使用者而言「版本」比 commit 直覺；每個版本可以再疊加多次存檔 |
| 內網遠端 = 子資料夾裸儲存庫 | 綁定 `\\伺服器\共用\專案` 時，版本紀錄放在其下 `.d3d_version_history.git`（bare repo），`.dsproj`/`.dsproj_data` 另外直接複製到父層 | v1.2 前用一般儲存庫，Git 工作目錄與直接複製的檔案互相衝突導致 push 被拒；分開後互不干涉，其他人也能直接從父層開啟專案 |
| 下載自動產生 Pull 版本 | 內網下載後依目前版本建立 `<原版本>.1-Pull`（已是 `.N-Pull` 則 N+1），說明 `Pull from server <日期時間>` | 可追溯這批檔案何時從伺服器同步下來 |
| 版本說明跳過自動訊息 | 顯示版本說明時略過 `Auto Save:`、`Auto Initial commit:` 開頭的 commit，往回找使用者的說明（v1.2.1） | 自動存檔會把使用者的說明蓋掉 |
| 全域 safe.directory | 啟動時 `ensure_global_safe_directory()` | 網路磁碟／其他使用者建立的資料夾會被 Git 視為不安全而拒絕操作 |
| 不跳出黑色視窗 | subprocess 一律 `CREATE_NO_WINDOW` | 打包成 --noconsole 的 exe 時避免閃視窗 |

## 2. 功能清單與對應程式

| 功能 | UI 位置（v2.0 ① 模型建置工作區） | `GitModelManager` 方法 |
|---|---|---|
| Git 身分顯示／設定（全域） | 共用資訊列「Git 身分」＋⚙️；啟動時未設定自動跳出 | `get_global_user_identity`、`set_global_user_identity`、`is_global_user_configured` |
| 開啟工作資料夾（三種情境：未初始化／有未存變更／乾淨） | 共用資訊列「瀏覽本機」 | `is_initialized`、`has_uncommitted_changes`、`do_initial_setup`、`do_auto_commit` |
| 狀態檢查（重寫規則、確認 LFS） | 共用資訊列「狀態檢查」 | `init_repo` |
| 時光機：列出版本、顯示說明、恢復 | 「本機建置」分頁左側「時光機」 | `get_all_branches`、`get_current_branch`、`get_branch_info`、`switch_branch` |
| 建置快照 | 「本機建置」分頁右側「儲存建置快照」 | `create_scenario_branch("build/<標籤>")`、`commit_scenario_changes` |
| 綁定遠端（GitHub HTTPS 或內網 UNC） | 「推送到遠端」分頁 | `normalize_remote_url`、`set_remote_url`、`ensure_filesystem_remote` |
| 推送（規則 → LFS → 版本紀錄 → 執行檔複製） | 同上，含進度視窗 | `prepare_for_push`、`push_with_progress`、`deploy_runnable_files`、`_sync_lfs_objects` |
| 下載（Clone） | 共用資訊列「從雲端下載」對話框 | `clone_repo`、`_clone_filesystem`、`create_pull_version` |
| 版本歷史查詢（本機或遠端資料夾，唯讀） | 「版本歷史」分頁 | `resolve_git_root`、`get_latest_branch`、`get_commit_log` |

## 3. 外部相依

- 使用者電腦需安裝 **Git** 與 **Git LFS**（未安裝時 `_ensure_lfs_installed` 丟出 zh-TW 說明）。
- 遠端：GitHub（HTTPS）或公司內網共用資料夾（格式：`\\伺服器\共用資料夾\…\<專案代號>`）。

## 4. 與其他模組的界線

- **執行模組、成果模組不得呼叫 `GitModelManager`**，也不得要求資料夾已初始化 Git（見 run SPEC §0）。
- DIMR 匯出資料夾、`output\`、執行 log、預檢備份都被 `.gitignore` 排除，不會進版本庫。
- 舊版「📝 情境參數設定」分頁曾以 `scenario/<名稱>` 分支＋configparser 改 MDU 的方式實作（隱藏中）；
  新版改由 run SPEC P5 的情境精靈取代，**不再使用 Git 分支**。`create_scenario_branch` 仍供建置快照使用。

## 4.5 修正紀錄

| 日期 | 問題 | 修正 |
|---|---|---|
| 2026-09-29 | 內網路徑開頭少了 `\`（例：`伺服器\共用\專案`）時被當成網址，推送時 Git LFS 報「batch request: missing protocol」 | `normalize_remote_url` 自動補成 `//伺服器/…`；`push_with_progress` 推送前先正規化已儲存的位址，舊專案不必重新綁定（測試：`tests/test_git_control_remote.py`） |

## 5. 已知限制與日後可改善

| 項目 | 說明 |
|---|---|
| 自動化測試不足 | 目前只有遠端位址處理與內網推送（`tests/test_git_control_remote.py`）；其餘功能日後修改時再補 |
| `git_control.py` 約 1,450 行 | 單一類別過大；若日後大改可拆成 identity / local / remote / lfs 子模組（非必要不動） |
| `app.py` 背景執行緒 | 此模組的進度視窗已透過 `root.after(0, ...)` 回主執行緒更新，屬正確做法 |
| 恢復版本會覆蓋未存檔修改 | 目前以確認對話框提醒；可考慮恢復前自動存一個快照 |
