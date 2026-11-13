from comp import *
from theme import *
import numpy as np
# Hand-routed nets; the turn orders noted below keep every wire free of crossings.
W,H=1700,1180
C=dict(v5='#B8432F',gnd='#8A8880',plate='#5E8C6A',arm='#4A6FA5',usb='#87867F')
wires=[];marks=[];text=[]
def route(pts,col,w=3.4,r=12,ends=(True,True)):
    d=f'M{pts[0][0]:.1f} {pts[0][1]:.1f}'
    for i in range(1,len(pts)-1):
        p0,p1,p2=map(np.array,(pts[i-1],pts[i],pts[i+1])); a=p1-p0; b=p2-p1; la,lb=np.hypot(*a),np.hypot(*b)
        if la<1e-6 or lb<1e-6: continue
        rr=min(r,la/2,lb/2); q0=p1-a/la*rr; q1=p1+b/lb*rr
        d+=f'L{q0[0]:.1f} {q0[1]:.1f}Q{p1[0]:.1f} {p1[1]:.1f} {q1[0]:.1f} {q1[1]:.1f}'
    d+=f'L{pts[-1][0]:.1f} {pts[-1][1]:.1f}'
    wires.append(f'<path d="{d}" stroke="{IVORY}" stroke-width="{w+5}" fill="none" stroke-linejoin="round" stroke-linecap="round"/>'
                 f'<path d="{d}" stroke="{col}" stroke-width="{w}" fill="none" stroke-linejoin="round" stroke-linecap="round"/>')
    for p,e in zip((pts[0],pts[-1]),ends):
        if e: marks.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="4" fill="{IVORY}" stroke="{col}" stroke-width="2.2"/>')
def tag(x,y,t,col,anchor='middle'):
    tw=len(t)*7.6+20; x0=x-tw/2 if anchor=='middle' else (x if anchor=='start' else x-tw)
    text.append(f'<rect x="{x0:.0f}" y="{y-11:.0f}" width="{tw:.0f}" height="22" rx="11" fill="#FFFFFF" stroke="{col}" stroke-width="1.2"/>'+T(x0+tw/2,y+4,t,11.5,col,weight=600))
def head(x,y,t,sub=None,anchor='start'):
    s=T(x,y,t,19,INK,anchor,500,SERIF)
    if sub: s+=T(x,y+20,sub,12.5,MUTE,anchor,400,SANS)
    text.append(s)

mcu_s,M=nodemcu(300,360,8)
pd_s,PD=uln2003(720,150,8,power='top')
ad_s,AD=uln2003(720,760,8,power='bottom')
pm_s,PM=stepper(1260,292,7)
am_s,AM=stepper(1260,902,7)
parts=[mcu_s,pd_s,ad_s,pm_s,am_s]

# plate θ: D1 D2 D5 D6 → IN1..IN4, all turning up (upper pins turn first)
for k,(pin,inp) in enumerate((('R2','IN1'),('R3','IN2'),('R8','IN3'),('R9','IN4'))):
    a,b=M[pin],PD[inp]; xt=540+k*15
    route([a,(xt,a[1]),(xt,b[1]),b],C['plate'])
# arm r: D7 RX TX → IN1 IN2 IN4, all turning down (lower pins turn first); D0 → IN3 as a net label
for k,(pin,inp) in enumerate((('R13','IN4'),('R12','IN2'),('R10','IN1'))):
    a,b=AD[inp],M[pin]; xt=540+k*15
    route([b,(xt,b[1]),(xt,a[1]),a],C['arm'])
a=M['R1']; route([a,(a[0]+46,a[1])],C['arm'],ends=(True,False)); tag(a[0]+52,a[1],'D0 → arm IN3',C['arm'],'start')
b=AD['IN3']; route([(b[0]-46,b[1]),b],C['arm'],ends=(False,True)); tag(b[0]-52,b[1],'D0',C['arm'],'end')

# power: VIN rail on the far left feeds the plate driver from the top and the arm driver from below
v=M['L15']; route([v,(230,v[1]),(230,120),(PD['+'][0],120),PD['+']],C['v5'])
route([(230,v[1]),(230,1112),(AD['+'][0],1112),AD['+']],C['v5'],ends=(False,True)); marks.append(f'<circle cx="230" cy="{v[1]:.1f}" r="5" fill="{C["v5"]}"/>')
g=M['L10']; route([g,(262,g[1]),(262,140),(PD['−'][0],140),PD['−']],C['gnd'])
g=M['R14']; route([g,(518,g[1]),(518,1076),(AD['−'][0],1076),AD['−']],C['gnd'])
tag(230,400,'5 V · VIN',C['v5']); tag(262,250,'GND',C['gnd']); tag(518,760,'GND',C['gnd'])

# motors → JST
for D,Mo in ((PD,PM),(AD,AM)):
    for k in range(5):
        a=D[f'M{k+1}']; b=Mo[f'w{k+1}']; xm=(a[0]+b[0])/2
        route([a,(xm,a[1]),(xm,b[1]),b],MOTOR_WIRES[k],w=3,r=8,ends=(False,False))

# USB in
u=(300+12.8*8,360+48.3*8+3.4*8-14)
route([u,(u[0],820)],C['usb'],w=5,ends=(False,False)); tag(u[0],834,'USB · 5 V in',C['usb'])

head(848,470,'Plate driver','ULN2003 · θ axis','middle')
head(848,716,'Arm driver','ULN2003 · r axis','middle')
head(1260,420,'Plate motor','28BYJ-48 · turns the plate','middle')
head(1260,1030,'Arm motor','28BYJ-48 · drives the rack','middle')
head(402,330,'NodeMCU v2','ESP8266 · powered over USB','middle')

lx,ly=1440,520
leg=[('5 V','v5'),('GND','gnd'),('Plate signals','plate'),('Arm signals','arm')]
text.append(f'<rect x="{lx}" y="{ly}" width="230" height="{60+len(leg)*30+40}" rx="14" fill="#FFFFFF" stroke="{RULE}"/>'+T(lx+22,ly+36,'Legend',18,INK,'start',500,SERIF))
for i,(t,k) in enumerate(leg):
    y=ly+70+i*30; text.append(f'<path d="M{lx+22} {y-4}h34" stroke="{C[k]}" stroke-width="3.6" stroke-linecap="round"/>'+T(lx+70,y+1,t,14,INK,'start',400,SANS))
y=ly+70+len(leg)*30
text.append(''.join(f'<path d="M{lx+22+k*7} {y-10}v12" stroke="{c}" stroke-width="3.4" stroke-linecap="round"/>' for k,c in enumerate(MOTOR_WIRES))+T(lx+70,y+1,'Motor lead',14,INK,'start',400,SANS))
text.append(T(40,60,'Wiring diagram',32,INK,'start',500,SERIF)+T(W-40,60,'AccelStepper HALF4WIRE · pins passed as IN1, IN3, IN2, IN4',14,MUTE,'end',400,SANS))
svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><defs>{DEFS}</defs>'
     f'<rect width="{W}" height="{H}" rx="28" fill="{IVORY}"/>{"".join(parts)}{"".join(wires)}{"".join(marks)}{"".join(text)}</svg>')
open('out/wiring.svg','w').write(svg); print(len(svg)//1024,'KB')
