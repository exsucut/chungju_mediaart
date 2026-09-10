#!/usr/bin/env python3
"""
스토리보드 흐름 보드 빌더.  shots.json + images/ -> board.html (단일 파일, 이미지 내장)

샷 추가/수정
  1) images/ 에 이미지를 넣고  2) shots.json 수정  3) python3 build_board.py
  무분할 샷: "img" (21:9 플레이트)  ·  분할 샷: "split": true + "imgL"/"imgR"

무분할 플레이트는 CSS 로 좌 16:9 / 우 4:3 크롭을 자동 생성한다.
  좌 = 플레이트 왼쪽 50% 폭, 세로 중앙 크롭
  우 = 플레이트 오른쪽 50% 폭, 세로 중앙 크롭
타임라인과 톤 곡선은 len·tone 값에서 자동 계산된다.
"""
import base64, json, os, re, shutil, subprocess, sys, tempfile

HERE, IMGDIR = os.path.dirname(os.path.abspath(__file__)), None
IMGDIR = os.path.join(HERE, "images")
MAXW, QUALITY = 1240, 60
LEVEL = {"▁":1,"▂":2,"▃":3,"▄":4,"▅":5,"▆":6,"▇":7,"█":8,"✦":6}

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

def embed(name):
    if not name: return None
    src = os.path.join(IMGDIR, name)
    if not os.path.exists(src):
        print("  ! missing:", name, file=sys.stderr); return None
    tmp = os.path.join(tempfile.gettempdir(), "sb_" + name)
    if os.path.exists(tmp): os.remove(tmp)
    p = tmp if shrink(src, tmp) else src
    return "data:image/jpeg;base64," + base64.b64encode(open(p,"rb").read()).decode()

def esc(s): return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def secs(s):
    m = re.search(r"(\d+)", s or "0"); return int(m.group(1)) if m else 0
def level(t):
    v=[LEVEL[c] for c in (t or "") if c in LEVEL]; return max(v) if v else 1

d = json.load(open(os.path.join(HERE,"shots.json"), encoding="utf-8"))
TRACKS = d.get("tracks") or [{"id":"B","no":"","name":""}]
flat = [(a,s) for a in d["acts"] for s in a["shots"]]
total = sum(secs(s["len"]) for _,s in flat)

# ---- 타임라인 + 밝기 곡선 ----
W,H,PAD = 1000,96,5
pts,ticks,x = [],[],0.0
for a,s in flat:
    dur=secs(s["len"]); w=dur/total*W; lv=level(s.get("tone"))
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
timeline=f'''<svg class="tl" viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" aria-label="18샷 타임라인과 밝기 곡선">
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="var(--accent)" stop-opacity=".3"/>
<stop offset="1" stop-color="var(--accent)" stop-opacity="0"/></linearGradient></defs>
<path d="{area}" fill="url(#g)"/><path d="{line}" class="tl-line"/>{''.join(labels)}{''.join(bars)}</svg>'''

