from common import *
from theme import *
from line import render_lines, chain, path_d
P=parts(); Q=place(P,{})
BG=IVORY; GRID='#EEEBE1'; LINE=INK; DIM=MUTE
HID={'mcu_pcb':CLAY,'mcu_parts':CLAY,'drvL_pcb':'#5E8C6A','drvL_parts':'#5E8C6A','drvR_pcb':'#5E8C6A','drvR_parts':'#5E8C6A','motP':'#4A6FA5','motA':'#4A6FA5','gearP':'#6E5C93','gearA':'#6E5C93','bearing':'#946A47'}

def view(R,W,H,hidden=()):
    res,proj,img,idb,zb,sc,c=render_lines(Q,R,W,H,scale=S,hidden=hidden)
    g=[]
    for n,segs in res.items():
        for k,(w,col,dash) in {0:(0.9,LINE,''),1:(1.7,LINE,''),2:(1.1,HID.get(n,DIM),' stroke-dasharray="5 4"')}.items():
            s=[x for x in segs if x[4]==k]
            if s: g.append(f'<path d="{path_d(chain(s))}" stroke="{col}" stroke-width="{w}"{dash}/>')
    return ''.join(g),proj
def dim_h(x0,x1,y,label,ext0,ext1):
    return (f'<path d="M{x0} {ext0}V{y+8}M{x1} {ext1}V{y+8}" stroke="{DIM}" stroke-width="1" opacity=".7"/>'
            f'<path d="M{x0} {y}H{x1}" stroke="{DIM}" stroke-width="1.4"/>'
            f'<path d="M{x0} {y}l12 -5v10zM{x1} {y}l-12 -5v10z" fill="{DIM}"/>'
            f'<rect x="{(x0+x1)/2-34}" y="{y-13}" width="68" height="26" fill="{BG}"/>'
            f'<text x="{(x0+x1)/2}" y="{y+6}" font-family="{MONO}" font-size="17" fill="{LINE}" text-anchor="middle">{label}</text>')
def dim_v(y0,y1,x,label,ext0,ext1):
    return (f'<path d="M{ext0} {y0}H{x-8}M{ext1} {y1}H{x-8}" stroke="{DIM}" stroke-width="1" opacity=".7"/>'
            f'<path d="M{x} {y0}V{y1}" stroke="{DIM}" stroke-width="1.4"/>'
            f'<path d="M{x} {y0}l-5 12h10zM{x} {y1}l-5 -12h10z" fill="{DIM}"/>'
            f'<g transform="translate({x},{(y0+y1)/2}) rotate(-90)"><rect x="-38" y="-13" width="76" height="26" fill="{BG}"/>'
            f'<text y="6" font-family="{MONO}" font-size="17" fill="{LINE}" text-anchor="middle">{label}</text></g>')
