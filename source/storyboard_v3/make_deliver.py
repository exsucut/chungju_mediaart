# -*- coding: utf-8 -*-
"""구글 드라이브에 올릴 폴더를 만든다 — 원본 그대로, 이름만 ASCII.

보드를 빌드한 뒤 실행한다. index.html 에서 (원본 경로 → 내려받을 이름) 짝을
그대로 읽어 오므로, 보드가 말하는 이름과 드라이브에 올라가는 이름이 절대
어긋나지 않는다.

    python build_web.py && python make_deliver.py

만들어지는 것
    deliver/                     올릴 폴더 — 파일명이 전부 ASCII
    deliver/_manifest.csv        ascii 이름, 원본 이름, 해상도, 용량
"""
import csv
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "images")


def _find_out():
    p = HERE
    for _ in range(4):
        p = os.path.dirname(p)
        if os.path.exists(os.path.join(p, "index.html")):
            return p
    return os.path.dirname(os.path.dirname(HERE))


OUT = _find_out()
DELIVER = os.path.join(OUT, "deliver")

PAIR = re.compile(
    r'(?:href|data-o)="(orig/[^"?]+)[^"]*"[^>]*?(?:download|data-dl)="([^"]+)"'
    r'|(?:data-dl)="([^"]+)"[^>]*?(?:data-o)="(orig/[^"?]+)[^"]*"'
)


def pairs_from_board():
    """index.html 에서 (원본 상대경로, ASCII 파일명) 짝을 전부 거둔다."""
    html = io.open(os.path.join(OUT, "index.html"), encoding="utf-8").read()
    got = {}
    for m in PAIR.finditer(html):
        rel, name = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        if not rel or not name:
            continue
        got.setdefault(name, rel[len("orig/"):])
    return got


def main():
    pairs = pairs_from_board()
    if not pairs:
        print("index.html 에서 원본 링크를 못 찾았다. build_web.py 를 먼저 돌릴 것.",
              file=sys.stderr)
        return 1

    if os.path.isdir(DELIVER):
        shutil.rmtree(DELIVER)
    os.makedirs(DELIVER)

    try:
        from PIL import Image
    except ImportError:
        Image = None

    rows, total, missing = [], 0, []
    for name in sorted(pairs):
        src = os.path.join(SRC, pairs[name].replace("/", os.sep))
        if not os.path.exists(src):
            missing.append(pairs[name])
            continue
        dst = os.path.join(DELIVER, name)
        shutil.copy2(src, dst)
        size = os.path.getsize(dst)
        total += size
        res = ""
        if Image:
            try:
                with Image.open(src) as im:
                    res = f"{im.width}x{im.height}"
            except Exception:
                pass
        rows.append([name, pairs[name], res, f"{size/1024/1024:.2f}"])

    with io.open(os.path.join(DELIVER, "_manifest.csv"), "w",
                 encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["drive_filename", "source_filename", "resolution", "mb"])
        w.writerows(rows)

    print(f"deliver/  {len(rows)}장  {total/1024/1024:.0f} MB")
    if missing:
        print(f"  ! 원본 없음 {len(missing)}건: {missing[:3]}", file=sys.stderr)
    print(f"  → {DELIVER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