# ---- 본문 ----
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
            if len(items) < 2: return ""
            th = "".join(
                f'<button class="v{" on" if i==0 else ""}" data-t="{cls}" data-i="{i}" '
                f'style="background-image:url({d_["src"]})" title="{esc(d_["label"])}">'
                f'<span>{esc(d_["label"])}</span></button>'
                for i, d_ in enumerate(items))
            return f'<div class="vers" data-for="{cls}"><span class="vlab">버전</span>{th}</div>'

        def load(key, prefix, track="B"):
            out = []
            for i, v in enumerate(s.get(key, []) or []):
                if (v.get("track") or "B") != track: continue
                src = embed(v["f"])
                if not src: continue
                lab = v.get("label") or (v["f"].rsplit("_", 1)[-1].replace(".jpg", ""))
                out.append({"src": src, "label": lab, "file": v["f"]})
            return out

        def media_for(track):
            """한 트랙(안)의 이미지 블록. 그 트랙에 이미지가 없으면 None."""
            sid = esc(s["id"]) + ":" + track
            if s.get("split") and not (load("variantsL","L",track) or load("variantsR","R",track)) and load("variants","P",track):
                pass  # 이 트랙엔 통합 플레이트만 있음 → 아래 통합 렌더로
            elif s.get("split"):
                Ls, Rs = load("variantsL", "L", track), load("variantsR", "R", track)
                if not (Ls or Rs): return None
                lsrc = Ls[0]["src"] if Ls else ""
                rsrc = Rs[0]["src"] if Rs else ""
                split_html = (f'<div class="shotimg" data-shot="{sid}" '
                        f'style="--l:url({lsrc});--r:url({rsrc})">'
                        '<div class="proj"><figure class="scr"><span class="tag">좌측 스크린 · 1920×960</span>'
                        '<div class="fL"></div></figure>'
                        '<div class="gap" title="실물 철당간 · 건물 간극"><span></span></div>'
                        '<figure class="scr"><span class="tag">우측 파사드 · 3200×1200</span>'
                        '<div class="fR"></div></figure></div>'
                        + strip(Ls, "L") + strip(Rs, "R")
                        + '<p class="srcnote">좌·우 별도 클립 생성 — 광원 사양 통일 후 그레이딩으로 톤 일치</p></div>')
                Ps = load("variants", "P", track)
                if not Ps: return split_html
                return split_html + unified_html(sid+":U", Ps)
            Ps = load("variants", "P", track)
            if not Ps: return None
            return unified_html(sid, Ps)

        def unified_html(sid, Ps):
            return (f'<div class="shotimg" data-shot="{sid}" '
                    f'style="--src:url({Ps[0]["src"]})">'
                    '<figure class="plate"><span class="tag">원본 플레이트 · 21:9</span><div class="fP"></div></figure>'
                    '<div class="proj"><figure class="scr"><span class="tag">좌측 스크린 · 1920×960</span>'
                    '<div class="cL"></div></figure>'
                    '<div class="gap" title="실물 철당간 · 건물 간극"><span></span></div>'
                    '<figure class="scr"><span class="tag">우측 파사드 · 3200×1200</span>'
                    '<div class="cR"></div></figure></div>'
                    + strip(Ps, "P")
                    + '<p class="srcnote">21:9 단일 생성 — 좌 50% / 우 50%, 두 면의 <b>아래를 같은 지면선에 맞춰</b> 크롭 (우측 파사드가 더 높음)</p></div>')

        blocks = []
        for tk in TRACKS:
            inner = media_for(tk["id"])
            pend = "" if inner else " pending"
            if not inner:
                inner = ('<figure class="plate"><div class="fP ph">'
                         + esc(tk["no"]) + ' 생성 예정</div></figure>')
            blocks.append(
                f'<div class="tk{pend}" data-track="{esc(tk["id"])}">'
                f'<div class="tk-head"><span class="tk-no">{esc(tk["no"])}</span>'
                f'<span class="tk-name">{esc(tk["name"])}</span></div>{inner}</div>')
        media = '<div class="tracks">' + "".join(blocks) + '</div>'
        badge = '<span class="b split-b">좌우 분할</span>' if s.get("split") else '<span class="b">무분할</span>'
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
    </article>''')
    cards.append("  </div>\n</section>")

nav="".join(f'<a href="#{a["id"]}"><b>{a["id"]}</b>{esc(a["name"])}</a>' for a in d["acts"])

html=f'''<title>주성의 돛대</title>
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
}}
@media (prefers-color-scheme:dark){{
  :root:not([data-theme="light"]){{
    --bg:#0c0f13; --panel:#151a20; --sunk:#080b0e;
    --ink:#e6e9ed; --dim:#98a2ae; --faint:#6b7683; --line:#242c35;
    --accent:#d6ab55; --iron:#8996a5; --split:#6fb0dc;
  }}
}}
:root[data-theme="dark"]{{
  --bg:#0c0f13; --panel:#151a20; --sunk:#080b0e;
  --ink:#e6e9ed; --dim:#98a2ae; --faint:#6b7683; --line:#242c35;
  --accent:#d6ab55; --iron:#8996a5; --split:#6fb0dc;
}}
*{{box-sizing:border-box}}
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
.tl a rect:hover{{opacity:1}}
nav{{position:sticky;top:0;z-index:20;display:flex;gap:2px;overflow-x:auto;padding:9px 0;
  margin-bottom:6px;background:var(--bg);border-bottom:1px solid var(--line)}}
