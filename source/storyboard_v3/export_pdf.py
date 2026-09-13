#!/usr/bin/env python3
"""선택한 안을 '한 씬 = 한 페이지' PDF로 출력한다.

    python export_pdf.py
    python export_pdf.py --picks ~/Downloads/picks.json
    python export_pdf.py --only S5,S14,S18 --out 검토본.pdf

각 페이지에 들어가는 것
    1) 캔버스 합성 5320×1600 — 좌/우 스크린 테두리, 갭(실물 당간), 꺾임선 표시
    2) 좌측 스크린 1920×960 과 우측 파사드 3200×1200 의 실제 크롭
    3) 그 컷의 바닥 투사면 1:1
    4) 레이아웃 · 카메라 · 톤 · 설명 · 다음으로

선택(picks.json)은 보드 우하단 「선택 내보내기」 버튼으로 내려받는다.
파일이 없으면 각 컷의 첫 버전(최신 A안)을 쓴다.
"""
import argparse, html, json, os, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, "images")

# build_web.py 와 같은 값이어야 한다
GAP, OFFSET_L, ALIGN_Y = 200, 640, 0.62
SCR = {"L": dict(w=1920, h=960,  x=0,        y=OFFSET_L),
       "R": dict(w=3200, h=1200, x=1920+GAP, y=0)}
CANVAS_W = SCR["R"]["x"] + SCR["R"]["w"]
CANVAS_H = max(SCR["L"]["y"]+SCR["L"]["h"], SCR["R"]["y"]+SCR["R"]["h"])
FOLD_X   = int(SCR["R"]["x"] + SCR["R"]["w"]*0.58)

CHROME = next((p for p in [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome", "/usr/bin/chromium",
] if os.path.exists(p)), None)


def placed(path):
    """플레이트를 캔버스 폭에 맞추고 ALIGN_Y 로 얹은 5320×1600."""
    im = Image.open(path).convert("RGB")
    ph = int(round(im.height * CANVAS_W / im.width))
    im = im.resize((CANVAS_W, ph), Image.LANCZOS)
    c = Image.new("RGB", (CANVAS_W, CANVAS_H), (0, 0, 0))
    c.paste(im, (0, -int(round((ph - CANVAS_H) * ALIGN_Y))))
    return c


def marked(c):
    m = c.copy(); d = ImageDraw.Draw(m)
    for k, col in (("L", (226, 74, 74)), ("R", (74, 142, 226))):
        s = SCR[k]
        d.rectangle([s["x"], s["y"], s["x"]+s["w"]-1, s["y"]+s["h"]-1], outline=col, width=7)
    d.rectangle([SCR["L"]["w"], 0, SCR["R"]["x"], CANVAS_H-1], outline=(232, 196, 42), width=5)
    d.line([FOLD_X, 0, FOLD_X, CANVAS_H], fill=(232, 196, 42), width=5)
    return m


def crop(c, k):
    s = SCR[k]
    return c.crop((s["x"], s["y"], s["x"]+s["w"], s["y"]+s["h"]))


def pick_for(shot, picks):
    vs = shot.get("variants") or []
    if not vs:
        return None, None
    want = picks.get(shot["id"] + ":P")
    if want:
        want = os.path.basename(want.split("?")[0])
        for v in vs:
            if os.path.basename(v["f"]) == want:
                return v["f"], v.get("label")
    return vs[0]["f"], vs[0].get("label")


def esc(x): return html.escape(str(x or ""))


PAGE_CSS = """
@page { size: A4 landscape; margin: 8mm 9mm; }
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Malgun Gothic","Apple SD Gothic Neo",sans-serif;color:#15181c;font-size:8pt;line-height:1.5}
.page{page-break-after:always;height:194mm;display:flex;flex-direction:column}
.page:last-child{page-break-after:auto}
.hd{display:flex;align-items:baseline;gap:4mm;border-bottom:1.6pt solid #15181c;padding-bottom:1.6mm;margin-bottom:2.4mm}
.sid{font-family:"IBM Plex Mono",monospace;font-size:13pt;font-weight:700;letter-spacing:-.3pt}
.nm{font-size:12.5pt;font-weight:700;letter-spacing:-.4pt}
.act{font-size:7.4pt;color:#7b838d}
.tc{margin-left:auto;font-size:7.6pt;color:#4d555f;white-space:nowrap}
.tc b{color:#15181c}
.big{width:100%;border:.5pt solid #c9d0d8;display:block}
.cap{font-size:6.4pt;color:#8a929c;margin:1.1mm 0 2.6mm;display:flex;gap:3mm;flex-wrap:wrap}
.cap i{font-style:normal}
.cap .kL:before,.cap .kR:before,.cap .kG:before{content:"■";margin-right:1mm}
.cap .kL:before{color:#e24a4a}.cap .kR:before{color:#4a8ee2}.cap .kG:before{color:#e8c42a}
.row{display:flex;gap:4mm;align-items:flex-start;margin-bottom:2.6mm}
.cell{display:flex;flex-direction:column;gap:1mm}
.cell img{display:block;border:.5pt solid #c9d0d8}
.cell span{font-size:6.3pt;color:#8a929c;font-family:"IBM Plex Mono",monospace;letter-spacing:.02em}
.spec{margin-top:auto;border-top:.5pt solid #d9dfe5;padding-top:2mm;
  display:grid;grid-template-columns:auto 1fr auto 1fr;gap:.9mm 2.6mm;font-size:7.2pt}
.k{font-family:"IBM Plex Mono",monospace;font-size:6.4pt;color:#8a929c;letter-spacing:.08em;
  text-transform:uppercase;white-space:nowrap;padding-top:.3mm}
.v{color:#2b333c}
.desc{grid-column:2/5}
.ver{font-family:"IBM Plex Mono",monospace;font-size:6.6pt;color:#fff;background:#15181c;
  padding:.4mm 1.6mm;border-radius:1.2mm;white-space:nowrap}
.miss{padding:8mm;background:#f4f5f7;border:.5pt dashed #c9d0d8;color:#8a929c;text-align:center}
"""


