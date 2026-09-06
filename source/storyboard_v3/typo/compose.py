#!/usr/bin/env python3
"""
여러 캘리그래피 알파 + 작은 타이핑 부제를 한 플레이트에 배치 → 알파 레이어 + 합성본.
elements: ("calli", 캘리png, cx, cy, w)  /  ("text", 문구, cx, cy, h, kind)   — 모두 플레이트 비율
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
from calli_alpha import to_alpha, trim
from overlay import SUB_FONT, HANJA_FONT, spaced

def compose(plate_path, elements, out, backing=0.22):
    plate=Image.open(plate_path).convert("RGBA"); W,H=plate.size
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    back=Image.new("L",(W,H),0); bd=ImageDraw.Draw(back)
    for el in elements:
        if el[0]=="calli":
            _,path,cx,cy,w=el; c=trim(to_alpha(path)); tw=int(W*w); th=int(c.height*tw/c.width)
            c=c.resize((tw,th),Image.LANCZOS); px,py=int(W*cx-tw/2),int(H*cy-th/2)
            pad=int(th*.5); bd.rounded_rectangle((px-pad,py-pad,px+tw+pad,py+th+pad),radius=pad,fill=int(255*backing))
            layer.alpha_composite(c,(px,py))
        else:
            _,text,cx,cy,h,kind=el; font=ImageFont.truetype(HANJA_FONT if kind=="hanja" else SUB_FONT,int(H*h))
            tw=spaced(d,(int(W*cx),int(H*cy)),text,font,(235,240,255,255),int(H*h*.22),"ma")
            pad=int(H*h*.9); bd.rounded_rectangle((W*cx-tw/2-pad,H*cy-pad*.6,W*cx+tw/2+pad,H*cy+H*h*1.3+pad*.6),radius=pad,fill=int(255*backing))
    back=back.filter(ImageFilter.GaussianBlur(H*.04))
    alpha=Image.merge("RGBA",(Image.new("L",(W,H),0),)*3+(back,)); alpha=Image.alpha_composite(alpha,layer)
    alpha.save(out+"_alpha.png"); Image.alpha_composite(plate,alpha).convert("RGB").save(out+"_comp.jpg",quality=92)
    print("→",out,(W,H))

if __name__=="__main__":
    import json; cfg=json.load(open(sys.argv[1],encoding="utf-8"))
    compose(cfg["plate"],[tuple(e) for e in cfg["elements"]],cfg["out"],cfg.get("backing",.22))
