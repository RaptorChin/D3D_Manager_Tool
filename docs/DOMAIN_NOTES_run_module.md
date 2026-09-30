# D-Flow FM 領域知識與實務踩坑紀錄

> 來源：2026-09-29 以一個 1D2D 都市排水模型（模型代號 NWT_KL，數百 km²、百萬級網格，Delft3D FM Suite 2026.02 1D2D）
> 執行「一場格網雨量事件」＋ 8 核心 MPI 時的實際排錯過程，以及 D-Flow FM User Manual（2026 版）。
> 規格中的每條預檢規則都對應到本檔的一個真實問題。

---

## 1. 模型資料夾結構（DIMR 匯出格式）

```
<專案>\DIMR\
├─ dimr_config.xml            ← 執行入口；<component><workingDir> 指向 dflowfm
├─ run.bat                    ← 由程式產生／取代
└─ dflowfm\                   ← workingDir；分割與所有模型檔都在這裡
   ├─ NWT_KL.mdu              ← 主 MDU（dimr_config 的 <inputFile>）
   ├─ FlowFM_net.nc           ← 網格（MDU [geometry] NetFile）
   ├─ NWT_KL_bnd.ext          ← 新格式外力檔（MDU [external forcing] ExtForceFileNew）
   ├─ *.bc、Maxima.fou、structures.ini、nodeFile.ini、initialFields.ini …
   ├─ <事件>.nc               ← 格網雨量（.ext 只寫檔名 → 必須與 .ext 同資料夾）
   ├─ NWT_KL_0000.mdu … _0007.mdu        ← 分割產物
   ├─ FlowFM_0000_net.nc … _0007_net.nc  ← 分割產物
   ├─ DFM_interpreted_idomain_FlowFM_net.nc
   └─ output\                 ← MDU [output] OutputDir
      ├─ NWT_KL_0000_his.nc   ← 平行計算時 his 只由 rank 0 輸出，含全部測站
      ├─ NWT_KL_000N_map.nc   ← 每個子域一個 map，需 dfmoutput mapmerge
      ├─ NWT_KL_000N_fou.nc
      └─ NWT_KL_000N.dia
```

- 檔案路徑解析：`PathsRelativeToParent = 0` 時，`.ext` 內的檔名相對於 **MDU 所在資料夾**。
- 掃描 `.mdu` 時要排除分割產物：檔名符合 `_\d{4}\.mdu$`。

## 2. MDU 格式重點

- INI 風格：`[section]`、`Key = value   # comment`。**key 不分大小寫**（GUI 寫 `TStop`、手冊寫 `tStop`）。
- 行尾註解以 `#` 起始；值本身不含 `#`。
- 檔頭有 `# Generated on ...` 註解行，須保留。
- 換行符號為 CRLF，須保留。
- 時間相關（`[time]`）：
  - `RefDate`（yyyymmdd，當日 00:00）、`Tunit`（D/H/M/S）、`TStart`、`TStop`（相對 RefDate，單位 Tunit）
  - 也可能用 `StartDateTime` / `StopDateTime`（yyyymmddhhmmss，會覆蓋 TStart/TStop）→ 解析時要優先採用。
  - `Tzone`：「GMT 的資料來源以 refdat − Tzone×60 分鐘查詢」。模型用台灣時間、資料也是台灣時間 → `Tzone = 0`。
  - `DtUser`：外力更新間隔，也是 his/map 輸出對齊基準；建議 `HisInterval` 為 `DtUser` 的整數倍。
- 輸出（`[output]`）：
  - `HisInterval`、`MapInterval`：可為「interval」或「interval start end」三個數字。
  - `NcFormat`：3 = classic（計算中可被其他程式讀取）、4 = NetCDF4/HDF5（**計算中檔案被鎖，外部讀不到**）。
  - `FouFile`、`FouUpdateStep`（0 = 每 DtUser、1 = 每計算步，最大值較準）。
  - `StatsInterval`：空白則 .dia 不定期輸出進度統計；監控功能需要它（建議 60～300 s）。
  - `Wrimap_*` 開關決定 map 變數數量。
- `[numerics] Icgsolver`：主 MDU 可維持原值（如 4），分割時子 MDU 自動改為 6（PETSc）。
- GUI 會寫入新版核心不認得的 key（`branchfile`、`crossdeffile`、`Wrihis_zcor` …），執行時只產生 WARNING，可忽略。

