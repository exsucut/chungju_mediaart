#!/usr/bin/env python3
"""
GitHub Pages 용 빌드.
shots.json + images/ -> ../storyboard_web/{index.html, images/}
이미지는 상대 경로로 참조하고, 샷마다 giscus 코멘트 패널을 지연 로딩한다.

사용:  python3 build_web.py
"""
import hashlib, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, "images")
def _find_out():
    """출력 폴더(저장소 루트) 찾기 — 맥/윈도우 공통.
    1) 환경변수 STORYBOARD_OUT  2) 이 스크립트가 속한 git 저장소 루트
    3) 예전 맥 경로 ~/Documents/GitHub/chungju_mediaart"""
    env = os.environ.get("STORYBOARD_OUT")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    try:
        r = subprocess.run(["git", "-C", HERE, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return os.path.abspath(r.stdout.strip())
    except Exception:
        pass
    return os.path.expanduser("~/Documents/GitHub/chungju_mediaart")

OUT  = _find_out()
IMG  = os.path.join(OUT, "images")
MAXW, QUALITY = 1600, 72
LEVEL = {"▁":1,"▂":2,"▃":3,"▄":4,"▅":5,"▆":6,"▇":7,"█":8,"✦":6}

os.makedirs(IMG, exist_ok=True)

# giscus 설정 — storyboard_web/giscus.json 이 있으면 그 값을 쓴다 (재빌드해도 유지됨)
GISCUS = {"repo":"USER/REPO","repoId":"R_xxxxxxxx","category":"General","categoryId":"DIC_xxxxxxxx"}
_gp = os.path.join(OUT, "giscus.json")
if os.path.exists(_gp):
    try: GISCUS.update(json.load(open(_gp, encoding="utf-8")))
    except Exception as e: print("  ! giscus.json 읽기 실패:", e, file=sys.stderr)

def shrink(src, dst, maxw=None, quality=None):
    """긴 변을 maxw 로 줄여 JPEG 저장. Pillow 우선, 없으면 맥 sips. 둘 다 없으면 False."""
    maxw = maxw or MAXW; quality = quality or QUALITY
    try:
        from PIL import Image
        with Image.open(src) as im:
            im = im.convert("RGB")
            w, h = im.size
            if max(w, h) > maxw:
                sc = maxw / max(w, h)
                im = im.resize((max(1, int(w*sc)), max(1, int(h*sc))), Image.LANCZOS)
            # Pillow 의 quality 눈금은 sips 보다 빡빡하다. 같은 화질로 맞추려면 +16
            # (실측: sips 72 ≈ Pillow 88, 같은 원본에서 파일 크기 100% 일치)
            im.save(dst, "JPEG", quality=min(95, quality + 16), optimize=True)
        return True
    except ImportError:
        pass
    except Exception as e:
        print("  ! 축소 실패:", src, e, file=sys.stderr); return False
    if shutil.which("sips"):
        r = subprocess.run(["sips","-s","format","jpeg","-s","formatOptions",str(quality),
                            "-Z",str(maxw),src,"--out",dst],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return r.returncode == 0 and os.path.exists(dst)
    return False

# 어떤 원본에서 구운 결과인지 기록해 둔다. mtime 은 clone 할 때마다 바뀌어서
# (git 은 mtime 을 보존하지 않는다) 기계를 옮길 때마다 83장이 통째로 재인코딩됐다.
# 원본 내용의 해시를 비교하면 같은 그림은 다시 굽지 않는다.
MANIFEST = os.path.join(OUT, ".build_manifest.json")
_man = {}
if os.path.exists(MANIFEST):
    try: _man = json.load(open(MANIFEST, encoding="utf-8"))
    except Exception: _man = {}
_man_new = {}

def _digest(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

def copy_img(name):
    if not name: return None
    src = os.path.join(SRC, name)
    if not os.path.exists(src):
        print("  ! missing:", name, file=sys.stderr); return None
    dst = os.path.join(IMG, name)
    sig = _digest(src)
    _man_new[name] = sig
    if not os.path.exists(dst) or _man.get(name) != sig:
        if not shrink(src, dst): shutil.copy2(src, dst)
    return "images/" + name


# ── 화면 배치 (source/화면_사양_v2.md) ────────────────────────────
# 좌측 스크린이 우측 파사드보다 아래에 있다. 캔버스는 절대 크기가 아니라 비율만 의미가 있다.
GAP      = 200                      # 두 화면 사이 — 실물 철당간이 서는 자리
OFFSET_L = 640                      # 좌측 상단이 우측 상단보다 내려간 양
ALIGN_Y  = 0.62                     # 남는 세로를 위/아래에 나누는 비율 (1.0=아래정렬)
                                    # 0.75 = 위 3/4, 아래 1/4를 버린다 — 좌측 스크린에 건물이 들어오게
SCR = {"L": dict(w=1920, h=960,  x=0,        y=OFFSET_L),
       "R": dict(w=3200, h=1200, x=1920+GAP, y=0)}
CANVAS_W = SCR["R"]["x"] + SCR["R"]["w"]                       # 5320
CANVAS_H = max(SCR["L"]["y"]+SCR["L"]["h"], SCR["R"]["y"]+SCR["R"]["h"])  # 1600
STAGE_W  = 2200                     # 프리뷰 크롭 렌더 폭

def _pct(v, tot): return f"{v/tot*100:.4f}%"

def crop_screens(name):
    """플레이트를 캔버스 폭에 맞춰 아래 정렬로 얹고, 좌/우 스크린 영역을 실제로 잘라 저장.
    반환: {"L": 상대경로, "R": 상대경로, "plate_ar": 플레이트 가로/세로}"""
    from PIL import Image as _I
    src = os.path.join(SRC, name)
    if not os.path.exists(src): return None
    stem = os.path.splitext(name)[0]
    sig  = _man_new.get(name) or _digest(src)
    im = None; out = {}
    for tag in ("L","R"):
        dn  = f"{stem}__{tag}.jpg"
        dst = os.path.join(IMG, dn)
        if not os.path.exists(dst) or _man.get(dn) != sig:
            if im is None: im = _I.open(src).convert("RGB")
            sc  = CANVAS_W / im.width          # 플레이트를 캔버스 폭에 맞춤
            ph  = im.height * sc
            top = -(ph - CANVAS_H) * ALIGN_Y   # 남는 세로를 ALIGN_Y 비율로 위에서 버린다
            r   = SCR[tag]
            box = tuple(int(round(v)) for v in
                        (r["x"]/sc, (r["y"]-top)/sc, (r["x"]+r["w"])/sc, (r["y"]+r["h"]-top)/sc))
            box = (max(0,box[0]), max(0,box[1]), min(im.width,box[2]), min(im.height,box[3]))
            piece = im.crop(box)
            tw = int(STAGE_W * r["w"] / CANVAS_W)
            piece = piece.resize((tw, max(1,int(tw*r["h"]/r["w"]))), _I.LANCZOS)
            piece.save(dst, "JPEG", quality=82, optimize=True)
        _man_new[dn] = sig
        out[tag] = "images/" + dn
    if im is None:
        im = _I.open(src)
    out["plate_ar"] = im.width / im.height
    return out

def stage_html(paths, plate_src):
    """두 화면을 실제 상대 위치로 배치. 클릭하면 그 화면 크롭을 내려받는다."""
    L,R = SCR["L"], SCR["R"]
    return (
      f'<div class="stage" style="aspect-ratio:{CANVAS_W}/{CANVAS_H}">'
      f'<div class="scr sL" style="background-image:url({paths["L"]})">'
      f'<span class="tag">좌측 스크린 · 1920×960</span></div>'
      f'<div class="scr sR" style="background-image:url({paths["R"]})">'
      f'<span class="tag">우측 파사드 · 3200×1200</span></div>'
      f'<span class="pole" title="실물 철당간이 서는 자리"></span>'
      f'</div>')

def plate_html(src, ar):
    """원본 플레이트 + 두 화면이 실제로 쓰는 영역 표시. 클릭하면 원본을 내려받는다."""
    ph  = CANVAS_W / ar                 # 캔버스 폭에 맞췄을 때의 플레이트 높이
    top = -(ph - CANVAS_H) * ALIGN_Y    # 음수면 플레이트 위쪽이 잘림
    def rect(tag, cls):
        r = SCR[tag]
        return (f'<span class="rg {cls}" style="left:{_pct(r["x"],CANVAS_W)};'
                f'top:{_pct(r["y"]-top,ph)};width:{_pct(r["w"],CANVAS_W)};'
                f'height:{_pct(r["h"],ph)}"></span>')
    return (f'<a class="plate" href="{src}" download title="원본 내려받기" '
            f'style="aspect-ratio:{ar:.4f};background-image:url({src})">'
            f'<span class="tag">원본 플레이트 · 클릭하면 내려받기</span>'
            f'{rect("L","rgL")}{rect("R","rgR")}</a>')


_L,_R = SCR["L"], SCR["R"]
_CSSVAL = dict(
  LX=_L["x"]/CANVAS_W*100, LY=_L["y"]/CANVAS_H*100, LW=_L["w"]/CANVAS_W*100, LH=_L["h"]/CANVAS_H*100,
  RX=_R["x"]/CANVAS_W*100, RY=_R["y"]/CANVAS_H*100, RW=_R["w"]/CANVAS_W*100, RH=_R["h"]/CANVAS_H*100,
  PX=(_L["w"]+GAP/2)/CANVAS_W*100)
SCREEN_CSS = """/* -- 화면 배치 프리뷰 -- */
.plate{position:relative;display:block;margin-bottom:10px;background:var(--sunk) center/cover no-repeat;
  border:1px solid var(--line);cursor:pointer;text-decoration:none}
.plate:hover{border-color:var(--accent)}
.rg{position:absolute;border:2px solid;pointer-events:none}
.rgL{border-color:rgba(255,110,110,.9);box-shadow:inset 0 0 0 9999px rgba(255,110,110,.10)}
.rgR{border-color:rgba(90,170,255,.9);box-shadow:inset 0 0 0 9999px rgba(90,170,255,.10)}
.stage{position:relative;width:100%%;background:var(--sunk);margin-bottom:9px}
.stage .scr{position:absolute;display:block;background:var(--sunk) center/cover no-repeat;
  border:1px solid var(--line)}

.sL{left:%(LX).4f%%;top:%(LY).4f%%;width:%(LW).4f%%;height:%(LH).4f%%}
.sR{left:%(RX).4f%%;top:%(RY).4f%%;width:%(RW).4f%%;height:%(RH).4f%%}
.pole{position:absolute;left:%(PX).4f%%;bottom:0;width:0.42%%;height:82%%;z-index:2;
  background:linear-gradient(to top,var(--accent),rgba(214,171,85,.15));opacity:.85}
.ph{display:flex;align-items:center;justify-content:center;aspect-ratio:21/9;
  border:1px dashed var(--line);color:var(--faint);font-size:13px}
""" % _CSSVAL

def esc(s): return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def secs(s):
    m = re.search(r"(\d+)", s or "0"); return int(m.group(1)) if m else 0
def level(t):
    v=[LEVEL[c] for c in (t or "") if c in LEVEL]; return max(v) if v else 1

d = json.load(open(os.path.join(HERE,"shots.json"), encoding="utf-8"))
flat = [(a,s) for a in d["acts"] for s in a["shots"]]
total = sum(secs(s["len"]) for _,s in flat)

# 타임라인
W,H,PAD = 1000,96,5
pts,ticks,x = [],[],0.0
for a,s in flat:
    w=secs(s["len"])/total*W; lv=level(s.get("tone"))
    y=H-16-(lv-1)/7*(H-16-PAD)
    pts.append((x+w/2,y)); ticks.append((x,w,a,s)); x+=w
area="M0,{h} ".format(h=H-14)+" ".join(f"L{px:.1f},{py:.1f}" for px,py in pts)+f" L{W},{H-14} Z"
line="M"+" L".join(f"{px:.1f},{py:.1f}" for px,py in pts)
bars,labels=[],[]
for tx,tw,a,s in ticks:
    pal=a.get("palette",["#888","#888"]); col=pal[1] if len(pal)>1 else pal[0]
    bars.append(f'<a href="#{s["id"]}"><rect x="{tx:.1f}" y="{H-10}" width="{max(tw-1.6,1):.1f}" height="10" '
                f'fill="{col}" opacity=".8"><title>{esc(s["id"])} {esc(s["name"])} · {esc(s["len"])}</title></rect></a>')
    if tw>25: labels.append(f'<text x="{tx+tw/2:.1f}" y="{H-14}" class="tl-lab">{esc(s["id"])}</text>')
timeline=f'''<svg class="tl" viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" aria-label="타임라인과 밝기 곡선">
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#d6ab55" stop-opacity=".3"/><stop offset="1" stop-color="#d6ab55" stop-opacity="0"/>
</linearGradient></defs>
<path d="{area}" fill="url(#g)"/><path d="{line}" class="tl-line"/>{''.join(labels)}{''.join(bars)}</svg>'''

cards=[]
for act in d["acts"]:
    sw="".join(f'<span class="sw" style="background:{c}"></span>' for c in act.get("palette",[]))
    dur=sum(secs(s["len"]) for s in act["shots"])
    cards.append(f'''
<section class="act" id="{act['id']}">
  <div class="act-head">
    <div class="act-id">{esc(act['id'])}</div>
    <div class="act-main"><h2>{esc(act['name'])}</h2>
      <div class="act-meta"><span class="rng">{esc(act['range'])}</span>
      <span class="dur">{dur}초 · {len(act['shots'])}샷</span><span>{esc(act['tone'])}</span></div></div>
    <div class="act-sw">{sw}</div>
  </div>
  <p class="act-note">{esc(act.get('note',''))}</p>
  <div class="shots">''')
    for s in act["shots"]:
        def strip(items, cls):
            if len(items)<2: return ""
            btns=[]
            for i,v in enumerate(items):
                extra=""
                if cls=="P":
                    cs=v.get("crops") or {}
                    extra=(f' data-p="{v["src"]}" data-l="{cs.get("L","")}" '
                           f'data-r="{cs.get("R","")}" data-ar="{cs.get("plate_ar",2.333):.4f}"')
                else:
                    extra=f' data-s="{v["src"]}"'
                btns.append(f'<button class="v{" on" if i==0 else ""}" data-t="{cls}" data-i="{i}"'
                            f'{extra} style="background-image:url({v["src"]})" title="{esc(v["label"])}">'
                            f'<span>{esc(v["label"])}</span></button>')
            return f'<div class="vers" data-for="{cls}"><span class="vlab">버전</span>{"".join(btns)}</div>'
        def load(key):
            out=[]
            for v in (s.get(key) or []):
                src=copy_img(v["f"])
                if not src: continue
                out.append({"src":src,"label":v.get("label") or v["f"], "f":v["f"]})
            return out
        def unified_block(sid, Ps):
            for v in Ps:                       # 버전 전환용으로 전부 미리 크롭
                v["crops"] = crop_screens(v["f"]) or {}
            cs = Ps[0]["crops"]
            if not cs:
                return f'<div class="shotimg" data-shot="{sid}"></div>'
            return (f'<div class="shotimg" data-shot="{sid}">'
                    + plate_html(Ps[0]["src"], cs["plate_ar"])
                    + stage_html(cs, Ps[0]["src"])
                    + strip(Ps,"P")
                    + '<p class="srcnote">좌 1920×960(2:1) · 우 3200×1200(8:3) — 우측이 위, 좌측이 '
                      f'{OFFSET_L}px 아래. 갭 {GAP}px가 실물 철당간 자리. 플레이트를 캔버스 폭에 맞추고 남는 세로를 위 {ALIGN_Y:.0%} / 아래 {1-ALIGN_Y:.0%}로 버림</p></div>')

        def split_block(sid, Ls, Rs):
            l = Ls[0]["src"] if Ls else ""; r = Rs[0]["src"] if Rs else ""
            return (f'<div class="shotimg" data-shot="{sid}" style="--l:url({l});--r:url({r})">'
                    f'<div class="stage" style="aspect-ratio:{CANVAS_W}/{CANVAS_H}">'
                    f'<div class="scr sL" style="background-image:var(--l)">'
                    f'<span class="tag">좌측 스크린 · 1920×960</span></div>'
                    f'<div class="scr sR" style="background-image:var(--r)">'
                    f'<span class="tag">우측 파사드 · 3200×1200</span></div>'
                    f'<span class="pole" title="실물 철당간이 서는 자리"></span></div>'
                    + strip(Ls,"L") + strip(Rs,"R")
                    + '<p class="srcnote">좌·우 별도 생성 — 광원 사양 통일 후 그레이딩으로 톤 일치</p></div>')

        sid = esc(s["id"])
        Ls, Rs = load("variantsL"), load("variantsR")
        Ps = load("variants")
        parts = []
        if Ls or Rs: parts.append(split_block(sid, Ls, Rs))
        if Ps:       parts.append(unified_block(sid + (":U" if parts else ""), Ps))
        media = "".join(parts) or '<figure class="plate"><div class="ph">이미지 없음</div></figure>'
        badge='<span class="b split-b">좌우 분할</span>' if s.get("split") else '<span class="b">무분할</span>'
        cards.append(f'''
    <article class="shot" id="{esc(s['id'])}">
      <div class="shot-head"><span class="sid">{esc(s['id'])}</span><h3>{esc(s['name'])}</h3>
        <span class="tc">{esc(s['tc'])}</span><span class="len">{esc(s['len'])}</span>{badge}</div>
      {media}
      <div class="specs">
        <div><span class="k">레이아웃</span><span class="v2">{esc(s.get('layout',''))}</span></div>
        <div><span class="k">카메라</span><span class="v2">{esc(s.get('cam',''))}</span></div>
        <div><span class="k">톤</span><span class="v2 tonebar">{esc(s.get('tone',''))}</span></div>
      </div>
      <p class="desc">{esc(s.get('desc',''))}</p>
      <p class="trans"><span>다음으로</span>{esc(s.get('trans',''))}</p>
      <section class="cm" data-shot="{esc(s['id'])}">
        <button class="cm-toggle" type="button" aria-expanded="false">
          <span>코멘트</span><span class="cm-count" hidden>0</span>
        </button>
        <div class="cm-body" hidden>
          <ul class="cm-list"><li class="cm-empty">아직 코멘트가 없습니다.</li></ul>
          <form class="cm-form">
            <textarea class="cm-text" rows="2" placeholder="이 샷에 대한 의견" maxlength="1000"></textarea>
            <button class="cm-send" type="submit">남기기</button>
          </form>
          <p class="cm-note" hidden></p>
        </div>
      </section>
    </article>''')
    cards.append("  </div>\n</section>")

nav="".join(f'<a href="#{a["id"]}"><b>{a["id"]}</b>{esc(a["name"])}</a>' for a in d["acts"])

html=f'''<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>염원 — 주성의 돛대 · 스토리보드</title>
<meta name="description" content="2026 청주 국가유산 미디어아트 제오경 스토리보드">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@500;700&family=Noto+Sans+KR:wght@350;400;600&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
:root{{
  --bg:#e9ecef; --panel:#f6f7f9; --sunk:#dde2e8;
  --ink:#161a1f; --dim:#59636f; --faint:#88929e; --line:#ccd4dc;
  --accent:#a97a2c; --iron:#3d4753; --split:#2b6a92;
  --serif:"Noto Serif KR",ui-serif,Georgia,serif;
  --sans:"Noto Sans KR",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  color-scheme: light dark;
}}
@media (prefers-color-scheme:dark){{
  :root{{--bg:#0c0f13;--panel:#151a20;--sunk:#080b0e;--ink:#e6e9ed;--dim:#98a2ae;
    --faint:#6b7683;--line:#242c35;--accent:#d6ab55;--iron:#8996a5;--split:#6fb0dc;}}
}}
*{{box-sizing:border-box}}
html,body{{margin:0}}
body{{background:var(--bg);color:var(--ink);font-family:var(--sans);font-weight:350;
  line-height:1.65;-webkit-font-smoothing:antialiased}}
img{{max-width:100%}}
.wrap{{max-width:1150px;margin:0 auto;padding:0 26px 110px}}
.top{{padding:60px 0 26px}}
.eyebrow{{font-family:var(--mono);font-size:11px;letter-spacing:.16em;color:var(--accent);
  text-transform:uppercase;margin:0 0 14px}}
.top h1{{font-family:var(--serif);font-weight:700;font-size:clamp(30px,4.4vw,46px);
  letter-spacing:-.02em;line-height:1.15;margin:0 0 12px;text-wrap:balance}}
.top .sub{{color:var(--dim);font-size:15px;margin:0 0 22px;max-width:62ch}}
.facts{{display:flex;flex-wrap:wrap;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}
.facts div{{flex:1 1 120px;padding:13px 16px 13px 0;border-right:1px solid var(--line)}}
.facts div:last-child{{border-right:0}}
.facts dt{{font-family:var(--mono);font-size:10px;letter-spacing:.13em;color:var(--faint);
  text-transform:uppercase;margin:0 0 3px}}
.facts dd{{margin:0;font-size:14px;font-weight:600;font-variant-numeric:tabular-nums}}
.howto{{margin:20px 0 0;padding:11px 14px;background:var(--sunk);border-left:2px solid var(--accent);
  font-size:13px;color:var(--dim);max-width:76ch}}
.howto b{{color:var(--ink);font-weight:600}}
.tlwrap{{margin:26px 0 6px}}
.tl-cap{{display:flex;justify-content:space-between;font-family:var(--mono);font-size:10.5px;
  letter-spacing:.1em;color:var(--faint);text-transform:uppercase;margin-bottom:8px}}
.tl{{width:100%;height:96px;display:block}}
.tl-line{{fill:none;stroke:var(--accent);stroke-width:1.8;stroke-linejoin:round;vector-effect:non-scaling-stroke}}
.tl-lab{{font-family:var(--mono);font-size:9px;fill:var(--faint);text-anchor:middle}}
nav{{position:sticky;top:0;z-index:20;display:flex;gap:2px;overflow-x:auto;padding:9px 0;
  margin-bottom:6px;background:var(--bg);border-bottom:1px solid var(--line)}}
nav a{{flex:0 0 auto;color:var(--dim);text-decoration:none;font-size:12.5px;padding:6px 13px;white-space:nowrap}}
nav a b{{font-family:var(--mono);color:var(--accent);margin-right:7px;font-weight:600;font-size:11px}}
nav a:hover{{background:var(--panel);color:var(--ink)}}
.act{{padding-top:52px;scroll-margin-top:56px}}
.act-head{{display:flex;align-items:flex-end;gap:16px;padding-bottom:11px;border-bottom:2px solid var(--ink)}}
.act-id{{font-family:var(--mono);font-size:11px;font-weight:600;color:var(--accent);
  border:1px solid var(--accent);padding:2px 7px;margin-bottom:6px}}
.act-main{{flex:1;min-width:0}}
.act-main h2{{font-family:var(--serif);font-weight:700;margin:0;font-size:25px;letter-spacing:-.015em}}
.act-meta{{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;color:var(--dim);margin-top:3px}}
.act-meta .rng,.act-meta .dur{{font-family:var(--mono);font-variant-numeric:tabular-nums}}
.act-sw{{display:flex;gap:3px;margin-bottom:7px}}
.sw{{width:20px;height:20px;border:1px solid var(--line)}}
.act-note{{font-size:14.5px;color:var(--dim);margin:16px 0 30px;max-width:74ch}}
.shots{{display:flex;flex-direction:column;gap:30px}}
.shot{{background:var(--panel);border:1px solid var(--line);padding:20px;scroll-margin-top:60px}}
.shot-head{{display:flex;align-items:center;gap:11px;flex-wrap:wrap;margin-bottom:16px}}
.sid{{font-family:var(--mono);font-size:11.5px;font-weight:600;color:var(--bg);background:var(--iron);padding:3px 8px}}
.shot-head h3{{font-family:var(--serif);font-weight:500;margin:0;font-size:19px;flex:1;min-width:150px}}
.tc,.len{{font-family:var(--mono);font-size:11.5px;color:var(--dim);font-variant-numeric:tabular-nums}}
.len{{border:1px solid var(--line);padding:2px 6px}}
.b{{font-size:11px;padding:3px 9px;border:1px solid var(--line);color:var(--faint)}}
.b.split-b{{color:var(--split);border-color:var(--split)}}
figure{{margin:0;position:relative}}
.tag{{position:absolute;top:7px;left:7px;z-index:2;font-family:var(--mono);font-size:9.5px;
  letter-spacing:.05em;background:rgba(8,11,14,.68);color:#f2f4f6;padding:3px 7px}}
{SCREEN_CSS}
.vers{{display:flex;align-items:center;gap:6px;margin-top:9px;flex-wrap:wrap}}
.vlab{{font-family:var(--mono);font-size:9.5px;letter-spacing:.12em;color:var(--faint);
  text-transform:uppercase;margin-right:2px}}
button.v{{width:74px;height:42px;padding:0;border:1px solid var(--line);cursor:pointer;
  background-size:cover;background-position:center;position:relative;opacity:.5;transition:opacity .15s}}
button.v:hover{{opacity:.85}}
button.v.on{{opacity:1;border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}}
button.v span{{position:absolute;left:0;right:0;bottom:0;font-family:var(--mono);font-size:8.5px;
  background:rgba(8,11,14,.72);color:#f2f4f6;padding:1px 0;text-align:center}}
.gap{{flex:0 0 30px;align-self:stretch;display:flex;justify-content:center}}
.gap span{{width:2px;background:repeating-linear-gradient(to bottom,var(--line) 0 5px,transparent 5px 11px)}}
.ph{{display:flex;align-items:center;justify-content:center;border:1px dashed var(--line);
  color:var(--faint);font-size:13px}}
.srcnote{{font-family:var(--mono);font-size:10.5px;color:var(--faint);margin:8px 0 0}}
/* 두 안 병기 */
.tracks{{display:flex;flex-direction:column;gap:18px}}
.tk{{border-left:2px solid var(--accent);padding-left:12px}}
.tk.pending{{border-left-color:var(--line)}}
.tk-head{{display:flex;align-items:baseline;gap:9px;margin-bottom:9px}}
.tk-no{{font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.1em;color:var(--bg);
  background:var(--accent);padding:2px 8px}}
.tk.pending .tk-no{{background:var(--faint)}}
.tk-name{{font-family:var(--serif);font-weight:500;font-size:15px;color:var(--ink)}}
.tk.pending .tk-name{{color:var(--dim)}}
.tk.pending .ph{{min-height:0;aspect-ratio:21/9}}
.specs{{display:flex;flex-wrap:wrap;gap:7px;margin:16px 0 12px}}
.specs>div{{display:flex;gap:9px;align-items:baseline;background:var(--sunk);padding:5px 11px}}
.specs .k{{font-family:var(--mono);font-size:10px;letter-spacing:.09em;color:var(--faint);text-transform:uppercase}}
.specs .v2{{font-size:12.5px}}
.tonebar{{font-family:var(--mono);letter-spacing:-1.5px;color:var(--accent);font-size:14px}}
.desc{{font-size:14.5px;margin:0 0 14px;max-width:78ch}}
.trans{{font-size:13.5px;color:var(--dim);margin:0;padding-top:13px;border-top:1px solid var(--line)}}
.trans span{{font-family:var(--mono);font-size:9.5px;letter-spacing:.13em;text-transform:uppercase;
  color:var(--accent);margin-right:11px}}
.cm{{margin-top:14px;border-top:1px solid var(--line);padding-top:12px}}
.cm-toggle{{background:none;border:1px solid var(--line);color:var(--dim);font-family:var(--mono);
  font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;padding:5px 13px;cursor:pointer}}
.cm-toggle:hover{{color:var(--ink);border-color:var(--accent)}}
.cm-toggle{{display:inline-flex;align-items:center;gap:8px}}
.cm-count{{background:var(--accent);color:var(--bg);border-radius:999px;padding:0 6px;
  font-size:10px;font-weight:600;min-width:17px;text-align:center}}
.cm-body{{margin-top:12px;max-width:78ch}}
.cm-list{{list-style:none;margin:0 0 12px;padding:0;display:flex;flex-direction:column;gap:8px}}
.cm-list li{{background:var(--sunk);padding:9px 12px;font-size:13.5px;position:relative}}
.cm-empty{{color:var(--faint);font-style:italic}}
.cm-meta{{display:block;font-family:var(--mono);font-size:10px;letter-spacing:.06em;
  color:var(--faint);margin-bottom:4px;font-variant-numeric:tabular-nums}}
.cm-del{{position:absolute;top:5px;right:7px;background:none;border:0;color:var(--faint);
  font-size:16px;line-height:1;padding:2px 5px;cursor:pointer;opacity:0;transition:opacity .15s}}
.cm-list li:hover .cm-del,.cm-del:focus{{opacity:1}}
.cm-del:hover{{color:#c0483c}}
.cm-form{{display:flex;gap:7px;align-items:flex-start;flex-wrap:wrap}}
.cm-text{{flex:1;min-width:220px;resize:vertical;background:var(--bg);border:1px solid var(--line);
  color:var(--ink);font-family:var(--sans);font-size:13px;padding:7px 9px}}
.cm-text:focus{{outline:none;border-color:var(--accent)}}
.cm-send{{background:var(--accent);color:var(--bg);border:0;font-family:var(--sans);
  font-size:12.5px;font-weight:600;padding:8px 16px;cursor:pointer}}
.cm-send:disabled{{opacity:.45;cursor:default}}
.cm-note{{font-size:12px;color:var(--faint);margin:8px 0 0}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important;animation:none!important}}}}
@media(max-width:760px){{
  .proj{{flex-direction:column;gap:9px;align-items:stretch}} .gap{{display:none}}
  .wrap{{padding:0 15px 80px}} .facts div{{flex-basis:45%}}
}}
</style>
</head><body>
<div class="wrap">
<header class="top">
  <p class="eyebrow">2026 청주 국가유산 미디어아트 · 제오경</p>
  <h1>염원 — 주성의 돛대</h1>
  <p class="sub">용두사지 철당간 설화를 홍수 · 고려의 주조기술 · 철당간의 완성이라는 하나의 수직적 서사로
     재구성한 5분 미디어아트. 좌측 스크린과 우측 건물 파사드, 그리고 그 사이에 실제로 서 있는 국보 철당간을 무대로 삼는다.</p>
  <dl class="facts">
    <div><dt>Duration</dt><dd>5분 00초</dd></div>
    <div><dt>Shots</dt><dd>{len(flat)}샷</dd></div>
    <div><dt>Generations</dt><dd>19블록</dd></div>
    <div><dt>Ratio</dt><dd>21:9 → 16:9 / 4:3</dd></div>
    <div><dt>Version</dt><dd>v3</dd></div>
  </dl>
  <p class="howto">각 샷 카드 아래 <b>코멘트</b> 버튼을 누르면 그 샷 전용 의견창이 열립니다.
     GitHub 계정으로 로그인하면 누구나 남길 수 있고, 본인 글은 직접 수정·삭제할 수 있습니다.</p>
  <div class="tlwrap">
    <div class="tl-cap"><span>0:00 — 5:00 · 밝기 곡선</span><span>막대를 누르면 해당 샷으로</span></div>
    {timeline}
  </div>
</header>
<nav>{nav}</nav>
{''.join(cards)}
</div>
<script>
/* ---- 버전 선택 ---- */
(function(){{
  var KEY='dotdae_sb_pick', saved={{}};
  try{{saved=JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch(e){{}}
  function setBg(el, url){{ if(el&&url){{ el.style.backgroundImage='url('+url+')'; if(el.tagName==='A') el.href=url; }} }}
  function apply(box,type,i,persist){{
    var strip=box.querySelector('.vers[data-for="'+type+'"]'); if(!strip) return;
    var btns=strip.querySelectorAll('button.v'), b=btns[i]; if(!b) return;
    if(type==='P'){{
      var plate=box.querySelector('.plate');
      setBg(plate, b.dataset.p);
      if(plate && b.dataset.ar) plate.style.aspectRatio=b.dataset.ar;
      setBg(box.querySelector('.sL'), b.dataset.l);
      setBg(box.querySelector('.sR'), b.dataset.r);
    }} else {{
      setBg(box.querySelector(type==='L'?'.sL':'.sR'), b.dataset.s);
    }}
    btns.forEach(function(x){{x.classList.remove('on')}});
    b.classList.add('on');
    if(persist){{saved[box.dataset.shot+':'+type]=i;
      try{{localStorage.setItem(KEY,JSON.stringify(saved))}}catch(e){{}}}}
  }}
  document.querySelectorAll('.shotimg').forEach(function(box){{
    ['P','L','R'].forEach(function(t){{
      var k=box.dataset.shot+':'+t; if(saved[k]!=null) apply(box,t,saved[k],false);
    }});
  }});
  document.addEventListener('click',function(e){{
    var b=e.target.closest('button.v'); if(!b) return;
    e.preventDefault();
    apply(b.closest('.shotimg'), b.dataset.t, +b.dataset.i, true);
  }});
}})();
</script>
</body></html>'''

open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(html)
json.dump(_man_new, open(MANIFEST,"w",encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
n=len(os.listdir(IMG))
print(f"built: {OUT}/index.html  ({os.path.getsize(os.path.join(OUT,'index.html'))/1024:.0f} KB, images {n})")
