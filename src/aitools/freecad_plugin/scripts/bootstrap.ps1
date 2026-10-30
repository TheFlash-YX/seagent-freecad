param([string]$Data = (Join-Path $env:LOCALAPPDATA 'SEAgent\FreeCAD'))
$ErrorActionPreference = 'Stop'
if (-not [IO.Path]::IsPathRooted($Data)) { throw '机器目录必须是绝对路径' }
if ($env:PROCESSOR_ARCHITECTURE -ne 'AMD64') { throw '本候选仅Windows x64' }
$Root = Split-Path $PSScriptRoot -Parent
$Lock = Get-Content -LiteralPath (Join-Path $Root 'upstream.lock.json') -Raw | ConvertFrom-Json
$Asset = $Lock.platforms.'Windows-AMD64'.python
New-Item -ItemType Directory -Force -Path (Join-Path $Data 'downloads'),(Join-Path $Data 'runtime') | Out-Null
$Archive = Join-Path $Data 'downloads\python.tar.gz'
if (!(Test-Path -LiteralPath $Archive) -or (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Asset.sha256) {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $Downloaded = $false
  for ($Try = 0; $Try -lt 3; $Try++) {
    try { Invoke-WebRequest -UseBasicParsing -Uri $Asset.url -OutFile "$Archive.part" -TimeoutSec 300; $Downloaded=$true; break } catch { if ($Try -eq 2) { throw 'Python下载失败，请检查网络/代理，然后重新运行；不修改执行策略' } }
  }
  if (!$Downloaded -or (Get-FileHash -LiteralPath "$Archive.part" -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Asset.sha256) { throw 'Python下载SHA256不一致，未执行' }
  Move-Item -LiteralPath "$Archive.part" -Destination $Archive -Force
}
$PythonDir = Join-Path $Data 'runtime\python'
if (!(Test-Path -LiteralPath $PythonDir)) {
  $Stage = Join-Path $Data 'runtime\python.partial'
  if (Test-Path -LiteralPath $Stage) { throw '保留中断python.partial，请检查后处理' }
  New-Item -ItemType Directory -Path $Stage | Out-Null
  $Members = & tar.exe -tzf $Archive
  if ($LASTEXITCODE -ne 0 -or ($Members | Where-Object { $_ -match '^/|(^|/)\.\.(/|$)|^[A-Za-z]:' })) { throw '非法归档路径' }
  & tar.exe -xzf $Archive -C $Stage --strip-components 1
  if ($LASTEXITCODE -ne 0) { throw 'Python解压失败；保留现场' }
  Move-Item -LiteralPath $Stage -Destination $PythonDir
}
& (Join-Path $PythonDir 'python.exe') -X utf8 (Join-Path $PSScriptRoot 'bootstrap.py') --data $Data
if ($LASTEXITCODE -ne 0) { throw '依赖准备失败，按具体错误恢复；未启动FreeCAD' }
