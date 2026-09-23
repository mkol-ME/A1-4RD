# Builds Alfred.exe (talk to him) and Alfred Text.exe (type to him), and puts
# copies on the Desktop.
#   powershell -ExecutionPolicy Bypass -File client\launcher\build.ps1
# Rerun it if the project folder moves. The exes are machine-specific (they have
# this checkout's path baked in), so they are built here rather than committed.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$project = (Resolve-Path (Join-Path $here "..\..")).Path
$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) { throw "C# compiler not found at $csc" }

$bin = Join-Path $here "bin"
New-Item -ItemType Directory -Force $bin | Out-Null
$desktop = [Environment]::GetFolderPath("Desktop")
$escaped = $project.Replace('"', '""')

$launchers = @(
    @{ Name = "Alfred";      Script = "client\listen.py"; Title = "Alfred" },
    @{ Name = "Alfred Text"; Script = "client\chat.py";   Title = "Alfred (text)" }
)
foreach ($launcher in $launchers) {
    $info = Join-Path $bin "BuildInfo.$($launcher.Name.Replace(' ', '')).cs"
    "static class BuildInfo { " +
        "public const string ProjectDir = @""$escaped""; " +
        "public const string Script = @""$($launcher.Script)""; " +
        "public const string Title = ""$($launcher.Title)""; }" |
        Out-File -Encoding utf8 $info

    $exe = Join-Path $bin "$($launcher.Name).exe"
    & $csc /nologo /target:exe /optimize "/out:$exe" (Join-Path $here "Alfred.cs") $info
    if ($LASTEXITCODE -ne 0) { throw "compile failed: $($launcher.Name)" }

    # A running Alfred holds its own exe open, so say so rather than dying on a
    # raw IOException. The bin copy above is already the new one.
    try {
        Copy-Item $exe (Join-Path $desktop "$($launcher.Name).exe") -Force
    } catch {
        throw "Built $exe, but could not replace the Desktop copy: $($_.Exception.Message)`nClose that Alfred window if one is open, then run this again."
    }
    Write-Host "Built $exe -> $(Join-Path $desktop "$($launcher.Name).exe")"
}
