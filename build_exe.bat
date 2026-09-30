@echo off
chcp 65001 > nul
REM ============================================================
REM  打包 D-Flow 模式檔案管理系統 v2.0（Flet 版）成單一執行檔
REM  使用方式：在檔案總管中雙擊此檔案，或在專案資料夾的終端機輸入 build_exe.bat
REM  產出位置：dist\D3D_Manager_Tool.exe（約 95 MB）
REM ============================================================
cd /d "%~dp0"

echo [1/2] 執行測試...
python -m pytest -q
if errorlevel 1 (
    echo.
    echo 測試未通過，已停止打包。請先修正錯誤。
    pause
    exit /b 1
)

echo.
echo [2/2] 打包中（約需 1～2 分鐘）...
flet pack app.py -n D3D_Manager_Tool -i assets/icon.ico --add-data "assets;assets" --hidden-import cftime netCDF4.utils --product-name "D-Flow 模式檔案管理系統" --product-version 2.0.0 --file-version 2.0.0.0 -y
if errorlevel 1 (
    echo.
    echo 打包失敗，請查看上方訊息。
    pause
    exit /b 1
)

echo.
echo 完成！執行檔位置：%~dp0dist\D3D_Manager_Tool.exe
pause
