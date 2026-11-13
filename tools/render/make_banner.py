from common import *
from theme import *
from pixfont import text_px
from drawing import rose
P=parts(); Q=place(P,{})
R=rot(150,-56)
body,proj,bb,sc,c=draw(Q,R,1000,900,fill=real_fill,sw=(0.9,1.7))
plot=''
for pts in rose():
    q=proj(np.c_[pts,np.full(len(pts),34.36)])
    plot+='M'+'L'.join(f'{x:.1f} {y:.1f}' for x,y,_ in q[::2])
# keep the pen, rail and holder in front of the drawing
front={k:v for k,v in Q.items() if k in('rail','holder','holder_cap','refill','cap','clamp','magC')}
fb,_,_,_,_=draw(front,R,1000,900,fill=real_fill,sw=(0.9,1.7),scale=sc,center=c)
x0,y0,x1,y1=bb; sD=430/(y1-y0)
dev=(f'<g transform="translate({1560-x1*sD:.1f},{470-y1*sD:.1f}) scale({sD:.4f})">{body}'
     f'<path d="{plot}" stroke="#2C4A8A" stroke-width="1.6" fill="none"/>{fb}</g>')
pts,w=text_px('POLARBOT'); px=15
def logo(dx,dy,col): return ''.join(f'<rect x="{dx+x*px}" y="{dy+y*px}" width="{px}" height="{px}" fill="{col}"/>' for x,y in pts)
L=logo(80,132,CLAY)+logo(74,126,INK)
chips=['ESP8266 · Wi-Fi','2 × 28BYJ-48','r · θ kinematics','G-code over WebSocket']
cx=78; ch=''
for t in chips:
    w_=len(t)*9.6+30
    ch+=f'<rect x="{cx}" y="340" width="{w_:.0f}" height="36" rx="18" fill="none" stroke="{RULE}" stroke-width="1.5"/><text x="{cx+w_/2:.0f}" y="363" font-family="{MONO}" font-size="14" fill="{SLATE}" text-anchor="middle">{t}</text>'
    cx+=w_+12
W,H=1600,500
svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><rect width="{W}" height="{H}" rx="32" fill="{CLOUD}"/>'
     f'{L}<text x="76" y="286" font-family="{SERIF}" font-size="34" fill="{INK}">A Wi-Fi polar plotter that draws on a spinning plate</text>'
     f'<text x="78" y="320" font-family="{SANS}" font-size="18" fill="{SLATE}">3D-printed · one USB cable · streams G-code from your browser</text>'
     f'{ch}<text x="78" y="440" font-family="{MONO}" font-size="13" letter-spacing="3" fill="{MUTE}">OPEN SOURCE HARDWARE + FIRMWARE · MIT</text>'
     f'<g fill="none" stroke-linecap="round" stroke-linejoin="round">{dev}</g></svg>')
open('out/banner.svg','w').write(svg); print(len(svg)//1024,'KB')
