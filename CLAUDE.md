# D3D_Manager_Tool — Claude Code 專案指引

> 本檔案由 Claude Code 在每次開啟專案時自動讀取。請保持精簡；詳細規格放在 `docs/`。

## 溝通語言

- 一律使用**台灣繁體中文（zh-TW）**回覆與撰寫註解、UI 文字、commit 訊息；避免簡體字與大陸用語
  （例：使用「檔案、資料夾、程式、設定、執行緒、預設」，不用「文件、文件夾、程序、配置、線程、默認」）。
- 程式識別字（變數、函式、類別名稱）用英文。

## 專案概述

- 桌面工具：輔助 Delft3D FM Suite（D-Flow FM / D-HYDRO 1D2D）的三個工作階段——
  **① 建置模型**（版本控管、模型檢視）→ **② 執行模擬**（預檢、分割、MPI 執行、監控）→ **③ 檢視成果**（結果檢核、淹水統計、情境比較）。
- 技術：Python（目前環境 3.14）、**Flet 0.86.5**（v2.0 起；v1.x 為 CustomTkinter），以 `flet pack` 打包成 Windows 單一執行檔。
- 目標平台：**僅 Windows**（使用者工作站：Windows、Delft3D FM Suite 2026.02 1D2D、Intel MPI）。
- 入口：`app.py`（Flet 版 v2.0）；畫面在 `ui/`，核心邏輯在 `core/`，圖示在 `assets/`。
  舊版 CustomTkinter 介面保留為 `app_ctk.py`（v1.2.1 行為），v2.0 確認穩定後刪除。
- 已發佈：v1.2.1（版本控管功能）。開發中：v2.0（分支 `dev/v2.0`）。

## 文件地圖（開工前先看 OVERVIEW）

| 文件 | 內容 |
|---|---|
| **`docs/OVERVIEW.md`** | 整體規劃：模組地圖與狀態、架構、版本歷程、**里程碑 M0～M7**、待決事項 |
| `docs/SPEC_version_control.md` | ✅ 已完成的版本控管模組現況與設計決策（修改 `git_control.py` 前必讀） |
| `docs/SPEC_run_module.md` | 📐 執行模擬模組規格 P1～P5（目前開發主題） |
| `docs/DOMAIN_NOTES_run_module.md` | Delft3D FM 領域知識與實務踩坑 |
| `docs/SPEC_build_module.md` | 💡 建置輔助構想（範圍待確認） |
| `docs/SPEC_results_module.md` | 💡 成果檢視構想（範圍待確認） |
| `docs/UI_PLAN.md` | **畫面架構（主頁面＋三大工作區）**、Flet 遷移範圍、Flet 踩坑紀錄（寫 Flet 程式前必讀） |
| `tests/fixtures/README.md` | 測試資料說明 |

## 目前開發主題：里程碑 M2（執行模組 P2），M1.5 待使用者以真實專案驗證推送／下載

開發範圍原則：
- 執行模組與成果模組**不整合 Git 版本控制**。不得呼叫 `GitModelManager`，也不得要求資料夾已初始化 Git。
- 既有的 Git 功能（分頁 1、4、5 與 `core/git_control.py`）維持原狀，除非任務明確要求，否則不要修改。
- 依 OVERVIEW 的里程碑與 SPEC 的階段（P1 → P5）逐步進行；每個階段完成、測試通過後再進入下一階段。
- 標示 💡 的構想模組，需先與使用者確認範圍並補齊規格，才可開始實作。
- 新畫面一律依 `docs/UI_PLAN.md` §1 放進對應工作區（① 建置／② 執行／③ 成果）的分頁，不再新增平鋪的頂層分頁。
- 各文件的「狀態」欄與 OVERVIEW 的模組地圖，在階段完成時一併更新。

## 程式慣例

### 模型檔讀寫（重要）
- **禁止使用 `configparser` 讀寫 `.mdu`、`.ext`、`.bc`、`.ini` 模型檔。**
  原因（已用實際檔案驗證）：
  1. key 大小寫：GUI 寫 `TStop`，`optionxform=str` 後 `get('Tstop')` 取不到，會回傳預設值。
  2. 行尾註解 `# ...` 會被當成值的一部分。
  3. 寫回時丟失檔頭註解、對齊空白，且會「新增」`Tstop` 而非修改 `TStop`，造成重複 key。
  4. 新格式 `.ext` 允許多個同名區塊（`[Boundary]`、`[Meteo]`），`configparser` 會丟出 `DuplicateSectionError`。
- 一律使用 `core/model_files/` 內的逐行解析器（P1 已完成：`MduFile`、`ExtFile`、`BcFile`、`FouFile`、`StructuresFile`、`DimrConfig`）：key 比對不分大小寫、只改目標行的「值」、保留其餘位元組（註解、空白、換行符號 CRLF）。

