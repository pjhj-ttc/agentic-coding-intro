# Tip Portal setup check for Windows.
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File .\setup.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Ok($msg)   { Write-Host "  [OK]   $msg" -ForegroundColor Green }
function Fail($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red; exit 1 }

# Remove a .venv that can't be used here. A venv made in WSL/Linux contains symlinks
# that Windows can't resolve, so fall back to rmdir, then to moving it out of the way.
function Remove-OldVenv {
    try { Remove-Item -Recurse -Force ".venv" -ErrorAction Stop; return } catch {}
    try { cmd /c "rmdir /s /q ""$PSScriptRoot\.venv""" 2>$null } catch {}
    if (-not (Test-Path ".venv")) { return }
    $aside = ".venv-old-$(Get-Date -Format yyyyMMdd-HHmmss)"
    try {
        Rename-Item ".venv" $aside -ErrorAction Stop
        Write-Host "  [..]   Could not delete the old .venv, moved it to $aside (safe to delete later)" -ForegroundColor Yellow
        return
    } catch {}
    Fail "Could not remove the old .venv folder. Delete it by hand (File Explorer, or in WSL: rm -rf .venv) and run this script again"
}

Write-Host "`nChecking your machine..." -ForegroundColor Cyan

# The project should live on a local drive: on network or WSL paths (\\...) the
# database can't lock its file, and installs are slow
$onNetworkPath = $PSScriptRoot.StartsWith("\\")
if ($onNetworkPath) {
    Write-Host "  [..]   The project is on a network/WSL path ($PSScriptRoot). It works best on C:, e.g. C:\Users\<you>\course" -ForegroundColor Yellow
}

# git
if (Get-Command git -ErrorAction SilentlyContinue) { Ok (git --version) }
else { Fail "git not found. Install from https://git-scm.com/download/win" }

# git identity (needed to commit)
$gitName = git config user.name
if ($gitName) { Ok "git knows who you are ($gitName)" }
else { Fail "git doesn't know your name yet. Run:  git config --global user.name ""Your Name""  and  git config --global user.email ""you@example.com""" }

# Python 3.11+ (try the py launcher first, then python) and where it lives
$pyExe = $null
foreach ($candidate in @(@("py", "-3"), @("python"))) {
    if (-not (Get-Command $candidate[0] -ErrorAction SilentlyContinue)) { continue }
    $candidateArgs = @($candidate | Select-Object -Skip 1)
    try {
        $info = @(& $candidate[0] @candidateArgs -c "import sys; print('%d.%d' % sys.version_info[:2]); print(sys.executable)" 2>$null)
    } catch { continue }
    if ($info.Count -ge 2 -and [version]$info[0] -ge [version]"3.11") {
        $pyExe = $candidate[0]; $pyArgs = $candidateArgs; $version = $info[0]; $pythonPath = $info[1]
        break
    }
}
if ($pyExe) { Ok "Python $version found: $pythonPath" }
else {
    $stub = Get-Command python -ErrorAction SilentlyContinue
    if ($stub -and $stub.Source -like "*WindowsApps*") {
        Fail "Only the Microsoft Store shortcut for Python was found ($($stub.Source)). Install Python 3.11+ from https://www.python.org/downloads/ (tick 'Add to PATH')"
    }
    Fail "Python 3.11+ not found. Install from https://www.python.org/downloads/ (tick 'Add to PATH')"
}

Write-Host "`nSetting up the project..." -ForegroundColor Cyan

# A Windows virtual environment keeps its Python in .venv\Scripts\python.exe.
# A .venv without it was made elsewhere (e.g. in WSL/Linux or on another machine): rebuild it.
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if ((Test-Path ".venv") -and -not (Test-Path $venvPython)) {
    Write-Host "  [..]   The existing .venv was not made for Windows - rebuilding it" -ForegroundColor Yellow
    Remove-OldVenv
}
if (-not (Test-Path $venvPython)) {
    & $pyExe @pyArgs -m venv .venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPython)) { Fail "Could not create the virtual environment in .venv" }
}
$venvVersion = & $venvPython --version
if ($LASTEXITCODE -ne 0) { Fail "The Python in .venv doesn't work. Delete the .venv folder and run this script again" }
Ok "Virtual environment ready: $venvPython ($venvVersion)"
& $venvPython -m pip install --quiet --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) { Fail "pip install failed" }
Ok "Dependencies installed"

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
Ok ".env present"

$dbHint = "Could not create the database"
if ($onNetworkPath) { $dbHint += ". The project is on a network/WSL path where the database can't lock its file: clone it to C:\Users\<you>\course and run this script there" }
& $venvPython -m flask --app app init-db | Out-Null
if ($LASTEXITCODE -ne 0) { Fail $dbHint }
& $venvPython -m flask --app app seed | Out-Null
if ($LASTEXITCODE -ne 0) { Fail $dbHint }
Ok "Database created with sample tips"

& $venvPython -m pytest -q
if ($LASTEXITCODE -ne 0) { Fail "Tests failed - ask a facilitator" }
Ok "Tests pass"

Write-Host "`nAll good! Start the app with:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\python -m flask --app app run --debug"
Write-Host "then open http://127.0.0.1:5000`n"
