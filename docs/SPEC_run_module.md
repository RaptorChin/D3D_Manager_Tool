# 「▶️ 執行模擬」模組規格書

版本：v0.2（2026-09-29）
狀態：**P1 ✅ 完成（2026-09-29）**；P2 待 M1.5（Flet 遷移）完成後開始
相關文件：`OVERVIEW.md`（整體規劃、里程碑 M1～M5）、`DOMAIN_NOTES_run_module.md`（領域知識，規則背後的原因）、
`tests/fixtures/README.md`（測試資料）、`UI_PLAN.md`（UI 框架決策）

> 本模組在整體規劃中的位置：
> - **P1** 的 `core/model_files/` 與 P3 的 `nc_inspect.py`、`findings.py` 是全專案共用地基，建置輔助（build SPEC）與成果檢視（results SPEC）也會使用。
> - **P4** 的結果檢核（R01～R06）判定「模擬是否有效」；「結果是什麼」的呈現屬成果模組（results SPEC）。
> - **UI 位置**：本模組的畫面都在「**② 執行模擬**」工作區（見 `UI_PLAN.md` §1.3）：
>   共用資訊列＝Delft3D 安裝／DIMR 資料夾／核心數；分頁＝情境設定（P5）、預檢（P3）、執行與監控（P2＋P4）、批次佇列（P5）。
>   P4 的結果檢核畫面在「③ 檢視成果」工作區的「結果檢核」分頁。
> - **P5** 的換雨型精靈修改的是 DIMR 匯出資料夾，不會回寫 `.dsproj`（OVERVIEW 待決事項 D3），因此放在 ② 而非 ①。
> - **UI 框架已決定改用 Flet**（OVERVIEW 待決事項 D1）。下方 P2 的版面草圖與 `root.after` 等寫法是以 CustomTkinter 撰寫的舊版描述；
>   實作時以 UI_PLAN §1 的工作區版面為準，並於 M1.5 完成後、P2 開工前改寫這些段落。

---

## 0. 目標與範圍

### 目標
把「D-Flow FM 模型以 N 核心 MPI 執行一場事件」的整套手動流程自動化，並**在執行前擋下已知錯誤、執行後判定是否為無效模擬**。

```
 [選擇模型] → [預檢] → [分割] → [執行] → [監控] → [結果檢核]
                 │ 有紅燈（error）即不可進入下一步（可由使用者明確覆寫）
```

### 範圍內
- 以 DIMR 匯出資料夾（含 `dimr_config.xml`）為單位執行。
- D-Flow FM 單一元件（可含 1D2D），MPI 平行（N ≥ 1）。
- Windows、Delft3D FM Suite（2023 以後版本的資料夾結構）。

### 範圍外（明確不做）
- **Git 版本控制整合**：執行模組不得呼叫 `GitModelManager`，不得要求資料夾已初始化 Git。
- RTC、D-Waves、D-WAQ 等多元件耦合（偵測到時給 info，不阻擋）。
- Linux / 叢集排程。
- 舊格式 `.ext`（`ExtForceFile`）的完整解析（偵測到時給 info）。

---

## 1. 架構

```
core/
├─ model_files/
│  ├─ __init__.py
│  ├─ ini_lines.py      逐行 INI 引擎（共用）：保留原始位元組、允許重複區塊、key 不分大小寫
│  ├─ mdu_file.py       MduFile：讀值、改值、取得時間窗
│  ├─ ext_file.py       ExtFile：區塊清單、引用檔案、[Meteo] 資訊
│  ├─ bc_file.py        BcFile：[Forcing] 清單、function、時間基準與範圍
│  ├─ fou_file.py       FouFile：各行 quantity / tstart / tstop
│  ├─ structures_file.py  StructuresFile：結構物清單、參數是否為時間序列檔
│  └─ dimr_config.py    DimrConfig：讀 workingDir / inputFile / process；寫入 process 與 communicator
├─ nc_inspect.py        讀 NetCDF 時間軸、變數、屬性、維度大小（netCDF4）
├─ install.py           偵測 Delft3D 安裝、找出各 .bat / .exe
├─ settings.py          使用者設定（%APPDATA%\D3DManagerTool\settings.json）
├─ preflight.py         預檢規則引擎
├─ partition.py         分割流程與 log 解析
├─ runner.py            DimrRunner：啟動、停止、狀態、輸出串流
├─ monitor.py           讀取 rank 0 .dia 的進度統計
├─ postcheck.py         結果檢核與報告
└─ findings.py          Finding / Severity dataclass
```

