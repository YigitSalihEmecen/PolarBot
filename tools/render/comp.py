# 2D component illustrations. Each fn returns (svg, pins) ; pins: name->(x,y) absolute
MONO="ui-monospace,'SF Mono','JetBrains Mono',Menlo,Consolas,monospace"
SANS="-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
DEFS='''
<linearGradient id="gMetal"><stop stop-color="#DAD8D1"/></linearGradient>
<linearGradient id="gGold"><stop stop-color="#C4A15F"/></linearGradient>
<linearGradient id="gCyd"><stop stop-color="#E6B65A"/></linearGradient>
<linearGradient id="gPur"><stop stop-color="#6F6194"/></linearGradient>
<linearGradient id="gBlk"><stop stop-color="#2E2D2A"/></linearGradient>
<linearGradient id="gBat"><stop stop-color="#F5F3EC"/></linearGradient>
<linearGradient id="gBatR"><stop stop-color="#B8432F"/></linearGradient>
<linearGradient id="gBatK"><stop stop-color="#2E2D2A"/></linearGradient>
<linearGradient id="gSpk"><stop stop-color="#D3D1CA"/></linearGradient>
<linearGradient id="gCone"><stop stop-color="#3B3A37"/></linearGradient>
<linearGradient id="gBrown"><stop stop-color="#946A47"/></linearGradient>
<filter id="sh"><feOffset dx="0" dy="0"/></filter>
'''
def T(x,y,t,size=10,fill='#fff',anchor='middle',weight=600,font=MONO,rot=0,op=1):
    r=f' transform="rotate({rot} {x} {y})"' if rot else ''
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" opacity="{op}"{r}>{t}</text>'
def smd(x,y,w,h,body='#1f1f22',cap='#d9d9d9'):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" rx=".8" fill="{cap}"/>'
            f'<rect x="{x+w*0.22:.1f}" y="{y:.1f}" width="{w*0.56:.1f}" height="{h}" fill="{body}"/>')
def soic(x,y,w,h,n,label='',pin='#cfd2d6',fs=7,rot=0):
    s=f'<g transform="rotate({rot} {x+w/2} {y+h/2})">'
    p=w/(n+0.5)
    for i in range(n):
        px=x+p*(i+0.5)
        s+=f'<rect x="{px:.1f}" y="{y-4:.1f}" width="{p*0.45:.1f}" height="5" fill="{pin}"/><rect x="{px:.1f}" y="{y+h-1:.1f}" width="{p*0.45:.1f}" height="5" fill="{pin}"/>'
    s+=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="1.5" fill="#1b1c1f"/><circle cx="{x+5}" cy="{y+h-5}" r="1.8" fill="#333"/>'
    if label: s+=T(x+w/2,y+h/2+fs*0.35,label,fs,'#8d9096',weight=500)
    return s+'</g>'
def jst(x,y,n,pitch=12,label=None,labels=None,vertical=False,lc='#3b2a00',exit='top',fs=7.2):
    # JST 1.25 style connector, beige housing
    w=n*pitch+8; h=16
    s=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2.5" fill="#f3ecdc" stroke="#c9bd9f"/>'
    s+=f'<rect x="{x+3}" y="{y+3}" width="{w-6}" height="{h-8}" rx="1.5" fill="#e2d6bb"/>'
    pins={}
    for i in range(n):
        cx=x+4+pitch*(i+0.5)
        s+=f'<rect x="{cx-2.2:.1f}" y="{y+5}" width="4.4" height="5" fill="url(#gGold)"/>'
        pins[i]=(cx,y if exit=='top' else y+h)
        if labels: s+=T(cx,(y+h+fs+3) if exit=='top' else (y-4),labels[i],fs,lc,weight=800)
    if label:
        s+=T(x+w/2,y-6,label,fs+1.6,lc,weight=800) if exit=='top' else T(x-8,y+h/2+(fs+1.6)*0.35,label,fs+1.6,lc,'end',800)
    return s,pins


