from common import *
from theme import *
from comp import T
from stl import load
from scene import D
O=(.93,.40,.16); Wt=(.93,.92,.88); K=(.18,.18,.19)
cells=[('base_plate.stl','Base','×1 · orange',O,rot(150,-56),{}),
       ('build_plate.stl','Build plate','×1 · white · ring gear underneath',Wt,rot(150,-120),{}),
       ('paper_clamp.stl','Paper clamp','×1 · black',K,rot(150,-56),{}),
       ('base_gear.stl','Plate pinion','×1 · white · 20 teeth',Wt,rot(150,-56),{}),
       ('linear_gear.stl','Arm pinion','×1 · white · 20 teeth',Wt,rot(150,-56),{}),
       ('linear_rail.stl','Rack arm','×1 · black',K,rot(120,-56),{}),
       ('linear_cap.stl','Lobe cap','×1 · white',Wt,rot(150,-56),{}),
       ('pen_holder_body.stl','Pen holder','×1 · black',K,rot(150,-70),{}),
       ('pen_holder_cap.stl','Pen holder cap','×1 · black',K,rot(150,-56),{})]
COLS=5; CW,CH,G=420,420,24
rows=(len(cells)+COLS-1)//COLS
W=COLS*CW+(COLS+1)*G; H=rows*CH+(rows+1)*G+90
o=[f'<rect width="{W}" height="{H}" rx="28" fill="{IVORY}"/>',T(G+6,62,'Printed parts',32,INK,'start',500,SERIF),
   T(W-G-6,62,'PLA · 0.2 mm layers · STLs in cad/',14,MUTE,'end',400,SANS)]
for i,(fn,name,meta,col,R,_) in enumerate(cells):
    c,r=i%COLS,i//COLS; x=G+c*(CW+G); y=90+G+r*(CH+G)
    body,proj,bb,sc,cc=draw({'p':(load(D+fn),col)},R,CW,CH-120,fill=real_fill,sw=(0.9,1.6),pad=40)
    o.append(f'<rect x="{x}" y="{y}" width="{CW}" height="{CH}" rx="16" fill="#FFFFFF" stroke="{RULE}"/>')
    o.append(f'<g transform="translate({x},{y+10})" fill="none" stroke-linecap="round" stroke-linejoin="round">{body}</g>')
    o.append(T(x+22,y+CH-76,name,21,INK,'start',500,SERIF)+T(x+22,y+CH-50,meta,13.5,SLATE,'start',400,SANS)+T(x+22,y+CH-24,fn,12.5,MUTE,'start',500,MONO))
# tenth cell: what is not printed
x=G+4*(CW+G); y=90+G+(CH+G)
o.append(f'<rect x="{x}" y="{y}" width="{CW}" height="{CH}" rx="16" fill="{CLOUD}"/>'+T(x+22,y+44,'Not printed',21,INK,'start',500,SERIF))
for k,l in enumerate(['NodeMCU v2 (ESP8266)','2 × 28BYJ-48 + ULN2003','6808 bearing (40 × 52 × 7)','12 × magnet Ø5 × 1.5 mm','Ø3 mm pen refill','Screws, jumper wires']):
    o.append(T(x+22,y+86+k*30,'· '+l,15,SLATE,'start',400,SANS))
svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(o)}</svg>'
open('out/printed-parts.svg','w').write(svg); print(len(svg)//1024,'KB')
