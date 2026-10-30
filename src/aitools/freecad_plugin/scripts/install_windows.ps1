$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'bootstrap.ps1')
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw '依赖准备失败' }
$Data=Join-Path $env:LOCALAPPDATA 'SEAgent\FreeCAD'
& (Join-Path $Data 'runtime\.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'wizard.py') --data $Data
if ($LASTEXITCODE -ne 0) { throw '安装向导未完成' }
