from comp import *
from theme import *
CW,CH,G=420,400,20; COLS=4
cards=[
 ('NodeMCU v2','ESP8266 · Wi-Fi · micro-USB','×1', lambda cx,cy: nodemcu(cx-64,cy-121,5)[0]),
 ('28BYJ-48 stepper','5 V · 4096 half-steps / rev','×2', lambda cx,cy: stepper(cx+12,cy-5,5)[0]),
 ('ULN2003 driver board','one per motor','×2', lambda cx,cy: uln2003(cx-102,cy-112,6.4)[0]),
 ('6808-2RS bearing','40 × 52 × 7 mm · carries the plate','×1', lambda cx,cy: bearing(cx,cy-5,4.4)),
 ('Disc magnet','Ø5 × 1.5 mm · plate + clamp','×12', lambda cx,cy: ''.join(magnet(cx+dx,cy-20+dy,6) for dx,dy in((-60,0),(0,-20),(60,0),(-30,30),(30,30)))),
 ('Pen refill','Ø3 mm metal ballpoint refill','×1', lambda cx,cy: refill(cx-150,cy-5,4.2)),
 ('USB cable','powers the whole machine','×1', None),
 ('Hardware &amp; wiring','M3 screws · jumper wires','—', None),
]
def usb(cx,cy):
    return (f'<path d="M{cx-150} {cy+40}c80 0 60-80 140-80s80 70 160 70" stroke="#2E2D2A" stroke-width="7" fill="none" stroke-linecap="round"/>'
            f'<rect x="{cx-180}" y="{cy+28}" width="34" height="24" rx="5" fill="#2E2D2A"/><rect x="{cx-200}" y="{cy+33}" width="22" height="14" rx="2" fill="url(#gMetal)" stroke="#141413"/>'
            f'<rect x="{cx+150}" y="{cy+19}" width="30" height="20" rx="5" fill="#2E2D2A"/><rect x="{cx+178}" y="{cy+23}" width="14" height="12" rx="2" fill="url(#gMetal)" stroke="#141413"/>')
def misc(cx,cy):
    o=''
    for i,c in enumerate(['#B8432F','#2E2D2A','#5E8C6A','#4A6FA5']):
        o+=f'<path d="M{cx-120} {cy-40+i*14}c60 0 40 70 110 70s50-60 120-60" stroke="{c}" stroke-width="5" fill="none" stroke-linecap="round"/>'
    for i in range(3):
        x=cx-60+i*60; y=cy+52
        o+=(f'<path d="M{x-14} {y}h28v-6q0-6-6-6h-16q-6 0-6 6z" fill="url(#gMetal)" stroke="#141413" stroke-width="1.2"/><rect x="{x-5}" y="{y}" width="10" height="34" fill="url(#gMetal)" stroke="#141413" stroke-width="1.2"/>'
            +''.join(f'<path d="M{x-5} {y+5+k*6}l10-3" stroke="#8e9298" stroke-width="1.5"/>' for k in range(5)))
    return o
rows=(len(cards)+COLS-1)//COLS
W=COLS*CW+(COLS+1)*G; H=rows*CH+(rows+1)*G+90
o=[f'<rect width="{W}" height="{H}" rx="28" fill="{IVORY}"/>',T(G+8,60,'Bill of materials',30,INK,'start',500,SERIF),
   T(W-G-8,58,'everything runs from one USB port',15,MUTE,'end',500,SANS)]
for i,(name,spec,qty,fn) in enumerate(cards):
    c,r=i%COLS,i//COLS; x=G+c*(CW+G); y=90+G+r*(CH+G)
    o.append(f'<rect x="{x}" y="{y}" width="{CW}" height="{CH}" rx="20" fill="#FFFFFF" stroke="{RULE}"/>')
    o.append(f'<rect x="{x+16}" y="{y+16}" width="{CW-32}" height="{CH-120}" rx="12" fill="{CLOUD}"/>')
    cx,cy=x+CW/2,y+16+(CH-120)/2
    o.append(fn(cx,cy) if fn else (usb(cx,cy) if 'USB' in name else misc(cx,cy)))
    o.append(T(x+22,y+CH-64,name,20,INK,'start',500,SERIF)+T(x+22,y+CH-40,spec,13.5,MUTE,'start',500,SANS))
    o.append(f'<rect x="{x+CW-86}" y="{y+CH-88}" width="64" height="30" rx="15" fill="none" stroke="{CLAY}" stroke-width="1.5"/>'+T(x+CW-54,y+CH-67,qty,15,CLAY,weight=600,font=SANS))
svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><defs>{DEFS}</defs>{"".join(o)}</svg>'
open('out/components.svg','w').write(svg); print(W,H,len(svg)//1024,'KB')
