#!/usr/bin/env python3
"""
타이포 알파 레이어 — 타이포_사양.md 구현
서체 HS봄바람체 2.1 · 흰색 가는 획 · 약한 외부 글로우 · 뒤 배경 20~30% 눌림 · 자간 넉넉
출력: <이름>_alpha.png (투명 레이어, 배경 없음) + <이름>_comp.jpg (플레이트 합성 확인용)
사용: python overlay.py <플레이트> <레이아웃키> <출력이름>
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = next(p for p in [
    os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts/HSBombaram2.1.ttf"),
    "C:/Windows/Fonts/HSBombaram2.1.ttf",
    os.path.expanduser("~/Library/Fonts/HSBombaram2.1.ttf")] if os.path.exists(p))
# 보조 서체: 한글·한자 다 있는 얇은 고딕 (무드보드의 작은 부제 느낌). 맑은 고딕 Semilight
SUB_FONT = next((p for p in ["C:/Windows/Fonts/malgunsl.ttf","C:/Windows/Fonts/malgun.ttf",
                             "/System/Library/Fonts/AppleSDGothicNeo.ttc"] if os.path.exists(p)), FONT)
# 한자용: 第五景 — 맑은 고딕 Semilight 에는 한자가 없어 Noto Serif KR 사용
HANJA_FONT = next((p for p in ["C:/Windows/Fonts/NotoSerifKR-VF.ttf","C:/Windows/Fonts/batang.ttc",
                               "/System/Library/Fonts/AppleSDGothicNeo.ttc"] if os.path.exists(p)), SUB_FONT)

def spaced(draw, xy, text, font, fill, spacing, anchor="la"):
    """자간 넉넉하게 — 글자 하나씩 찍음. anchor: la(좌상) / ma(중앙상) / ra(우상)"""
    widths=[draw.textlength(ch, font=font) for ch in text]
    total=sum(widths)+spacing*(len(text)-1)
    x,y=xy
    if anchor=="ma": x-=total/2
    elif anchor=="ra": x-=total
    for ch,w in zip(text,widths):
        draw.text((x,y), ch, font=font, fill=fill); x+=w+spacing
    return total

# 레이아웃: (텍스트, 크기비율(높이대비), 자간비율, x비율, y비율, anchor, 서체)
LAYOUTS = {
 "S1": [  # 좌 존: 第五景 위에 작게 / 제오경.  우 존: 염원 / 주성의 돛대 / 용두사지 철당간 · 962
   ("第 五 景",   .030, .25, .165, .335, "ma", "hanja"),
   ("제오경",     .085, .35, .165, .385, "ma", "main"),
   ("염원",       .095, .45, .755, .295, "ma", "main"),
   ("주성의 돛대", .062, .22, .755, .445, "ma", "main"),
   ("용두사지 철당간  ·  962", .026, .18, .755, .560, "ma", "sub"),
 ],
 "S12bR": [
   ("돛을 세워라", .075, .30, .50, .375, "ma", "main"),
   ("― 부처가 이르기를", .028, .16, .50, .520, "ma", "sub"),
 ],
}

def render(plate_path, key, out_name, glow=1.0, backing=0.25):
    plate=Image.open(plate_path).convert("RGB"); W,H=plate.size
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    back=Image.new("L",(W,H),0); bd=ImageDraw.Draw(back)
    for text,sz,sp,xr,yr,anc,kind in LAYOUTS[key]:
        font=ImageFont.truetype({"main":FONT,"sub":SUB_FONT,"hanja":HANJA_FONT}[kind], int(H*sz))
        x,y=int(W*xr),int(H*yr)
        tw=spaced(d,(x,y),text,font,(255,255,255,255),int(H*sz*sp),anc)
        # 뒤 눌림 영역(부드러운 사각)
        bx0=x-tw/2 if anc=="ma" else (x-tw if anc=="ra" else x)
        pad=int(H*sz*0.9); bd.rounded_rectangle((bx0-pad,y-pad*0.6,bx0+tw+pad,y+H*sz*1.3+pad*0.6), radius=pad, fill=int(255*backing))
    back=back.filter(ImageFilter.GaussianBlur(H*0.04))
    # 글로우: 글자 알파를 흐려서 아래에 깔기
    a=layer.split()[3]
    glow_a=a.filter(ImageFilter.GaussianBlur(H*0.010)).point(lambda v:int(v*0.28*glow))
    glow_l=Image.merge("RGBA",(Image.new("L",(W,H),235),Image.new("L",(W,H),240),Image.new("L",(W,H),255),glow_a))
    # 알파 레이어 = 눌림(검정) + 글로우 + 글자
    alpha=Image.new("RGBA",(W,H),(0,0,0,0))
    alpha=Image.alpha_composite(alpha, Image.merge("RGBA",(Image.new("L",(W,H),0),)*3+(back,)))
    alpha=Image.alpha_composite(alpha, glow_l)
    alpha=Image.alpha_composite(alpha, layer)
    os.makedirs(os.path.dirname(out_name) or ".", exist_ok=True)
    alpha.save(out_name+"_alpha.png")
    comp=Image.alpha_composite(plate.convert("RGBA"), alpha).convert("RGB")
    comp.save(out_name+"_comp.jpg", quality=92)
    print("→", out_name+"_alpha.png", "/", out_name+"_comp.jpg", (W,H))

if __name__=="__main__":
    render(sys.argv[1], sys.argv[2], sys.argv[3])
