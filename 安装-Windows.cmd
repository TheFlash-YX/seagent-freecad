@echo off
chcp 65001 >nul
powershell.exe -NoProfile -File "%~dp0src\aitools\freecad_plugin\scripts\install_windows.ps1"
if errorlevel 1 echo 安装未完成。若执行策略阻止，请按公司规定联系IT；不要全局绕过策略。
pause