# ───────────────────────── PolarBot parts (top views) ─────────────────────────
NODE_L=['A0','RSV','RSV','SD3','SD2','SD1','CMD','SD0','CLK','GND','3V3','EN','RST','GND','VIN']
NODE_R=['D0','D1','D2','D3','D4','3V3','GND','D5','D6','D7','D8','RX','TX','GND','3V3']
def nodemcu(x,y,s=8):
    W,H=25.6*s,48.3*s; p=2.54*s; y0=y+H/2-7*p+2*s
    o=f'<rect x="{x}" y="{y}" width="{W}" height="{H}" rx="{1.2*s}" fill="#2B2A27" stroke="#141413" stroke-width="1.5"/>'
    # ESP-12E module with antenna
    mx,my=x+W/2-8*s,y+1.2*s
    o+=f'<rect x="{mx}" y="{my}" width="{16*s}" height="{24*s}" rx="2" fill="#1F1E1C" stroke="#3a3936"/>'
    o+=f'<path d="M{mx+1.5*s} {my+5*s}v-3.2h{2.2*s}v3.2h{2.2*s}v-3.2h{2.2*s}v3.2h{2.2*s}v-3.2h{2.2*s}v3.2h{2.2*s}v-3.2" stroke="#C4A15F" stroke-width="2" fill="none"/>'
    o+=f'<rect x="{mx+2*s}" y="{my+7*s}" width="{12*s}" height="{15*s}" rx="2" fill="url(#gMetal)" stroke="#8e9298"/>'
    o+=T(mx+8*s,my+14*s,'ESP8266',max(9,1.3*s),'#55595f',weight=700)+T(mx+8*s,my+16.8*s,'ESP-12E',max(7,1*s),'#6b6f75',weight=500)
    o+=T(x+W/2,y+30*s,'NodeMCU',max(11,1.9*s),'#F0EEE6',weight=700,font=SANS)+T(x+W/2,y+32.6*s,'v2 · ESP8266',max(7,1.05*s),'#B9B6AC',weight=500)
    o+=soic(x+W/2-3*s,y+35*s,6*s,4*s,4,'',fs=6)
    for i,lab in enumerate(('RST','FLASH')):
        bx=x+(4.5+i*13)*s; by=y+40.5*s
        o+=f'<rect x="{bx}" y="{by}" width="{3.6*s}" height="{3*s}" rx="2" fill="url(#gMetal)"/><circle cx="{bx+1.8*s}" cy="{by+1.5*s}" r="{0.9*s}" fill="#e8e8e8"/>'+T(bx+1.8*s,by+4.8*s,lab,max(6,0.9*s),'#B9B6AC',weight=600)
    o+=f'<rect x="{x+W/2-4*s}" y="{y+H-2*s}" width="{8*s}" height="{3.4*s}" rx="2" fill="url(#gMetal)" stroke="#8e9298"/>'
    pins={}
    for i in range(15):
        py=y0+i*p
        for side,lab,xx in ((0,NODE_L[i],x+1.6*s),(1,NODE_R[i],x+W-1.6*s)):
            o+=f'<rect x="{xx-0.75*s:.1f}" y="{py-0.75*s:.1f}" width="{1.5*s:.1f}" height="{1.5*s:.1f}" fill="url(#gGold)"/><circle cx="{xx:.1f}" cy="{py:.1f}" r="{0.38*s:.1f}" fill="#141413"/>'
            o+=T(xx+(1.5*s if side==0 else -1.5*s),py+3.5,lab,max(7.5,1.1*s),'#E9E6DC',anchor='start' if side==0 else 'end',weight=700)
            pins[('L' if side==0 else 'R')+str(i+1)]=(xx,py)
    return o,pins

def uln2003(x,y,s=8,power='top'):
    W,H=32*s,35*s
    o=f'<rect x="{x}" y="{y}" width="{W}" height="{H}" rx="{1*s}" fill="#2F6B4F" stroke="#141413" stroke-width="1.5"/>'
    cx,cy=x+11*s,y+17.5*s
    o+=f'<rect x="{cx-3.3*s}" y="{cy-9.8*s}" width="{6.6*s}" height="{19.6*s}" rx="2" fill="#1b1c1f"/>'
    for k in range(8):
        for sx in (-1,1): o+=f'<rect x="{cx+sx*3.3*s-(0.9*s if sx>0 else 0):.1f}" y="{cy-8.6*s+k*2.45*s:.1f}" width="{0.9*s:.1f}" height="{0.9*s:.1f}" fill="#cfd2d6"/>'
    o+=T(cx,cy,'ULN2003A',max(7,0.95*s),'#8d9096',weight=600,rot=90)
    for k,l in enumerate('ABCD'):
        o+=f'<circle cx="{x+20*s:.1f}" cy="{y+(10+k*4)*s:.1f}" r="{1.1*s:.1f}" fill="#D97757" stroke="#8a3e25"/>'+T(x+22.6*s,y+(10.4+k*4)*s,l,max(7,0.9*s),'#DDEFE4','start',700)
    for k in range(4): o+=smd(x+15*s,y+(9.2+k*4)*s,1.8*s,0.9*s)
    pins={}
    # inputs on the left edge
    for k in range(4):
        py=y+(11+k*3.2)*s; px=x+1.6*s
        o+=f'<rect x="{px-0.75*s:.1f}" y="{py-0.75*s:.1f}" width="{1.5*s:.1f}" height="{1.5*s:.1f}" fill="url(#gGold)"/>'+T(px+1.6*s,py+3.5,f'IN{k+1}',max(7,1*s),'#E9F3EC','start',700)
        pins[f'IN{k+1}']=(px,py)
    # power header
    py=y+1.8*s if power=='top' else y+H-1.8*s
    for k,lab in enumerate(('−','+')):
        px=x+(5+k*3.2)*s
        o+=f'<rect x="{px-0.75*s:.1f}" y="{py-0.75*s:.1f}" width="{1.5*s:.1f}" height="{1.5*s:.1f}" fill="url(#gGold)"/>'+T(px,py+(3.4*s if power=='top' else -1.4*s),lab,max(9,1.3*s),'#E9F3EC',weight=700)
        pins[lab]=(px,py)
    # motor connector on the right edge (JST-XH 5)
    jx=x+W-6*s; jy=y+(17.5-6.5)*s
    o+=f'<rect x="{jx}" y="{jy}" width="{5.6*s}" height="{13*s}" rx="2" fill="#F3EFE3" stroke="#C9BD9F"/>'
    for k in range(5):
        py=jy+(1.3+k*2.5)*s+0.5*s
        o+=f'<rect x="{jx+1.6*s:.1f}" y="{py-0.6*s:.1f}" width="{2.4*s:.1f}" height="{1.2*s:.1f}" fill="url(#gGold)"/>'
        pins[f'M{k+1}']=(jx+5.6*s,py)
    return o,pins

