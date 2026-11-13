from common import *
from theme import SERIF,IVORY,RULE
P=parts()
HL_LIT,HL_SH='#F4D9CC','#E6B29C'
def ikea_fill(hl):
    def f(n,c):
        g=[k for k,v in GROUPS.items() if n in v][0]
        if g in hl: return HL_LIT,HL_SH
        return '#ffffff','#e9e7e2'
    return f
SCREW=lambda x,y,s=1: (f'<g transform="translate({x},{y}) scale({s})" stroke="{INK}" stroke-width="2.2" fill="#fff">'
  '<path d="M-16 0h32v-7q0-7-7-7h-18q-7 0-7 7z"/><path d="M-6 0v34l6 9 6-9v-34" />'
  '<path d="M-6 8l12-4M-6 16l12-4M-6 24l12-4M-6 32l12-4" stroke-width="1.6"/><path d="M-5 -10h10" stroke-width="2.6"/></g>')
ICON={
 'screw':lambda x,y:SCREW(x,y-18,0.95),
 'board':lambda x,y:f'<g transform="translate({x},{y})" stroke="{INK}" stroke-width="2.2" fill="#fff"><rect x="-24" y="-16" width="48" height="32" rx="3"/><rect x="-10" y="-9" width="20" height="18" fill="{INK}"/><path d="M-20 -12v24M20 -12v24" stroke-dasharray="2 3"/></g>',
 'motor':lambda x,y:f'<g transform="translate({x},{y})" stroke="{INK}" stroke-width="2.2" fill="#fff"><path d="M-28 -6h56v6h-56z"/><circle cy="4" r="17"/><circle cy="-4" r="4" fill="{INK}"/><circle cx="-23" cy="-3" r="2"/><circle cx="23" cy="-3" r="2"/></g>',
 'bearing':lambda x,y:f'<g transform="translate({x},{y})" stroke="{INK}" stroke-width="2.2" fill="#fff"><circle r="24"/><circle r="17"/><circle r="11" fill="#fff"/>'+''.join(f'<circle cx="{20.5*np.cos(t):.1f}" cy="{20.5*np.sin(t):.1f}" r="2.2" fill="{INK}" stroke="none"/>' for t in np.linspace(0,2*np.pi,12,endpoint=False))+'</g>',
 'magnet':lambda x,y:f'<g transform="translate({x},{y})" stroke="{INK}" stroke-width="2.2" fill="#fff"><ellipse cy="-6" rx="18" ry="7"/><path d="M-18 -6v12a18 7 0 0 0 36 0v-12"/></g>',
 'pen':lambda x,y:f'<g transform="translate({x},{y}) rotate(-35)" stroke="{INK}" stroke-width="2.2" fill="#fff"><rect x="-3" y="-30" width="6" height="52" rx="2"/><path d="M-3 22l3 10 3-10" fill="{INK}"/></g>',
 'wire':lambda x,y:f'<g transform="translate({x},{y})" fill="none" stroke-width="4" stroke-linecap="round"><path d="M-26 -20c20 0 10 40 52 40" stroke="#B8432F"/><path d="M-26 -8c20 0 10 40 52 40" stroke="{INK}"/><path d="M-26 4c18 0 14 -26 52 -26" stroke="#4A6FA5"/></g>',
 'paper':lambda x,y:f'<g transform="translate({x},{y})" stroke="{INK}" stroke-width="2.2" fill="#fff"><circle r="24"/><path d="M-12 4c6-14 18-14 22 0s-14 14-18 6" fill="none" stroke-width="1.6"/></g>',
}
def callout(x,y,qty,label,icon):
    return (f'<rect x="{x}" y="{y}" width="250" height="96" rx="14" fill="#fff" stroke="{RULE}" stroke-width="2"/>'+ICON[icon](x+48,y+48)+
            f'<text x="{x+98}" y="{y+50}" font-family="{SANS}" font-size="34" font-weight="700" fill="{INK}">{qty}</text>'
            f'<text x="{x+98}" y="{y+76}" font-family="{SANS}" font-size="15" fill="#5f5b52">{label}</text>')
R=rot(150,-56)
def step(num,groups,hl,offs,callouts,caption,arrows_for=(),extra=None,W=1300,H=1050):
    Q=place(P,{g:offs.get(g,(0,0,0)) for g in GROUPS})
    Q={n:v for n,v in Q.items() if any(n in GROUPS[g] for g in groups)}
    body,proj,bb,sc,c=draw(Q,R,W,H,fill=ikea_fill(hl),sw=(1.2,2.3))
    ov=''
    for g in arrows_for:
        names=[n for n in GROUPS[g] if n in Q]
        a=centroid(Q,names); b=a-np.array(offs[g])
        pa,pb=proj(a)[0],proj(b)[0]; d=pb[:2]-pa[:2]; L=np.hypot(*d); u=d/L
        s0=pa[:2]+u*L*0.08; s1=pa[:2]+u*L*0.92
        ov+=arrow(*s0,*s1,col='#fff',w=11,head=26)+arrow(*(s0+u*2),*(s1-u*3),col=INK,w=4,head=18)
    if extra: ov+=extra(proj)
    x0,y0,x1,y1=bb; m=70
    vb=[min(x0-m,0),min(y0-m-150,-30),0,0]; vb[2]=max(x1+m,W)-vb[0]; vb[3]=max(y1+m,H)-vb[1]+90
    hdr=f'<text x="{vb[0]+56}" y="{vb[1]+124}" font-family="{SERIF}" font-size="120" fill="{INK}">{num}</text>'
    cx=vb[0]+vb[2]-56
    for k,(q,l,ic) in enumerate(callouts): hdr+=callout(int(cx-250-k*270),int(vb[1]+40),q,l,ic)
    hdr+=f'<text x="{vb[0]+56}" y="{vb[1]+vb[3]-44}" font-family="{SANS}" font-size="22" fill="{INK}">{caption}</text>'
    return svg_wrap(body+ov+hdr,vb,bg=IVORY,radius=24)
