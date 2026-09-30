@echo off
chcp 65001 > nul
REM ============================================================
REM  打包 D-Flow 模式檔案管理系統 v2.0（Flet 版）
REM  使用方式：在檔案總管中雙擊此檔案，或在專案資料夾的終端機輸入 build_exe.bat
REM  產出位置：dist\D3D_Manager_Tool.exe（約 19 MB，不含畫面引擎）
REM  畫面引擎 dist\flet-windows.zip：升級 Flet 或換圖示時才需要，改用 build_exe.bat --client
REM  詳細說明見 build_exe.py
REM ============================================================
cd /d "%~dp0"

python build_exe.py %*
if errorlevel 1 (
    echo.
    echo 打包失敗，請查看上方訊息。
    pause
    exit /b 1
)
pause
