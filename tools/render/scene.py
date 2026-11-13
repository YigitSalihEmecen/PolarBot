import os
import numpy as np
from stl import load
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','cad','')

def box(c,s):
    c=np.array(c,float); h=np.array(s,float)/2
    v=np.array([[x,y,z] for x in(-1,1) for y in(-1,1) for z in(-1,1)])*h+c
    f=[(0,1,3),(0,3,2),(4,6,7),(4,7,5),(0,4,5),(0,5,1),(2,3,7),(2,7,6),(0,2,6),(0,6,4),(1,5,7),(1,7,3)]
    return v[np.array(f)]
def tube(c,r0,r1,h,n=48):
    """Annulus (r0>0) or cylinder (r0=0) standing on z=c[2]."""
    a=np.linspace(0,2*np.pi,n,endpoint=False); b=np.roll(a,-1); c=np.array(c,float)
    def P(r,t,z): return np.stack([c[0]+r*np.cos(t),c[1]+r*np.sin(t),np.full_like(t,c[2]+z)],1)
    o=[]
    for z0,z1,r in ((0,h,r1),):
        o+=[np.stack([P(r,a,z0),P(r,b,z0),P(r,b,z1)],1),np.stack([P(r,a,z0),P(r,b,z1),P(r,a,z1)],1)]
    if r0>0:
        o+=[np.stack([P(r0,a,0),P(r0,b,h),P(r0,b,0)],1),np.stack([P(r0,a,0),P(r0,a,h),P(r0,b,h)],1)]
        for z,s in ((h,1),(0,-1)):
            A,B,A0,B0=P(r1,a,z),P(r1,b,z),P(r0,a,z),P(r0,b,z)
            o+=[np.stack([A0,B,A] if s<0 else [A0,A,B],1),np.stack([A0,B0,B] if s<0 else [A0,B,B0],1)]
    else:
        for z,s in ((h,1),(0,-1)):
            C=np.repeat(np.array([[c[0],c[1],c[2]+z]]),n,0)
            o.append(np.stack([C,P(r1,a,z),P(r1,b,z)] if s>0 else [C,P(r1,b,z),P(r1,a,z)],1))
    return np.concatenate(o)
def cat(*a): return np.concatenate(a)

COL=dict(orange=(.93,.40,.16),white=(.93,.92,.88),ink=(.15,.15,.16),metal=(.78,.79,.81),steel=(.62,.64,.67),
         blue=(.20,.42,.75),green=(.15,.45,.30),black=(.12,.12,.13),paper=(.98,.98,.96),gold=(.80,.65,.30))

def stepper(cx,cy,z0,d):
    """28BYJ-48: Ø28×19 body, ears at the top, shaft 8 mm off-centre toward d, wire box opposite."""
    d=np.array(d,float); p=np.array([-d[1],d[0]])
    def at(u,v): return (cx+d[0]*u+p[0]*v, cy+d[1]*u+p[1]*v)
    body=tube((cx,cy,z0),0,14,19)
    ears=box((cx,cy,z0+18.6),(abs(p[0])*42+abs(d[0])*7,abs(p[1])*42+abs(d[1])*7,0.8))
    wb=at(-15.5,0); wbox=box((wb[0],wb[1],z0+9),(abs(d[0])*7+abs(p[0])*17,abs(d[1])*7+abs(p[1])*17,15))
    s=at(8,0)
    return cat(body,ears,wbox,tube((s[0],s[1],z0+19),0,4.5,1.5,24)),tube((s[0],s[1],z0+20.5),0,2.5,8,16)

def uln2003(cx,cy,z0):
    pcb=box((cx,cy,z0+0.8),(32,35,1.6))
    chip=box((cx-4,cy+2,z0+3.2),(6.5,19.5,3.2))
    jst=box((cx+9,cy+8,z0+5),(6,12.5,7))
    leds=cat(*[tube((cx+9,cy-12+i*3.2,z0+1.6),0,1.2,2.5,12) for i in range(4)])
    hdr=cat(box((cx-12.5,cy-10,z0+5),(2.5,10,7)),box((cx-12.5,cy+8,z0+5),(2.5,5,7)))
    return pcb,cat(chip,jst,leds,hdr)