## 3. 新格式外力檔 `.ext`（fileVersion 2.x）

- INI 風格但**允許重複區塊名稱**，必須以「區塊清單」解析：
  ```ini
  [General]
  fileVersion=2.02
  fileType=extForce

  [Boundary]
  quantity=waterlevelbnd
  nodeId=410
  forcingFile=NWT_KL_boundaryconditions1d.bc

  [Meteo]
  quantity=rainfall
  forcingFile=<事件>.nc
  forcingFileType=netcdf
  forcingVariableName = rainfall
  interpolationMethod=linearSpaceTime
  operand=O
  ```
- 區塊類型：`[Boundary]`、`[Lateral]`、`[Meteo]`（其餘見手冊 C.6.2）。
- 被 `#` 註解掉的整個區塊視為停用。
- 舊格式 `.ext`（MDU `ExtForceFile`，`QUANTITY=`/`FILENAME=`/`FILETYPE=` 連續 key-value）目前不需支援，但偵測到時要給 info。

### 雨量的兩種 quantity（最容易錯）
| quantity | 意義 | 單位 |
|---|---|---|
| `rainfall` | 距上一時間點的**累積量** | mm |
| `rainfall_rate` | 該時間點的**瞬時強度** | **mm/day** |

- 時雨量 nc（每小時累積 mm）→ 用 `rainfall`。誤用 `rainfall_rate` 會少 24 倍。
- NetCDF 以 `standard_name` 辨識變數（`rainfall` ↔ `precipitation_amount`；`rainfall_rate` ↔ `rainfall_rate`），
  或在 `.ext` 用 `forcingVariableName` 指定變數名稱。
- 核心讀到雨量 forcing 後會把 `[external forcing] Rainfall = 1` 寫進 .dia 的參數回顯 → 可作為「雨量有掛上」的佐證。

## 4. `.bc` 檔

```ini
[Forcing]
name                  = global
function              = timeSeries        ← timeSeries 才有時間範圍；constant 與時間無關
timeInterpolation     = linear
quantity              = time
unit                  = seconds since 2000-01-01 00:00:00   ← 時間基準（也可能是 minutes/hours）
quantity              = rainfall_rate
unit                  = mm day-1
0      0
600    0
...
```
- 一個 `.bc` 可有多個 `[Forcing]`（`[forcing]` 大小寫皆可），每個以 `name` 對應 `.ext` 的 nodeId / locationFile 點名。
- 實例：GUI 自動產生的零值 `NWT_KL_meteo.bc` 時間基準是 2000-01-01、長 6 小時；換成 2021 年事件後若仍被 `.ext` 引用 → 時間超出範圍報錯。

## 5. `.fou`（統計輸出）

```
*quantity tstart    tstop     numcyc    knfac     v0plu     layno     param
wd        -1        -1        0         1         0                   max
wl        -1        -1        0         1         0                   max
```
- 以空白分隔，`*` 開頭為註解。tstart/tstop 單位 = MDU 的 Tunit，相對 RefDate；`-1` = 模擬起訖。
- 實例：舊檔寫 `0  21600`，新模擬 36000～122400 → 完全不重疊，最大值圖為空。

## 6. 格網雨量 NetCDF（實例：`<事件>.nc`）

- 格式：NetCDF-4/HDF5（檔頭魔術字 `\x89HDF`），scipy 讀不了，需 netCDF4。
- 維度：`time`=25、`y`=373、`x`=339；變數 `rainfall(time, y, x)` float32、`x`/`y`（TWD97 m，間距 320 m）、`lat`/`lon`、`crs`（EPSG:3826）。
- `time:units = "minutes since 1970-01-01 00:00:00.0 +0000"`；範圍為某日 10:00 ～ 次日 10:00，每小時（25 筆）。
- `rainfall` **沒有 `units`、沒有 `standard_name`**（靠 `forcingVariableName` 才讀得到）。
- 時間標註 `+0000`，但資料內容實際對應台灣時間 → 實務上以「標籤即台灣時間」處理，`Tzone = 0`。
- 空間範圍（TWD97 x/y）必須完全涵蓋模型範圍（預檢 W07）。

## 7. 分割（partition）

- 指令（在 dflowfm 資料夾執行）：
  `"<install>\...\x64\bin\run_dflowfm.bat" "--partition:ndomains=8:icgsolver=6:contiguous=1:seed=1" NWT_KL.mdu`