MOTOR_WIRES=['#3F6FB0','#D9A0B4','#E3C04A','#E58A3A','#C9442F']
def stepper(cx,cy,s=6,shaft=True):
    r=14*s
    o=f'<rect x="{cx-21*s}" y="{cy-3.5*s}" width="{42*s}" height="{7*s}" rx="{3.5*s}" fill="url(#gMetal)" stroke="#141413" stroke-width="1.2"/>'
    for sx in (-1,1): o+=f'<circle cx="{cx+sx*17.5*s}" cy="{cy}" r="{2.1*s}" fill="#F0EEE6" stroke="#8e9298"/>'
    o+=f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#gMetal)" stroke="#141413" stroke-width="1.5"/>'
    o+=f'<circle cx="{cx}" cy="{cy}" r="{r*0.82}" fill="none" stroke="#a9acb2" stroke-width="1.5"/>'
    # wire box on the left
    o+=f'<rect x="{cx-r-3.5*s}" y="{cy-8.5*s}" width="{6*s}" height="{17*s}" rx="{1.2*s}" fill="#3F6FB0" stroke="#141413" stroke-width="1.2"/>'
    if shaft:
        o+=f'<circle cx="{cx+8*s}" cy="{cy}" r="{4.5*s}" fill="#CFCAB9" stroke="#8e9298"/><circle cx="{cx+8*s}" cy="{cy}" r="{2.5*s}" fill="#C4A15F" stroke="#8a6d2f"/><rect x="{cx+6.5*s}" y="{cy-0.6*s}" width="{3*s}" height="{1.2*s}" fill="#8a6d2f"/>'
    o+=T(cx-1*s,cy+r*0.55,'28BYJ-48',max(8,1.25*s),'#55595f',weight=700)
    pins={f'w{k+1}':(cx-r-3.5*s,cy+(-5+k*2.5)*s) for k in range(5)}
    return o,pins

def bearing(cx,cy,s=4):
    o=f'<circle cx="{cx}" cy="{cy}" r="{26*s}" fill="url(#gMetal)" stroke="#141413" stroke-width="1.5"/>'
    o+=f'<circle cx="{cx}" cy="{cy}" r="{23.5*s}" fill="#2E2D2A"/><circle cx="{cx}" cy="{cy}" r="{22.5*s}" fill="none" stroke="#55534e" stroke-width="1"/>'
    o+=f'<circle cx="{cx}" cy="{cy}" r="{21*s}" fill="url(#gMetal)" stroke="#8e9298"/><circle cx="{cx}" cy="{cy}" r="{20*s}" fill="#F0EEE6" stroke="#141413" stroke-width="1.2"/>'
    o+=T(cx,cy+4,'6808-2RS',max(10,2.6*s),'#87867F',weight=600)
    return o

def magnet(cx,cy,s=6):
    o=''
    for k in range(3):
        y=cy+k*1.6*s
        o+=f'<path d="M{cx-2.5*s} {y}v{1.5*s}a{2.5*s} {0.9*s} 0 0 0 {5*s} 0v-{1.5*s}" fill="#9EA2A8" stroke="#141413" stroke-width="1"/><ellipse cx="{cx}" cy="{y}" rx="{2.5*s}" ry="{0.9*s}" fill="#D3D5D8" stroke="#141413" stroke-width="1"/>'
    return o

def refill(x,y,s=4):
    L=67*s
    o=f'<rect x="{x}" y="{y-1.5*s}" width="{L}" height="{3*s}" rx="{1.5*s}" fill="url(#gMetal)" stroke="#141413" stroke-width="1.2"/>'
    o+=f'<path d="M{x+L} {y-1.2*s}l{4*s} {1.2*s}-{4*s} {1.2*s}z" fill="#C4A15F" stroke="#141413" stroke-width="1"/><circle cx="{x+L+4.3*s}" cy="{y}" r="{0.5*s}" fill="#141413"/>'
    o+=f'<rect x="{x+4*s}" y="{y-1.5*s}" width="{20*s}" height="{3*s}" fill="#4A6FA5" opacity=".35"/>'
    return o
