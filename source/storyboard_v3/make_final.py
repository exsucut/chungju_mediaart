# -*- coding: utf-8 -*-
"""확정안만 따로 묶는다.

빌드가 `orig/` 에 모든 안을 컷별 폴더 · ASCII 이름으로 깔아 둔다. 거기서
**각 컷의 1번 안(= 확정안)과 바닥 전부**만 골라 `final/` 로 옮긴다.
탈락안 수백 장과 섞이지 않게 하려는 것이다.

    python build_web.py && python make_final.py

만들어지는 것
    final/C01_SQ0_S00_plate_v01.png     한 컷에 한 장 — 평평하게 둔다
    final/C01_SQ0_S00_floor_01.png      바닥은 여러 장일 수 있다
    final/_manifest.csv                 컷 · 종류 · 포맷 · 해상도 · 용량
    final/_README.txt

컷번호(C01–C27)가 앞에 있어 이름순 정렬이 곧 이야기 순서다.
"""
import csv
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_out():
    p = HERE
    for _ in range(4):
        p = os.path.dirname(p)
        if os.path.exists(os.path.join(p, "index.html")):
            return p
    return os.path.dirname(os.path.dirname(HERE))


OUT = _find_out()
ORIG = os.path.join(OUT, "orig")
FINAL = os.path.join(OUT, "final")

# 확정안 = 각 컷의 1번 안. 바닥은 번호와 무관하게 전부 가져간다.
KEEP = re.compile(r"_(?:plate|screenL|screenR)_v01\.|_floor_\d+\.")

README = """Jeogyeong "Yeomwon" - confirmed takes
=====================================

One confirmed plate per cut, plus that cut's floor projection plates.
Rejected alternates are NOT here - they stay in ../orig/.

    C11_SQ1_S05_plate_v01.png
    |   |   |   |     |
    |   |   |   |     v01 = the confirmed take
    |   |   |   kind: plate / floor / screenL / screenR
    |   |   cut id
    |   scene (sequence) number
    cut number in story order, C01 - C27

Sorting by name puts every cut in story order.
PNG files are lossless masters. A few are JPEG because no lossless master
exists for them - see the format column in _manifest.csv.
"""


def main():
    if not os.path.isdir(ORIG):
        print("orig/ 가 없다. build_web.py 를 먼저 돌릴 것.", file=sys.stderr)
        return 1
    if os.path.isdir(FINAL):
        shutil.rmtree(FINAL)
    os.makedirs(FINAL)

    try:
        from PIL import Image
    except ImportError:
        Image = None

    rows, total = [], 0
    for root, _, files in os.walk(ORIG):
        for f in sorted(files):
            if not KEEP.search(f):
                continue
            src = os.path.join(root, f)
            shutil.copy2(src, os.path.join(FINAL, f))
            size = os.path.getsize(src)
            total += size
            res, fmt = "", os.path.splitext(f)[1].lstrip(".").upper()
            if Image:
                try:
                    with Image.open(src) as im:
                        res, fmt = f"{im.width}x{im.height}", im.format
                except Exception:
                    pass
            cut = os.path.basename(root)
            kind = f.replace(cut + "_", "").rsplit(".", 1)[0]
            rows.append([f, cut, kind, fmt, res, f"{size/1024/1024:.2f}"])

    with io.open(os.path.join(FINAL, "_manifest.csv"), "w",
                 encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["filename", "cut", "kind", "format", "resolution", "mb"])
        w.writerows(sorted(rows))
    io.open(os.path.join(FINAL, "_README.txt"), "w", encoding="utf-8").write(README)

    png = sum(1 for r in rows if r[3] == "PNG")
    cuts = len({r[1] for r in rows})
    print(f"final/  {len(rows)}장  {total/1024/1024:.0f} MB  "
          f"({cuts}컷 · PNG 무손실 {png} · JPEG {len(rows)-png})")
    jpg = sorted(r[0] for r in rows if r[3] != "PNG")
    if jpg:
        print("  JPEG 로 남은 것: " + " ".join(jpg))
    print(f"  → {FINAL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