- `core/` **不得 import tkinter / customtkinter**。
- 既有 `core/d3d_parser.py`（configparser 版）與 `core/d3d_runner.py`（d_hydro.exe 版）在 P1/P2 完成後由新模組取代；
  `app.py` 的 `on_mdu_select`、`save_scenario` 改用 `MduFile`。確認無其他呼叫者後再刪除舊檔。

### 共用資料結構

```python
# core/findings.py
from dataclasses import dataclass
from enum import Enum

class Severity(str, Enum):
    ERROR = "error"      # 紅燈：不修正就不能執行（或結果必定無效）
    WARNING = "warning"  # 黃燈：可能有問題，需使用者確認
    INFO = "info"        # 資訊

@dataclass
class Finding:
    severity: Severity
    code: str            # 規則代碼，例如 "E01"
    file: str            # 相關檔案（相對 DIMR 資料夾）
    message: str         # 問題描述（zh-TW）
    fix: str = ""        # 建議修正方式（zh-TW）
```

---

## 2. 階段規劃

每個階段都要：程式碼 ＋ 測試（`python -m pytest -q` 全綠）＋ 在 UI 可操作（P1 除外）。
完成一個階段再開始下一個。

---

### P1：模型檔讀寫地基

**任務**
1. `ini_lines.py`：逐行 INI 引擎
   - 讀入時保留每一行原文（含 CRLF / LF、行尾空白、註解）。
   - 行分類：區塊標頭 `[name]`、key-value、註解行（`#` 或 `*` 開頭）、空行、資料行（.bc 的數值列）。
   - 區塊以**清單**保存（允許重名），每個區塊記錄起訖行號。
   - key 比對不分大小寫；取值時去除行尾 `# 註解` 與前後空白。
   - `set_value(section, key, value, occurrence=0)`：只替換該行「值」的部分，
     保留 key 原本的大小寫、`=` 前後對齊空白、行尾註解（若新值較長而擠壓註解，至少保留 1 個空白）。
   - key 不存在時：在該區塊最後一個 key 之後插入新行（格式對齊同區塊其他行）。
   - `save(path)`：未修改的行逐位元組寫回；編碼預設 utf-8，讀取失敗時退回 cp950，並以原編碼寫回。
2. `mdu_file.py`：`MduFile`
   - `get(section, key) -> str | None`、`get_float(...)`、`set(section, key, value)`。
   - `time_window() -> (start: datetime, stop: datetime)`：處理 RefDate、Tunit、TStart/TStop，
     且 `StartDateTime`/`StopDateTime` 存在時優先。
   - 解析路徑：`net_file`、`ext_file_new`、`ext_file_old`、`fou_file`、`structure_file`、`output_dir`（相對 MDU 資料夾轉成絕對路徑）。
3. `ext_file.py`：`ExtFile`
   - `blocks: list[ExtBlock]`（type、key-value、起訖行號、是否被註解停用）。
   - `referenced_files() -> list[(block, key, abs_path)]`（`forcingFile`、`locationFile`、`targetMaskFile`…）。
   - `meteo_blocks()`：quantity、forcingFile、forcingFileType、forcingVariableName。
4. `bc_file.py`：`BcFile`
   - `forcings: list[BcForcing]`（name、function、quantities、units、time_reference、時間值的最小/最大）。
   - 解析 `unit = seconds|minutes|hours|days since YYYY-MM-DD[ HH:MM:SS]` → `time_range() -> (datetime, datetime)`；`function = constant` 回傳 None。
5. `fou_file.py`、`structures_file.py`、`dimr_config.py`（讀＋寫 `<process>`、`<mpiCommunicator>`，寫入時保留其餘 XML 內容與縮排）。
6. `app.py`：`on_mdu_select`、`save_scenario` 改用 `MduFile`；`_post_load_project` 掃描 .mdu 時排除 `_\d{4}\.mdu$`。

