#!/usr/bin/env python3
"""
생성한 캘리그래피(검정 바탕 흰 글씨) → 알파 레이어 → 플레이트에 얹기.
휘도를 알파로: 검정=투명, 흰=불투명. 글로우·입자도 그대로 알파에 실린다.
사용: python calli_alpha.py <캘리png> <플레이트> <출력이름> [--x 0.5 --y 0.4 --w 0.55 --gamma 1.0 --backing 0.22]
   x,y = 글씨 중심의 플레이트 내 위치(비율), w = 글씨 폭(플레이트 폭 대비)
"""
import sys, os, argparse
from PIL import Image, ImageFilter, ImageOps, ImageChops

def to_alpha(path, gamma=1.0, floor=8):
    im=Image.open(path).convert("RGB")
    lum=ImageOps.grayscale(im)
    # 바닥 노이즈 제거 후 감마
    lum=lum.point(lambda v: 0 if v<floor else int(255*((v-floor)/(255-floor))**gamma))
    rgba=Image.new("RGBA",im.size,(255,255,255,0)); rgba.putalpha(lum)
    return rgba

def trim(rgba, pad=0.06):
    bbox=rgba.split()[3].point(lambda v:255 if v>10 else 0).getbbox()
    if not bbox: return rgba
    x0,y0,x1,y1=bbox; pw=int((x1-x0)*pad); ph=int((y1-y0)*pad)
    return rgba.crop((max(0,x0-pw),max(0,y0-ph),min(rgba.width,x1+pw),min(rgba.height,y1+ph)))

def place(plate_path, calli_rgba, x, y, w, backing, out):
    plate=Image.open(plate_path).convert("RGBA"); W,H=plate.size
    tw=int(W*w); th=int(calli_rgba.height*tw/calli_rgba.width)
    c=calli_rgba.resize((tw,th),Image.LANCZOS)
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    px,py=int(W*x-tw/2),int(H*y-th/2)
    if backing>0:  # 뒤 눌림 (검정 20~30%)
        b=Image.new("L",(W,H),0); from PIL import ImageDraw
        d=ImageDraw.Draw(b); pad=int(th*0.6)
        d.rounded_rectangle((px-pad,py-pad,px+tw+pad,py+th+pad),radius=pad,fill=int(255*backing))
        b=b.filter(ImageFilter.GaussianBlur(H*0.04))
        layer=Image.alpha_composite(layer, Image.merge("RGBA",(Image.new("L",(W,H),0),)*3+(b,)))
    layer.alpha_composite(c,(px,py))
    layer.save(out+"_alpha.png")
    Image.alpha_composite(plate,layer).convert("RGB").save(out+"_comp.jpg",quality=92)
    print("→",out+"_alpha.png / _comp.jpg",(W,H),"글씨",(tw,th),"at",(px,py))

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("calli"); ap.add_argument("plate"); ap.add_argument("out")
    ap.add_argument("--x",type=float,default=.5); ap.add_argument("--y",type=float,default=.4)
    ap.add_argument("--w",type=float,default=.55); ap.add_argument("--gamma",type=float,default=1.0)
    ap.add_argument("--backing",type=float,default=.22); a=ap.parse_args()
    place(a.plate, trim(to_alpha(a.calli,a.gamma)), a.x,a.y,a.w,a.backing,a.out)