def nodemcu(cx,cy,z0):
    pcb=box((cx,cy,z0+0.8),(26,49,1.6))
    esp=box((cx,cy+13,z0+2.4),(16,24,1.6)); shield=box((cx,cy+10,z0+3.6),(12,15,1.2))
    usb=box((cx,cy-22,z0+3.1),(8,6,3))
    chip=box((cx,cy-10,z0+2.2),(5,5,1.2))
    hdr=cat(box((cx-11.5,cy+1,z0-1.3),(2.5,38,2.6)),box((cx+11.5,cy+1,z0-1.3),(2.5,38,2.6)))
    return pcb,cat(esp,usb,chip,hdr),shield

def parts():
    P={}
    L=lambda n,off=(0,0,0): load(D+n+'.stl')+np.array(off,float)
    P['base']=(L('base_plate'),COL['orange'])
    pcb,top,sh=nodemcu(10,-90.5,3.2)
    P['mcu_pcb']=(pcb,COL['blue']); P['mcu_parts']=(top,COL['black']); P['mcu_shield']=(sh,COL['metal'])
    for k,x in (('drvL',-46.5),('drvR',46.5)):
        a,b=uln2003(x,22,10); P[k+'_pcb']=(a,COL['green']); P[k+'_parts']=(b,COL['black'])
    a,b=stepper(0,47,2,(0,1)); P['motP']=(a,COL['metal']); P['motP_shaft']=(b,COL['gold'])
    a,b=stepper(-19.9,-91,15.5,(0,-1)); P['motA']=(a,COL['metal']); P['motA_shaft']=(b,COL['gold'])
    P['gearP']=(L('base_gear',(0,55,25.2)),COL['white'])
    P['gearA']=(L('linear_gear',(-19.9,-99,38.5)),COL['white'])
    P['bearing']=(tube((0,0,25.2),20,26,7),COL['steel'])
    P['plate']=(L('build_plate'),COL['white'])
    ang=np.radians([30,90,150,210,270,330])
    P['magP']=(cat(*[tube((70*np.cos(t),70*np.sin(t),32.7),0,2.5,1.5,16) for t in ang]),COL['steel'])
    P['paper']=(tube((0,0,34.2),0,72,0.15,96),COL['paper'])
    P['clamp']=(L('paper_clamp',(0,0,34.35)),COL['ink'])
    P['magC']=(cat(*[tube((70*np.cos(t),70*np.sin(t),34.85),0,2.5,1.5,16) for t in ang]),COL['steel'])
    P['rail']=(L('linear_rail',(0,0,38)),COL['ink'])
    P['cap']=(L('linear_cap',(0,0,45.4)),COL['white'])
    P['holder']=(L('pen_holder_body',(0,0,38)),COL['ink'])
    P['holder_cap']=(L('pen_holder_cap',(0,0,38)),COL['ink'])
    P['refill']=(cat(tube((0,0,35.6),0,1.5,62,16),tube((0,0,34.35),0,0.6,1.3,12)),COL['metal'])
    return P

GROUPS=dict(base=['base'],mcu=['mcu_pcb','mcu_parts','mcu_shield'],drivers=['drvL_pcb','drvL_parts','drvR_pcb','drvR_parts'],
    motP=['motP','motP_shaft'],motA=['motA','motA_shaft'],gearP=['gearP'],gearA=['gearA'],bearing=['bearing'],
    plate=['plate'],magP=['magP'],paper=['paper'],clamp=['clamp','magC'],rail=['rail'],cap=['cap'],
    pen=['holder','holder_cap','refill'])