**驗收條件（測試）**
- 讀 `fixtures/NWT_KL/NWT_KL_v2.mdu`：`get("time","tstop") == "122400"`（大小寫任意）。
- `set("time","TStop","39600")` 後存檔，與原檔 diff **只有那一行**，且該行的註解與對齊保留；檔頭 `# Generated on` 保留；CRLF 保留。
- 未修改直接存檔 → 與原檔**逐位元組相同**（mdu、ext、bc、structures.ini 都要測）。
- `ExtFile(NWT_KL_bnd.ext)`：2 個 `[Boundary]`、1 個 `[Meteo]`，不丟例外。
- `BcFile(NWT_KL_meteo.bc).forcings[0].time_range() == (2000-01-01 00:00, 2000-01-01 06:00)`。
- `BcFile(NWT_KL_boundaryconditions1d.bc)`：2 個 forcing，function 皆為 constant。
- `FouFile(Maxima_old.fou)` 的 wd 行 tstart=0、tstop=21600；`Maxima.fou` 為 -1/-1。
- `DimrConfig(dimr_config.xml)`：workingDir="dflowfm"、inputFile="NWT_KL.mdu"、processes=[0..7]。
  對一份沒有 `<process>` 的 XML 呼叫 `set_parallel(4)` 後可正確寫入。

---

### P2：分割與執行

**任務**
1. `install.py`
   - 掃描候選路徑（依版本新到舊排序）：
     - `C:\Program Files\Deltares\*\plugins\DeltaShell.Dimr\kernels\x64\bin\run_dimr_parallel.bat`
     - `C:\Program Files\Deltares\*\x64\bin\run_dimr_parallel.bat`
   - `Delft3DInstall` dataclass：`name`、`bin_dir`、`run_dimr_parallel`、`run_dimr`、`run_dflowfm`、`dfmoutput`（可能不存在）。
   - 使用者可手動指定 bin 資料夾，存入 `settings.json`。
2. `settings.py`：`install_bin_dir`、`ndomains`（預設 8）、`map_size_warn_gb`（預設 20）、最近使用的 DIMR 資料夾。
3. `partition.py`
   - 由 `dimr_config.xml` 找到 workingDir 與主 MDU；由 MDU 找 NetFile 基底名。
   - 刪除舊分割檔：`<mdu基底>_\d{4}.mdu`、`<net基底>_\d{4}_net.nc`、`DFM_interpreted_idomain_<net基底>_net.nc`。
   - 執行：`[run_dflowfm_bat, f"--partition:ndomains={n}:icgsolver=6:contiguous=1:seed={seed}", mdu_name]`，
     cwd = dflowfm 資料夾，stdout/stderr 寫入 `partition_log.txt`。
   - 驗證產物數量；失敗時解析 log（見 DOMAIN_NOTES §7 的失敗樣式）給出 zh-TW 錯誤訊息。
   - 成功後寫 `.partition_stamp.json`：`{"ndomains", "seed", "mdu_sha1", "net_sha1_head", "created"}`
     （net 檔很大，只取前 1 MB 的 sha1 ＋檔案大小＋修改時間）。
   - `is_partition_current(dimr_dir, n) -> bool`（給預檢 E07 用）。
4. `dimr_config.py`：執行前自動 `set_parallel(n)`（`n == 1` 時移除 `<process>` 與 `<mpiCommunicator>`）。
5. `runner.py`：`DimrRunner`
   - `start(dimr_dir, install, n)`：
     `subprocess.Popen([run_dimr_parallel_bat, str(n), "dimr_config.xml"], cwd=dimr_dir, env={..., "OMP_NUM_THREADS": "1"}, stdout=PIPE, stderr=STDOUT, creationflags=CREATE_NEW_PROCESS_GROUP)`；
     `n == 1` 改用 `run_dimr.bat dimr_config.xml`。
   - 讀取執行緒：逐行讀 stdout → 寫入 `DIMR\run_logs\run_YYYYMMDD_HHMMSS.log` → 放入 `queue.Queue`。
   - `stop()`：`taskkill /PID <pid> /T /F`。
   - 狀態：`IDLE → STARTING → RUNNING → (FINISHED | FAILED | STOPPED)`；以 callback 或 queue 事件通知 UI。
   - 由輸出判斷成功啟動（`Running parallel with N partitions`）與失敗（`ERROR` 開頭且非白名單，見 DOMAIN_NOTES §8）。
