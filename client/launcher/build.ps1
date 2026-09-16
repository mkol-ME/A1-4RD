# Builds Alfred.exe and puts a copy on the Desktop.
#   powershell -ExecutionPolicy Bypass -File client\launcher\build.ps1
# Rerun it if the project folder moves. The exe is machine-specific (it has
# this checkout's path baked in), so it is built here rather than committed.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$project = (Resolve-Path (Join-Path $here "..\..")).Path
$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) { throw "C# compiler not found at $csc" }

$bin = Join-Path $here "bin"
New-Item -ItemType Directory -Force $bin | Out-Null
$info = Join-Path $bin "BuildInfo.cs"
$escaped = $project.Replace('"', '""')
"static class BuildInfo { public const string ProjectDir = @""$escaped""; }" |
    Out-File -Encoding utf8 $info

$exe = Join-Path $bin "Alfred.exe"
& $csc /nologo /target:exe /optimize /out:$exe (Join-Path $here "Alfred.cs") $info
if ($LASTEXITCODE -ne 0) { throw "compile failed" }

$desktop = [Environment]::GetFolderPath("Desktop")
Copy-Item $exe (Join-Path $desktop "Alfred.exe") -Force
Write-Host "Built $exe"
Write-Host "Copied to $(Join-Path $desktop 'Alfred.exe')"