### 畫面與執行緒（Flet，v2.0 起）
- 畫面架構依 `docs/UI_PLAN.md` §1：主頁面 → 工作區（共用資訊列＋分頁）。新功能放進對應工作區的分頁（`ui/workspace.py` 的 `TabSpec`）。
- 共用配色、字型、按鈕等一律用 `ui/theme.py`；對話框用 `ui/dialogs.py`（`alert`、`confirm`、`run_with_progress`）。
- 背景工作一律以 `page.run_thread(func, ...)` 啟動（會帶入頁面 context），在該執行緒中可直接修改元件並呼叫 `page.update()`。
  **前提**：`app.main` 開頭已呼叫 `ui/runtime.install_thread_safe_update(page)`；Flet 0.86.5 背景執行緒的 `page.update()` 原本不會送出（進度條不動），不可移除。
  更新畫面一律用 `page.update()`，不要用 `control.update()`（後者不經過上述修正）。
  長時間工作用 `dialogs.run_with_progress(page, 標題, task)`，`task(update)` 以 `update(文字, 百分比)` 回報進度。
- 選資料夾用 `ft.FilePicker().get_directory_path()`（**非同步**，事件處理函式要寫成 `async def`），取得路徑後再 `page.run_thread(...)` 做耗時工作。
- Flet 0.86.5 API 與舊文件差很多，寫新元件前先用 `inspect.signature()` 核對；踩坑表見 `docs/UI_PLAN.md` §6。
- 字型：微軟正黑體（`Microsoft JhengHei`）、程式碼／log 用 Consolas。色彩語意：藍＝一般、綠＝下載／推送、紅＝危險、橘＝警告、灰＝次要。
- `app_ctk.py`（舊版）已不再修改。

### 外部程序（subprocess）
- 以 list 形式傳參數，不使用 `shell=True`；路徑可能含空白與括號（例：`D:\Models\專案(10m)`）。
- Windows 下加 `creationflags=subprocess.CREATE_NO_WINDOW`（背景工具）或 `CREATE_NEW_PROCESS_GROUP`（需可中止的模擬）。
- stdout 解碼：`encoding=locale.getpreferredencoding(False), errors="replace"`（中文 Windows 多為 cp950），不要硬指定 utf-8。
- 中止模擬：`taskkill /PID <pid> /T /F`（需連同 mpiexec 下的所有 dimr.exe 子程序）。

### 核心模組設計
- `core/` 內的模組**不得 import tkinter / customtkinter**，以便單元測試與日後 CLI 重用。
- 對外回傳結構化結果（dataclass），UI 層負責呈現。
- 檢查結果統一用 `Finding(level: "error"|"warning"|"info", code: str, file: str, message: str, fix: str)`。

## 測試

- 框架：`pytest`。測試放 `tests/`，測試資料放 `tests/fixtures/`（真實模型檔，勿修改原檔；測試需寫入時先複製到 `tmp_path`）。
- 執行：`python -m pytest -q`
- 核心模組（`core/`）新增或修改功能時，必須附測試。UI 不強制測試。
- 需要真實 Delft3D 安裝才能跑的測試，標記 `@pytest.mark.needs_delft3d`，預設略過。
- **真實模型測試資料（`tests/fixtures/NWT_KL/`、`tests/fixtures/runs/`）不進 Git**：GitHub 儲存庫為公開（OVERVIEW D2）。
  用到這些檔案的測試一律加 `@requires_model_fixtures`（或使用 `rain_nc`、`nwt_kl_dir` fixture），檔案不存在時自動略過，不可讓測試因此失敗。
  程式碼、文件、截圖也**不得出現**公司內網伺服器名稱、真實專案路徑、個人信箱；範例一律用 `\\伺服器\共用資料夾\專案`。
  取得方式：`D3D_run_module_handoff.zip`，或原模型的 `DIMR\dflowfm\` 資料夾。

## 相依套件

- 完整清單與安裝方式見 `requirements.txt`（`python -m pip install -r requirements.txt`）。
- Flet 三個套件（`flet`、`flet-desktop`、`flet-cli`）一律鎖定 `0.86.5`，升級需集中處理並重新核對 API。
- `customtkinter` 在 M1.5 遷移完成後移除。
- **打包**：Flet 版使用 `flet pack`（底層為 PyInstaller，產生單一 .exe），**不使用** `flet build windows`（需另裝 Flutter SDK 與 Visual Studio）。
  netCDF4 需加 hidden imports：`cftime`、`netCDF4.utils`。M0 已實測（2026-09-29）：打包後可正常讀取 NetCDF-4 雨量檔；
  單一 .exe 約 95 MB（CustomTkinter 版約 32 MB），啟動解壓約需 5～7 秒。

## 常用指令

```bash
python app.py                 # 啟動程式
python -m pytest -q           # 執行測試
python -m pytest -m needs_delft3d          # 執行需要 Delft3D 的測試（預設略過）
build_exe.bat                               # 打包 v2.0：先跑測試，再 flet pack 產生 dist\D3D_Manager_Tool.exe
python app_ctk.py                           # 啟動舊版 CustomTkinter 介面（v1.2.1）
pyinstaller D3D_Manager_Tool_ctk.spec       # 打包舊版（僅需緊急修正 v1.x 時）
```