6. UI：`app.py`
   - 旗標拆成 `SHOW_SCENARIO_TAB = False`、`SHOW_RUN_TAB = True`。
   - 分頁「▶️ 執行模擬」版面：
     ```
     ┌ 執行環境 ─────────────────────────────────────────┐
     │ Delft3D 安裝：[下拉：自動偵測結果] [📂 手動指定]      │
     │ DIMR 資料夾：[唯讀路徑] [📂 瀏覽]  核心數：[ 8 ▾]    │
     └──────────────────────────────────────────────────┘
     [🔍 預檢]  [✂️ 分割]  [🔥 開始執行]  [⏹ 停止]        ← 依狀態啟用/停用
     ┌ 預檢結果（P3）────────────────────────────────────┐
     ┌ 進度（P4）：████████░░ 62%  模擬時間 06-05 01:00  剩餘約 1h20m  平均Δt 2.3 s ┐
     ┌ Log（最後 500 行，Consolas，深色底）────────────────┐
     ```
   - DIMR 資料夾預設：目前專案資料夾下尋找 `dimr_config.xml`（深度 ≤ 3，排除 output）；找不到就讓使用者瀏覽。
   - **修正執行緒問題**：UI 更新一律經 `queue.Queue` ＋ `root.after(100, poll)`。
   - Log Textbox 只保留最後 500 行；完整 log 在檔案。

**驗收條件**
- 單元測試：以 fake `run_dflowfm.bat`（寫一個會建立 N×2 個假檔案的 .bat / python 腳本）測分割流程、清舊檔、stamp 寫入、產物驗證失敗訊息。
- 單元測試：`partition_log_failed.txt` 解析後回傳「找不到 MDU（請確認工作目錄）」訊息。
- 單元測試：`DimrRunner` 以 fake 程序（印幾行後結束，或長時間執行）測試狀態轉換、log 檔寫入、`stop()`。
- `@needs_delft3d` 手動測試：實機分割 NWT_KL 並執行 60 秒後按停止，所有 dimr.exe / mpiexec.exe 行程都結束。

---

### P3：預檢（Preflight）

**任務**
- `preflight.py`：`run_preflight(dimr_dir, n, settings) -> list[Finding]`。
- 每條規則一個函式，登錄於清單；單一規則出錯（例外）時轉成 `Finding(ERROR, "X99", ...)`，不中斷其他規則。
- UI：預檢結果以表格呈現（圖示＋代碼＋檔案＋訊息），點選一列在下方顯示「建議修正」。
  有 ERROR 時「開始執行」按鈕停用；提供「我了解風險，仍要執行」勾選框。