nav a{{flex:0 0 auto;color:var(--dim);text-decoration:none;font-size:12.5px;padding:6px 13px;white-space:nowrap}}
nav a b{{font-family:var(--mono);color:var(--accent);margin-right:7px;font-weight:600;font-size:11px}}
nav a:hover{{background:var(--panel);color:var(--ink)}}
nav a:focus-visible,.tl a:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
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
.shot-head h3{{font-family:var(--serif);font-weight:500;margin:0;font-size:19px;flex:1;min-width:150px;letter-spacing:-.01em}}
.tc,.len{{font-family:var(--mono);font-size:11.5px;color:var(--dim);font-variant-numeric:tabular-nums}}
.len{{border:1px solid var(--line);padding:2px 6px}}
.b{{font-size:11px;padding:3px 9px;border:1px solid var(--line);color:var(--faint)}}
.b.split-b{{color:var(--split);border-color:var(--split)}}
figure{{margin:0;position:relative}}
.tag{{position:absolute;top:7px;left:7px;z-index:2;font-family:var(--mono);font-size:9.5px;
  letter-spacing:.05em;background:rgba(8,11,14,.68);color:#f2f4f6;padding:3px 7px}}
/* 원본 21:9 플레이트 */
.plate{{margin-bottom:9px}}
.fP{{aspect-ratio:21/9;background:var(--sunk) center/cover no-repeat;background-image:var(--src)}}
/* 실제 투사 프레임 */
.proj{{display:flex;align-items:flex-end}}
.scr{{flex:1;min-width:0}}
.cL,.fL{{aspect-ratio:2/1;background:var(--sunk) no-repeat}}
.cR,.fR{{aspect-ratio:8/3;background:var(--sunk) no-repeat}}
.cL{{background-image:var(--src);background-size:266.667% auto;background-position:left bottom}}
.cR{{background-image:var(--src);background-size:160% auto;background-position:right bottom}}
.fL{{background-image:var(--l);background-size:cover;background-position:center}}
.fR{{background-image:var(--r);background-size:cover;background-position:center}}
.vers{{display:flex;align-items:center;gap:6px;margin-top:9px;flex-wrap:wrap}}
.vlab{{font-family:var(--mono);font-size:9.5px;letter-spacing:.12em;color:var(--faint);
  text-transform:uppercase;margin-right:2px}}
button.v{{width:74px;height:42px;padding:0;border:1px solid var(--line);cursor:pointer;
  background-size:cover;background-position:center;position:relative;opacity:.5;
  transition:opacity .15s,border-color .15s}}
button.v:hover{{opacity:.85}}
button.v.on{{opacity:1;border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}}
button.v span{{position:absolute;left:0;right:0;bottom:0;font-family:var(--mono);font-size:8.5px;
  background:rgba(8,11,14,.72);color:#f2f4f6;padding:1px 0;text-align:center}}
button.v:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
.gap{{flex:0 0 30px;align-self:stretch;display:flex;justify-content:center}}
.gap span{{width:2px;background:repeating-linear-gradient(to bottom,var(--line) 0 5px,transparent 5px 11px)}}
.ph{{display:flex;align-items:center;justify-content:center;border:1px dashed var(--line);
  color:var(--faint);font-size:13px}}
.srcnote{{font-family:var(--mono);font-size:10.5px;color:var(--faint);margin:8px 0 0;letter-spacing:.02em}}
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
@media (prefers-reduced-motion:reduce){{*{{transition:none!important;animation:none!important}}}}
@media(max-width:760px){{
  .proj{{flex-direction:column;gap:9px;align-items:stretch}} .gap{{display:none}}
  .wrap{{padding:0 15px 80px}} .facts div{{flex-basis:45%}}
}}
</style>
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
  <p class="howto">의견은 이 페이지의 <b>코멘트</b> 기능으로 남겨 주세요 — 해당 이미지나 문장을 드래그해 선택하면 그 자리에 스레드가 붙습니다. 작성자가 직접 수정·삭제할 수 있고, 답글도 이어집니다. 샷 번호(S5, S8b …)를 함께 적어 주시면 정리가 빠릅니다.</p>
  <div class="tlwrap">
    <div class="tl-cap"><span>0:00 — 5:00 · 밝기 곡선</span><span>막대를 누르면 해당 샷으로</span></div>
    {timeline}
  </div>
</header>
<nav>{nav}</nav>
{''.join(cards)}
</div>
<script>
(function(){{
  var KEY='dotdae_sb_pick';
  var saved={{}}; try{{saved=JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch(e){{}}
  function apply(box,type,i,persist){{
    var strip=box.querySelector('.vers[data-for="'+type+'"]');
    if(!strip) return;
    var b=strip.querySelectorAll('button.v')[i]; if(!b) return;
    var url=b.style.backgroundImage;
    box.style.setProperty(type==='P'?'--src':(type==='L'?'--l':'--r'), url);
    strip.querySelectorAll('button.v').forEach(function(x){{x.classList.remove('on')}});
    b.classList.add('on');
    if(persist){{
      saved[box.dataset.shot+':'+type]=i;
      try{{localStorage.setItem(KEY,JSON.stringify(saved))}}catch(e){{}}
    }}
  }}
  document.querySelectorAll('.shotimg').forEach(function(box){{
    ['P','L','R'].forEach(function(t){{
      var k=box.dataset.shot+':'+t;
      if(saved[k]!=null) apply(box,t,saved[k],false);
    }});
  }});
  document.addEventListener('click',function(e){{
    var b=e.target.closest('button.v'); if(!b) return;
    apply(b.closest('.shotimg'), b.dataset.t, +b.dataset.i, true);
  }});
}})();


</script>'''
out=os.path.join(HERE,"board.html")
open(out,"w",encoding="utf-8").write(html)
print("built:",out,f"{os.path.getsize(out)/1024/1024:.2f} MB")