W,H=1700,1300
S=3.2
body=[]
def lab(x,y,t): return f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="15" letter-spacing="3" fill="{DIM}">{t}</text>'
# plan (x-ray)
pw,pp=view(rot(0,0),640,700,hidden=tuple(HID))
PX,PY=110,110; body.append(f'<g transform="translate({PX},{PY})">{pw}</g>')
lo=pp(np.array([[-79,-117.4,45]]))[0]; hi=pp(np.array([[79,79,45]]))[0]
x0,x1=PX+lo[0],PX+hi[0]; yt,yb=PY+hi[1],PY+lo[1]
body.append(dim_h(x0,x1,yt-40,'158',yt-6,yt-6)); body.append(dim_v(yt,yb,x0-45,'196',x0-6,x0-6))
body.append(lab(PX+20,PY+690,'PLAN · X-RAY'))
# front elevation (from the lobe end)
fw,fp=view(rot(0,-90),640,360)
FX,FY=110,830; body.append(f'<g transform="translate({FX},{FY})">{fw}</g>')
g=fp(np.array([[-79,-117,0]]))[0]; t1=fp(np.array([[-79,-117,45.4]]))[0]; t2=fp(np.array([[-79,-117,97.6]]))[0]
xl=FX+fp(np.array([[-79,0,0]]))[0][0]
body.append(dim_v(FY+t1[1],FY+g[1],xl-30,'45',xl-6,xl-6)); body.append(dim_v(FY+t2[1],FY+g[1],xl-75,'98',xl-50,xl-6))
body.append(lab(FX+20,FY+20,'FRONT'))
# side elevation
sw_,sp=view(rot(-90,-90),700,360)
SX,SY=860,830; body.append(f'<g transform="translate({SX},{SY})">{sw_}</g>')
body.append(lab(SX+20,SY+20,'SIDE'))
# legend
lx,ly=900,170
items=[('NodeMCU v2',CLAY),('ULN2003 drivers','#5E8C6A'),('28BYJ-48 steppers','#4A6FA5'),('Pinions','#6E5C93'),('6808 bearing','#946A47')]
body.append(lab(lx,ly,'HIDDEN COMPONENTS'))
for i,(t,c) in enumerate(items):
    y=ly+40+i*36
    body.append(f'<path d="M{lx} {y-5}h46" stroke="{c}" stroke-width="2" stroke-dasharray="7 5"/><text x="{lx+62}" y="{y}" font-family="{SANS}" font-size="17" fill="{LINE}">{t}</text>')
facts=[('Drawing area','Ø 125 mm'),('Plate','Ø 150 mm on a 6808 bearing'),('Plate drive','20 : 68 gears, module 1.25'),('Arm drive','20-tooth pinion on a rack'),('USB','lobe end, NodeMCU micro-USB')]
py=ly+250; body.append(lab(lx,py,'KEY FIGURES'))
for i,(a_,b_) in enumerate(facts):
    body.append(f'<text x="{lx}" y="{py+38+i*32}" font-family="{SANS}" font-size="17" fill="{LINE}">{a_}<tspan fill="{DIM}" font-family="{MONO}" font-size="14"> — {b_}</tspan></text>')
# title block
tb=f'''<g transform="translate({W-640},{620})" font-family="{MONO}">
<rect width="600" height="130" fill="none" stroke="{DIM}" stroke-width="1.4"/>
<path d="M0 52H600M300 52V130M450 52V130" stroke="{DIM}" stroke-width="1"/>
<text x="20" y="36" font-size="24" font-family="{SERIF}" fill="{LINE}">PolarBot — general assembly</text>
<text x="20" y="80" font-size="12" fill="{DIM}" letter-spacing="2">MATERIAL</text><text x="20" y="108" font-size="17" fill="{LINE}">PLA · 3 colours</text>
<text x="320" y="80" font-size="12" fill="{DIM}" letter-spacing="2">UNITS</text><text x="320" y="108" font-size="17" fill="{LINE}">mm</text>
<text x="470" y="80" font-size="12" fill="{DIM}" letter-spacing="2">SHEET</text><text x="470" y="108" font-size="17" fill="{LINE}">1 / 1</text></g>'''
grid=f'<pattern id="g" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{GRID}" stroke-width="1"/></pattern><pattern id="G" width="200" height="200" patternUnits="userSpaceOnUse"><rect width="200" height="200" fill="url(#g)"/><path d="M200 0H0V200" fill="none" stroke="#E4E0D4" stroke-width="1.2"/></pattern>'
svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><defs>{grid}</defs>'
     f'<rect width="{W}" height="{H}" rx="28" fill="{BG}"/><rect x="20" y="20" width="{W-40}" height="{H-40}" rx="14" fill="url(#G)" stroke="{RULE}"/>'
     f'<g fill="none" stroke-linecap="round" stroke-linejoin="round">{"".join(body)}</g>{tb}</svg>')
open('out/blueprint.svg','w').write(svg); print(len(svg)//1024,'KB')