def build(shots_json, picks_path, out_pdf, only):
    d = json.load(open(shots_json, encoding="utf-8"))
    picks = {}
    if picks_path and os.path.exists(picks_path):
        raw = json.load(open(picks_path, encoding="utf-8"))
        picks = raw.get("picks", raw)
        print(f"  선택 {len(picks)}건 반영: {picks_path}")
    else:
        print("  선택 파일 없음 — 각 컷의 첫 버전(최신 A안)을 쓴다")

    tmp = tempfile.mkdtemp(prefix="sbpdf_")
    pages, n_img = [], 0
    for act in d["acts"]:
        for s in act["shots"]:
            sid = s["id"]
            if only and sid not in only:
                continue
            f, label = pick_for(s, picks)
            body = ""
            if f and os.path.exists(os.path.join(SRC, f)):
                c = placed(os.path.join(SRC, f))
                names = {}
                for tag, im in (("canvas", marked(c)), ("L", crop(c, "L")), ("R", crop(c, "R"))):
                    nm = f"{sid}_{tag}.jpg"
                    w = 2400 if tag == "canvas" else 1100
                    im.resize((w, max(1, int(im.height * w / im.width))), Image.LANCZOS) \
                      .save(os.path.join(tmp, nm), "JPEG", quality=88, optimize=True)
                    names[tag] = nm
                    n_img += 1
                fl = ""
                for v in (s.get("floor") or [])[:1]:
                    sp = os.path.join(SRC, v["f"])
                    if os.path.exists(sp):
                        nm = f"{sid}_floor.jpg"
                        Image.open(sp).convert("RGB").resize((700, 700), Image.LANCZOS) \
                             .save(os.path.join(tmp, nm), "JPEG", quality=86, optimize=True)
                        fl = (f'<div class="cell"><img src="{nm}" style="width:45mm;height:45mm">'
                              f'<span>바닥 1:1 · {esc(v["label"])}</span></div>')
                body = (
                    f'<img class="big" src="{names["canvas"]}" style="height:83mm;object-fit:fill">'
                    f'<div class="cap"><i class="kL">좌측 스크린 1920×960</i>'
                    f'<i class="kR">우측 파사드 3200×1200</i>'
                    f'<i class="kG">갭 200px = 실물 철당간 / 파사드 꺾임선</i>'
                    f'<i>플레이트 위 {ALIGN_Y:.0%} · 아래 {1-ALIGN_Y:.0%} 로 잘림 (블랙바 영역)</i></div>'
                    f'<div class="row">'
                    f'<div class="cell"><img src="{names["L"]}" style="width:90mm;height:45mm">'
                    f'<span>좌측 스크린 · 2:1</span></div>'
                    f'<div class="cell"><img src="{names["R"]}" style="width:120mm;height:45mm">'
                    f'<span>우측 파사드 · 8:3</span></div>{fl}</div>')
            else:
                body = '<div class="miss">플레이트 없음</div>'

            ver = f'<span class="ver">{esc(label)}</span>' if label else ""
            pages.append(f'''<section class="page">
  <div class="hd"><span class="sid">{esc(sid)}</span><span class="nm">{esc(s.get("name"))}</span>
    <span class="act">{esc(act["id"])} {esc(act["name"])}</span>
    <span class="tc">{esc(s.get("tc"))} · <b>{esc(s.get("len"))}</b> {ver}</span></div>
  {body}
  <div class="spec">
    <span class="k">레이아웃</span><span class="v">{esc(s.get("layout"))}</span>
    <span class="k">카메라</span><span class="v">{esc(s.get("cam"))}</span>
    <span class="k">톤</span><span class="v">{esc(s.get("tone"))}</span>
    <span class="k">다음으로</span><span class="v">{esc(s.get("trans"))}</span>
    <span class="k">설명</span><span class="v desc">{esc(s.get("desc"))}</span>
  </div>
</section>''')

    if not pages:
        sys.exit("출력할 컷이 없다")
    hp = os.path.join(tmp, "book.html")
    open(hp, "w", encoding="utf-8").write(
        f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        f'<title>{esc(d.get("title"))}</title><style>{PAGE_CSS}</style></head>'
        f'<body>{"".join(pages)}</body></html>')

    if not CHROME:
        sys.exit("Chrome/Edge 를 찾지 못했다 — PDF 변환 불가")
    out_pdf = os.path.abspath(out_pdf)
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={out_pdf}", "file:///" + hp.replace("\\", "/")],
                   capture_output=True, timeout=600)
    shutil.rmtree(tmp, ignore_errors=True)
    if not os.path.exists(out_pdf):
        sys.exit("PDF 생성 실패")
    print(f"  {len(pages)}페이지 · 이미지 {n_img}장 → {out_pdf}  ({os.path.getsize(out_pdf)//1024} KB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--picks", default=os.path.join(HERE, "picks.json"))
    ap.add_argument("--out",   default=os.path.join(HERE, "제오경_스토리보드.pdf"))
    ap.add_argument("--only",  default="", help="쉼표로 구분한 컷 id")
    a = ap.parse_args()
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    build(os.path.join(HERE, "shots.json"), a.picks, a.out, only)