- 分割會把主 MDU **複製**成 N 份子 MDU → **主 MDU 修改後必須重新分割**，否則子 MDU 還是舊設定。
- `.ext`、`.bc`、nc、`structures.ini` 等其他檔案所有 rank 共用，不需分割。
- 失敗實例：在 `DIMR\`（而非 `DIMR\dflowfm\`）執行 → log 出現
  `** INFO   : File not found: 'NWT_KL.mdu'. Ignoring this commandline argument.` 接著 `Error: Missing arguments.` 與 usage 說明。
- 成功後應產生 N 個 `<mdu>_000X.mdu`、N 個 `<net>_000X_net.nc`、1 個 `DFM_interpreted_idomain_<net>_net.nc`。
- `seed=1` 讓分割結果可重現。

## 8. 平行執行（DIMR + Intel MPI）

- `dimr_config.xml` 的 D-Flow FM `<component>` 內必須有：
  ```xml
  <process>0 1 2 3 4 5 6 7</process>
  <mpiCommunicator>DFM_COMM_DFMWORLD</mpiCommunicator>
  ```
  `<process>` 的編號數量必須等於分割數。`<inputFile>` 維持主 MDU 名稱。`<setting key="threads" value="1"/>` 建議保留。
- 執行：`run_dimr_parallel.bat <N> dimr_config.xml`（**第一個參數必須是行程數**；實例中寫成 `-d 0` 導致失敗），
  工作目錄 = dimr_config.xml 所在資料夾；環境變數 `OMP_NUM_THREADS=1`。
- 安裝路徑實例：
  `C:\Program Files\Deltares\Delft3D FM Suite 2026.02 1D2D\plugins\DeltaShell.Dimr\kernels\x64\bin\`
  內含 `run_dimr_parallel.bat`、`run_dimr.bat`、`run_dflowfm.bat`、`dflowfm-cli.exe`、`dimr.exe`、`mpiexec.exe`、`dfmoutput.exe`（待確認）。
  其他版本可能在 `...\<Suite>\x64\bin\`。
- 啟動時出現以下訊息屬正常，**不影響計算**（mpiexec 仍會成功啟動 N 個行程）：
  - `":: ERROR: This script must be sourced by oneapi-vars.bat."`
  - `"WARNING: File not found: ...\bin\vars.bat"`、`Problems may occur when using IntelMPI`
  - `Cannot find proj.db`（只影響經緯度換算）
- 成功啟動的特徵：`#0: Running parallel with 8 partitions`（每個 rank 一行）、`Modelinit finished`、`NWT_KL.Update(86400.0)`。
- MDU 表頭的 `D-Flow FM Version 1.2.184` 是 GUI 寫入的字串，實際核心版本以安裝資料夾為準。
- 使用者工作站為大小核 CPU，建議只用 P-core 數（8）作為 N。

## 9. 輸出與 log 判讀

- 平行時抽水站的連結分配訊息（每個 rank 各印一次）：
  `** INFO   : <模型>-Pump-A       1 nr of structure links`
  → 同一個 structure 在 ≥2 個 rank 都 > 0 表示落在分割邊界上（實例：8 座抽水站落在分割邊界，其中 5 座在 rank 1/4、3 座在 rank 3/6）。
  需在結果檢核時確認其抽水量未超過 capacity。
  → 所有 rank 皆為 0 表示沒找到連結（錯誤）。
- 初始化警告實例（可接受，但要列出）：
  - `For quantity frictioncoefficient in file frictioncoefficient.xyz no values found for 542 cells/links.`
  - `At node <人孔編號> the bedlevel is below the bedlevel of the assigned storage area.`
- 初始化摘要（.dia）：`nr of flownodes`、`nr of 2D internal flownodes`、`my model area`、`total model area (m2)` 等，可用於估算輸出大小。
- `NcFormat = 4` 時計算中開啟 his.nc 會失敗（HDF5 檔案鎖）；計算結束後即可讀。

## 10. 結構物（structures.ini）

- `fileVersion 3.00`；`[Structure]` 區塊，type 有 pump / orifice / weir / bridge / culvert / generalStructure…
- 參數可能是數值或時間序列檔名（`.bc`/`.tim`）→ 若為檔名需納入時間範圍檢查。
- 實例：183 個結構物（pump 118、orifice 57、bridge 6、weir 2）全為定值。
