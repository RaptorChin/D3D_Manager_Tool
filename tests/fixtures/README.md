# 測試資料（fixtures）

來源：2026-09-29 一個 1D2D 都市排水模型（模型代號 NWT_KL）執行一場格網雨量事件＋ 8 核心 MPI 的真實檔案。
**這些檔案不進 Git**（GitHub 儲存庫為公開）；換電腦時從 `D3D_run_module_handoff.zip` 解壓到 `tests/fixtures/`，缺檔時相關測試自動略過。
**請勿修改這些檔案。** 測試需要改寫時，先複製到 pytest 的 `tmp_path`。

網格檔 `FlowFM_net.nc`（數百 MB）未收錄；需要網格維度的測試請以參數注入（見 SPEC W01）。

## NWT_KL/（模擬 DIMR 資料夾結構）

| 檔案 | 內容 | 用途 |
|---|---|---|
| `dimr_config.xml` | 已含 `<process>0 1 2 3 4 5 6 7</process>` 與 `DFM_COMM_DFMWORLD`，workingDir=dflowfm | DimrConfig 讀寫、E06（刪掉 process 行做反例） |
| `run_original_wrong.bat` | 原始 run.bat：`run_dimr_parallel.bat -d 0`（**缺核心數**） | 反例參考 |
| `dflowfm/NWT_KL_v1.mdu` | 第一版：TStart=36000、TStop=122400、DtUser=300、**MapInterval=60**、NcFormat=3、FouUpdateStep=0 | W01（map 過大）、W06、W08 |
| `dflowfm/NWT_KL_v2.mdu` | 最終版：DtUser=60、MapInterval=3600、NcFormat=4、FouUpdateStep=0 | 正常案例、逐位元組 round-trip、W04 |
| `dflowfm/NWT_KL_bnd.ext` | 新格式 ext：2×`[Boundary]`（2 個 1D 節點）＋ 1×`[Meteo]`（NetCDF 雨量，forcingVariableName=rainfall） | ExtFile（重複區塊）、E03、E04 |
| `dflowfm/NWT_KL_meteo.bc` | GUI 產生的零值 `rainfall_rate`，時間基準 **2000-01-01**，0～21600 s | E02、E09（加回 ext 做反例） |
| `dflowfm/NWT_KL_boundaryconditions1d.bc` | 2 個 `function = constant` 水位 3.05 m（縮排格式、小寫 `[forcing]`） | BcFile：constant 無時間範圍 |
| `dflowfm/Maxima_old.fou` | wd / wl：tstart=0、tstop=21600 | E05 反例 |
| `dflowfm/Maxima.fou` | wd / wl：-1 / -1 | E05 正常 |
| `dflowfm/structures.ini` | 183 個結構物（pump 118、orifice 57、bridge 6、weir 2），全為定值；含中文名稱 | StructuresFile、編碼、R02 的 capacity |
| `dflowfm/<事件>.nc`（格網雨量，檔名依事件而定） | 格網雨量 NetCDF-4/HDF5；`rainfall(time=25, y, x)`；時間為某日 10:00～次日 10:00（units `minutes since 1970-01-01 00:00:00.0 +0000`）；TWD97 x/y，320 m 網格；**rainfall 無 units、無 standard_name** | nc_inspect、E01、E04、W03、W07、R01 |

> **關於格網雨量 nc**：檔案約 15 MB，依 OVERVIEW 待決事項 D2 **不提交 Git**（`.gitignore` 已排除）。
> 換電腦時需自行放回此位置，來源：`D3D_run_module_handoff.zip`，或原模型的 `DIMR\dflowfm\` 資料夾。
> 檔案不存在時，用到它的測試（nc_inspect、E01、E04、W03、W07、R01 等）會自動略過，不會失敗。

## runs/（log 與診斷檔）

| 檔案 | 內容 | 用途 |
|---|---|---|
| `partition_log_failed.txt` | 在錯誤資料夾（DIMR\ 而非 DIMR\dflowfm\）執行分割：`File not found: 'NWT_KL.mdu'` ＋ `Error: Missing arguments.` ＋ usage | partition log 失敗解析 |
| `dimr_run_log.txt` | 8 核心 DIMR 執行 stdout（初始化到 `Update(86400.0)`）：oneAPI/vars.bat 無害錯誤、`Running parallel with 8 partitions`、每個 rank 的 `nr of structure links`、糙度/入滲缺值警告、人孔底高警告 | runner 啟動判斷、錯誤白名單、R02 邊界抽水站解析（預期 8 座） |
| `NWT_KL_0000_init.dia` | rank 0 的 .dia（初始化階段）：參數回顯含 `Rainfall = 1`、tStart/tStop、網格統計（flownodes、total model area） | .dia 解析、「雨量有掛上」佐證 |

## 待補（P4 開始時由實機產生）

- `runs/stats_sample.dia`：StatsInterval=60 時 .dia 的進度統計片段（monitor 解析用）
- `runs/his_header.txt`：實際 his.nc 的變數清單（`ncdump -h` 或 netCDF4 列出；postcheck 變數名稱對照用）
- `runs/dia_finished_tail.txt`：正常結束時 .dia 最後 100 行（R05 用）