- 部分規則提供「一鍵修正」（標示 ✅）：修改前將文字檔備份到 `DIMR\_backup\YYYYMMDD_HHMMSS\`。

**規則表**

| 代碼 | 等級 | 規則 | 一鍵修正 |
|---|---|---|---|
| E01 | ERROR | 每個啟用中 `[Meteo]` 的 NetCDF 時間範圍必須涵蓋模擬時段 [start, stop] | — |
| E02 | ERROR | 每個被引用、`function=timeSeries` 的 `.bc` forcing，時間範圍必須涵蓋模擬時段 | — |
| E03 | ERROR | `.ext` / MDU 引用的每個檔案必須存在（相對 MDU 資料夾解析） | — |
| E04 | ERROR | NetCDF `[Meteo]`：`forcingVariableName` 必須存在於檔案；未指定時需有對應 `standard_name` 的變數 | — |
| E05 | ERROR | `.fou` 每一行的 tstart/tstop 若不為 -1，必須落在模擬時段內 | ✅ 改為 -1 |
| E06 | ERROR | `dimr_config.xml` 的 `<process>` 數量必須等於 N；N>1 時須有 `DFM_COMM_DFMWORLD` | ✅ 自動寫入 |
| E07 | ERROR | 分割檔不存在、數量不等於 N，或 `.partition_stamp.json` 的 mdu_sha1 與目前主 MDU 不符 | ✅ 重新分割 |
| E08 | ERROR | TStop ≤ TStart | — |
| E09 | ERROR | 同一 quantity 的雨量有 2 個以上啟用中的 `[Meteo]`（例如 NetCDF ＋ 零值 meteo.bc 同時存在） | — |
| W01 | WARNING | 預估 map 輸出總大小 > `map_size_warn_gb`（估算方式見下） | — |
| W02 | WARNING | `[Meteo] quantity = rainfall_rate`：提醒單位為 mm/day；若 NetCDF 變數 `units` 含 "mm" 且不含 "day"，升級為 ERROR 語氣的警告（疑似單位錯誤） | — |
| W03 | WARNING | NetCDF 時間 units 帶時區（如 `+0000`）且 MDU `Tzone ≠ 0`：提醒資料將被平移 Tzone 小時 | — |
| W04 | WARNING | `NcFormat = 4`：計算中無法讀取 his/map | ✅ 改為 3 |
| W05 | WARNING | `StatsInterval` 空白或 0：無法顯示進度 | ✅ 設為 60 |
| W06 | WARNING | `HisInterval` 不是 `DtUser` 的整數倍 | — |
| W07 | WARNING | 格網雨量的空間範圍（x/y 或 lon/lat）未完全涵蓋網格範圍（由 net.nc 節點座標 bbox 判斷） | — |
| W08 | WARNING | `FouUpdateStep = 0` 且 `DtUser > 60`：最大值可能低估 | ✅ 改為 1 |
| W09 | WARNING | N 大於實體 P-core 數（或邏輯核心數的一半）時提醒 | — |
| I01 | INFO | 顯示模擬時段（本地時間）、雨量檔時間範圍、預估輸出大小、網格數 | — |
| I02 | INFO | 偵測到 dimr_config 有 D-Flow FM 以外的元件（RTC 等）：本模組不檢查其輸入 | — |
| I03 | INFO | 偵測到舊格式 `ExtForceFile`：本模組不檢查其內容 | — |

**W01 map 大小估算**
```
frames      = floor((stop - start) / MapInterval) + 1
nFaces      = net.nc 的 mesh2d_nFaces（或 nNetElem）維度
nEdges      = net.nc 的 mesh2d_nEdges（或 nNetLink）維度
face_vars   = 依 Wrimap_* 開關計數（s1、ucx/ucy、waterdepth、…），先用保守對照表
edge_vars   = u1、q1 等
bytes       = frames × (face_vars × nFaces + edge_vars × nEdges) × 4（single）或 8（double）
```
對照表放在 `preflight.py` 常數，註明「估算值」。以 fixtures 的 v1 MDU（MapInterval=60）應觸發 W01。

**驗收條件（以 fixtures 組出情境測試）**
- 複製 `NWT_KL_v2.mdu` 到 tmp，以 `MduFile` 改成 TStart=0 / TStop=21600（今天最初的錯誤設定）＋ 雨量 nc → E01。
- 在 tmp 的 `.ext` 加一個引用 `NWT_KL_meteo.bc`（2000 年、rainfall_rate）的 `[Meteo]` 區塊 → E02 ＋ E09。
- `NWT_KL_v1.mdu`（MapInterval=60、NcFormat=3、DtUser=300）→ W01（需 net 維度：測試中以參數注入百萬級的 nFaces、nEdges 取代讀 net.nc）。
- `Maxima_old.fou` ＋ TStart=36000 → E05；一鍵修正後重跑預檢不再出現。
- 無 `<process>` 的 dimr_config ＋ N=8 → E06。
- 無 stamp 檔 → E07。
- `NWT_KL_v2.mdu` ＋ `Maxima.fou`（-1）＋ 正確 dimr_config ＋ 有效 stamp → 無 ERROR。
- 雨量 nc 無 units / standard_name，但 `.ext` 有 `forcingVariableName=rainfall` → E04 不觸發。

---

### P4：監控與結果檢核

**監控（`monitor.py`）**
- 每 10 秒讀取 `output\<mdu基底>_0000.dia` 檔尾（只讀新增的部分，記住 offset）。
- 解析 D-Flow FM 的統計輸出（`StatsInterval` 開啟時）：已模擬時間、剩餘模擬時間、已用實際時間、預估剩餘實際時間、平均時間步長。
  **格式以實機輸出為準**：先在 P4 開始時實際執行一次（StatsInterval=60），把 .dia 片段存成 `fixtures/runs/stats_sample.dia`，再依樣本寫 regex 與測試。
- 事件：
  - 平均 Δt < 0.01 s 連續 3 次 → WARNING「模型可能不穩定」。
  - 出現 `** ERROR` 或 `** FATAL` → ERROR（附該行內容）。
- UI：進度條、模擬時間（本地時間格式）、剩餘時間、平均 Δt。

**結果檢核（`postcheck.py`）**
- 計算結束（FINISHED）後自動執行，也可手動按「🧪 檢核結果」。
- 變數名稱**先以實機 his 檔確認**（`ncdump -h` 或 netCDF4 列出變數，存成 `fixtures/runs/his_header.txt`），名稱對照放常數表；
  找不到時以關鍵字（`rain`、`pump`、`balance`）搜尋並回報 INFO。

| 代碼 | 檢核 | 方法 | 判定 |
|---|---|---|---|
| R01 | 雨量有進模型 | his 各測站 `rain`（mm/day）÷ 24，與輸入格網雨量在測站座標的時雨量比對（最近格點） | 全為 0 → ERROR（無效模擬）；比值偏離 1 超過 ±20% → WARNING |
| R02 | 分割邊界抽水站 | 由 `partition` 或執行 log 解析出「≥2 rank 有連結」的抽水站；his 中其抽水量最大值 ≤ structures.ini 的 capacity × 1.05 | 超過 → WARNING |
| R03 | 質量平衡 | his 的 water balance 相關變數：總入流 − 總出流 − 蓄水變化 | 相對誤差 > 1% → WARNING |
| R04 | fou 輸出 | 各 `_000N_fou.nc` 有 wd / wl 最大值變數且非全為填充值 | 缺漏 → ERROR |
| R05 | 計算完整 | .dia 有正常結束訊息，且最後模擬時間 = TStop | 否 → ERROR |
| R06 | map 合併 | 以 `dfmoutput mapmerge` 合併 map（找不到 dfmoutput 時略過並 INFO） | 失敗 → WARNING |

- 輸出 `output\run_report.json` 與 `run_report.txt`（zh-TW 摘要）：
  模擬設定（時段、N、安裝版本、雨量檔）、執行時間、預檢 findings、檢核 findings、**總判定：有效 / 可疑 / 無效**
  （任一 ERROR → 無效；任一 WARNING → 可疑；否則有效）。

**驗收條件**
- `dimr_run_log.txt` 解析出 8 座邊界抽水站（名稱以本機 fixture 為準）。
- `NWT_KL_0000.dia` 解析出的 total model area、rank 0 flownodes 與檔案記載值一致。
- R01 以合成的小型 his.nc（測試中用 netCDF4 動態建立）測試「全為 0 → ERROR」與「比值正確 → 通過」。

---

### P5：換雨型精靈與批次佇列

**換雨型精靈**（分頁「📝 情境參數設定」改造，不使用 Git 分支）
1. 選擇格網雨量 nc → 顯示時間範圍、空間範圍、變數、是否有 units/standard_name、每小時最大雨量與全域平均歷線（小圖）。
2. 選擇 quantity（預設 `rainfall`，說明與 `rainfall_rate` 的差異）。
3. 自動提議：`RefDate` = 雨量起始日、`TStart`/`TStop` = 雨量時段（可選擇追加退水時間，追加部分需在 nc 補零 → 產生新 nc）、`Tzone = 0`。
4. 預覽將修改的檔案與差異（MDU 的 [time]、`.ext` 的 `[Meteo]`、`.fou` 改 -1、停用其他雨量 `[Meteo]`）。
5. 套用前備份到 `DIMR\_backup\YYYYMMDD_HHMMSS\`，套用後自動跑預檢。

**批次佇列**
- 加入多場事件（每場 = 一個雨量 nc ＋ 選項），依序執行：套用 → 預檢（有 ERROR 則跳過並記錄）→ 分割 → 執行 → 檢核 → 將 `output\` 更名為 `output_<事件名>\`。
- 佇列狀態存 `DIMR\run_queue.json`，程式重開可續跑。
- 全部完成後產生彙總表（每場：判定、執行時間、最大淹水深度統計）。

---

## 3. 非功能需求

- 預檢在 NWT_KL 規模（百萬級網格、25 筆雨量）需在 30 秒內完成（nc 只讀需要的維度與時間軸，不整批載入雨量陣列；W07 只讀 x/y）。
- 所有對使用者的訊息為 zh-TW，並附「建議修正」。
- 任何修改模型檔的動作都要先備份，且只改必要的行。
- 程式不得刪除使用者的輸出資料（`output\`）；批次更名前若目標已存在，改用加時間戳的名稱。
