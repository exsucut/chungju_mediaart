# 스토리보드 재빌드 + GitHub 배포 (Windows)
# 맥의 배포.command 와 같은 일을 합니다. 배포.bat 을 더블클릭하면 실행됩니다.
$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue) }
if (-not $py) { Write-Host "! Python 을 찾을 수 없습니다."; Read-Host "엔터를 누르면 닫힘"; exit 1 }
$PY = $py.Source

Write-Host "> 아티팩트용 보드 재빌드"
& $PY "$ROOT\source\storyboard_v3\build_board.py"
if ($LASTEXITCODE -ne 0) { Read-Host "엔터를 누르면 닫힘"; exit 1 }

Write-Host "> 웹(GitHub Pages)용 보드 재빌드"
& $PY "$ROOT\source\storyboard_v3\build_web.py"
if ($LASTEXITCODE -ne 0) { Read-Host "엔터를 누르면 닫힘"; exit 1 }

if (-not (git remote get-url origin 2>$null)) {
  Write-Host ""
  Write-Host "! 아직 GitHub 저장소가 연결돼 있지 않습니다."
  Write-Host "    git remote add origin https://github.com/exsucut/chungju_mediaart.git"
  Read-Host "엔터를 누르면 닫힘"; exit 0
}

if (-not (git status --porcelain)) {
  Write-Host "> 바뀐 내용이 없습니다."
  Read-Host "엔터를 누르면 닫힘"; exit 0
}

$MSG = $args[0]
if (-not $MSG) { $MSG = "스토리보드 갱신 " + (Get-Date -Format "yyyy-MM-dd HH:mm") }

git add -A
git -c user.name="jojeong-ung" -c user.email="exsucut@gmail.com" commit -q -m $MSG
if ($LASTEXITCODE -ne 0) { Write-Host "! 커밋 실패"; Read-Host "엔터를 누르면 닫힘"; exit 1 }
git push -q origin HEAD
if ($LASTEXITCODE -ne 0) { Write-Host "! 푸시 실패"; Read-Host "엔터를 누르면 닫힘"; exit 1 }

Write-Host "> 배포 완료 - $MSG"
Write-Host "> https://exsucut.github.io/chungju_mediaart/  (1~2분 뒤 반영)"
Read-Host "엔터를 누르면 닫힘"
