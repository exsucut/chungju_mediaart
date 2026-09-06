#!/bin/bash
# 스토리보드 재빌드 + GitHub 배포
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"

echo "▸ 아티팩트용 보드 재빌드"
python3 "$ROOT/storyboard_v3/build_board.py"

echo "▸ 웹(GitHub Pages)용 보드 재빌드"
python3 "$ROOT/storyboard_v3/build_web.py"

cd ~/Documents/GitHub/chungju_mediaart

if ! git remote get-url origin >/dev/null 2>&1; then
  echo
  echo "⚠ 아직 GitHub 저장소가 연결돼 있지 않습니다."
  echo "  아래를 한 번만 실행한 뒤 이 스크립트를 다시 실행하세요:"
  echo
  echo "    cd \"$ROOT/storyboard_web\""
  echo "    git remote add origin https://github.com/<아이디>/<저장소이름>.git"
  echo "    git branch -M main"
  echo "    git push -u origin main"
  echo
  exit 0
fi

if [ -z "$(git status --porcelain)" ]; then
  echo "▸ 바뀐 내용이 없습니다."
  exit 0
fi

MSG="${1:-스토리보드 갱신 $(date '+%Y-%m-%d %H:%M')}"
git add -A
git -c user.name="jojeong-ung" -c user.email="exsucut@gmail.com" commit -q -m "$MSG"
git push -q origin HEAD
echo "▸ 배포 완료 — $MSG"
URL=$(git remote get-url origin | sed -E 's#.*github.com[:/]([^/]+)/(.+?)(\.git)?$#https://\1.github.io/\2/#')
echo "▸ $URL  (1~2분 뒤 반영)"
