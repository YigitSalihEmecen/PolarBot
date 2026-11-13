from common import *
from theme import SERIF,IVORY,MUTE
P=parts()
off=dict(bearing=(0,0,55),plate=(0,0,110),magP=(0,0,128),paper=(0,0,160),clamp=(0,0,190),
         rail=(0,-95,205),cap=(0,-95,255),pen=(0,-95,270))
Q=place(P,off)
R=rot(150,-64)
body,proj,bb,sc,c=draw(Q,R,1500,1700,fill=real_fill,sw=(1.0,1.9))
items=[('Base',(75,10,22),(110,20)),('NodeMCU v2 · ESP8266',(10,-85,8),(150,10)),('ULN2003 driver ×2',(-46.5,22,12),(-120,30)),
       ('Plate motor + pinion',(0,55,31),(-100,40)),('Arm motor + pinion',(-19.9,-99,45),(150,-20)),
       ('6808 bearing',(0,0,87),(-170,-10)),('Build plate · ring gear',(-60,0,144),(-150,10)),('6 × magnet',(70*np.cos(np.radians(-30)),70*np.sin(np.radians(-30)),162),(140,10)),
       ('Paper',(-40,30,194),(-200,0)),('Paper clamp · 6 × magnet',(70,0,226),(140,0)),
       ('Rack arm',(4,-150,250),(150,40)),('Lobe cap',(25,-185,302),(150,-30)),('Pen holder + refill',(0,-95,330),(-140,-40))]
ov=[];legend=[]
for i,(label,pt,(dx,dy)) in enumerate(items,1):
    x,y,_=proj(np.array(pt,float))[0]; bx,by=x+dx,y+dy
    ov.append(f'<path d="M{x:.0f} {y:.0f}L{bx:.0f} {by:.0f}" stroke="{INK}" stroke-width="1.6" stroke-dasharray="2 4"/>'
              f'<circle cx="{x:.0f}" cy="{y:.0f}" r="4" fill="{INK}"/>'+balloon(bx,by,i))
    legend.append((i,label))
x0,y0,x1,y1=bb; m=90
vb=[x0-m-140,y0-m-60,(x1-x0)+2*m+280,(y1-y0)+2*m+60+230]
lx=vb[0]+50; ly=vb[1]+vb[3]-190; cols=3; cw=(vb[2]-100)/cols
leg=''
for k,(i,label) in enumerate(legend):
    cx=lx+(k%cols)*cw; cy=ly+(k//cols)*34
    leg+=balloon(cx+14,cy,i,r=13)+f'<text x="{cx+36:.0f}" y="{cy+5:.0f}" font-family="{SANS}" font-size="17" fill="{INK}">{label}</text>'
title=(f'<text x="{vb[0]+50:.0f}" y="{vb[1]+66:.0f}" font-family="{SERIF}" font-size="34" fill="{INK}">Exploded view</text>'
       f'<text x="{vb[0]+50:.0f}" y="{vb[1]+96:.0f}" font-family="{MONO}" font-size="13" letter-spacing="2" fill="{MUTE}">POLARBOT · 158 × 196 MM · 9 PRINTED PARTS</text>')
open('out/exploded.svg','w').write(svg_wrap(body+''.join(ov)+leg+title,vb,bg=IVORY))