WIRE={'red':'#B8432F','blk':'#2E2D2A','blu':'#4A6FA5','grn':'#5E8C6A','pur':'#6E5C93','ylw':'#C49A2C'}
def wires(proj):
    def p(v): return proj(np.array(v,float))[0][:2]
    def w(a,b,col,lift=40,width=4):
        a,b=p(a),p(b); d=np.hypot(*(b-a)); k=max(lift,0.25*d)
        c1=a+np.array([0,-k]); c2=b+np.array([0,-k])
        path=f'M{a[0]:.1f} {a[1]:.1f}C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {b[0]:.1f} {b[1]:.1f}'
        return (f'<path d="{path}" stroke="{INK}" stroke-width="{width+3}"/><path d="{path}" stroke="{WIRE[col]}" stroke-width="{width}"/>'
                f'<circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="4.5" fill="{INK}"/><circle cx="{b[0]:.1f}" cy="{b[1]:.1f}" r="4.5" fill="{INK}"/>')
    def tag(v,text,dx=0,dy=-30):
        x,y=p(v); x+=dx; y+=dy; wd=len(text)*9.6+22
        return (f'<rect x="{x-wd/2:.0f}" y="{y-16:.0f}" width="{wd:.0f}" height="28" rx="14" fill="{INK}"/>'
                f'<text x="{x:.0f}" y="{y+4:.0f}" font-family="{MONO}" font-size="15" font-weight="700" fill="#fff" text-anchor="middle">{text}</text>')
    MCU=(10,-75,6); o=''
    for i,col in enumerate(['grn','grn','grn','grn']):
        o+=w((5+i*2,-72,6),(-58+i*2.5,22,14),col,lift=60,width=3)
        o+=w((8+i*2,-72,6),(35+i*2.5,22,14),'blu',lift=50,width=3)
    o+=w((14,-74,6),(-38,10,14),'red',lift=40,width=3)+w((16,-74,6),(55,10,14),'red',lift=40,width=3)
    o+=w((18,-74,6),(-35,10,14),'blk',lift=34,width=3)+w((20,-74,6),(58,10,14),'blk',lift=34,width=3)
    o+=w((-46.5,34,14),(0,30,8),'pur',lift=30,width=4)+w((46.5,34,14),(-19.9,-75,30),'ylw',lift=60,width=4)
    o+=tag((10,-95,8),'NODEMCU',0,40)+tag((-46.5,22,12),'PLATE DRIVER',0,-40)+tag((46.5,22,12),'ARM DRIVER',0,-40)
    o+=tag((0,47,20),'PLATE MOTOR',-40,40)+tag((-19.9,-91,35),'ARM MOTOR',120,-10)
    return o
B=['base','mcu','drivers','motP','motA','gearP','gearA']
steps=[
 (1,['base','mcu','drivers'],{'mcu','drivers'},{'mcu':(0,0,30),'drivers':(0,0,30)},
  [('8×','M3 screw','screw'),('3×','NodeMCU + 2 ULN2003','board')],'Seat the NodeMCU in the lobe, USB port facing the end hole. Screw both ULN2003 boards onto their standoffs.',['mcu','drivers']),
 (2,B,{'motP','motA','gearP','gearA'},{'motP':(0,0,40),'motA':(0,0,40),'gearP':(0,0,70),'gearA':(0,0,70)},
  [('4×','M3 screw','screw'),('2×','28BYJ-48 stepper','motor')],'Screw the plate motor into its cradle and the arm motor into the lobe. Press a 20-tooth pinion onto each shaft.',['motP','motA','gearP','gearA']),
 (3,B,set(),{},[('~14×','jumper wires','wire')],'Wire it up: NodeMCU pins to both ULN2003 inputs, 5 V and GND to both boards, each motor into its driver.',[],wires),
 (4,B+['bearing','plate','magP'],{'bearing','plate','magP'},{'bearing':(0,0,30),'plate':(0,0,60),'magP':(0,0,85)},
  [('6×','magnet 5 × 1.5 mm','magnet'),('1×','6808 bearing','bearing')],'Press the bearing into the plate, glue a magnet into each pocket, and drop the plate onto the hub so the ring gear meets the pinion.',['bearing','plate','magP']),
 (5,B+['bearing','plate','magP','rail','cap'],{'rail','cap'},{'rail':(0,-60,0),'cap':(0,0,40)},
  [('4×','M3 screw','screw')],'Slide the rack arm in through the lobe, teeth against the pinion, then screw the lobe cap on.',['rail','cap']),
 (6,B+['bearing','plate','magP','rail','cap','pen'],{'pen'},{'pen':(0,0,50)},
  [('1×','pen refill Ø3 mm','pen')],'Screw the pen holder into the ring at the end of the arm, drop the refill in and close the holder cap.',['pen']),
 (7,list(GROUPS),{'paper','clamp'},{'paper':(0,0,25),'clamp':(0,0,50)},
  [('6×','magnet 5 × 1.5 mm','magnet'),('1×','paper disc Ø144','paper')],'Lay a paper disc on the plate and snap the magnetic clamp on top. Ready to plot.',['paper','clamp']),
]
for s in steps:
    svg=step(*s); open(f'out/step-{s[0]}.svg','w').write(svg); print('step',s[0],len(svg)//1024,'KB')
