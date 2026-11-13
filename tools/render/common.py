import numpy as np
from svgkit import *
INK='#1d1d1f'; PAPER='#f6f4ee'; ACC='#f2a516'
MONO="ui-monospace,'SF Mono','JetBrains Mono',Menlo,Consolas,monospace"
SANS="-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
def real_fill(n,c):
    return hexc(np.array(c)*0.97+0.03),hexc(np.array(c)*0.82+0.04)
def balloon(x,y,label,r=17,fill=INK,fg='#fff'):
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"/>'
            f'<text x="{x:.1f}" y="{y+5.5:.1f}" font-family="{SANS}" font-weight="700" font-size="16" fill="{fg}" text-anchor="middle">{label}</text>')
def arrow(x0,y0,x1,y1,col=INK,w=3,head=14):
    d=np.array([x1-x0,y1-y0]); L=np.hypot(*d); u=d/L; nrm=np.array([-u[1],u[0]])
    b=np.array([x1,y1])-u*head
    p1=b+nrm*head*0.5; p2=b-nrm*head*0.5
    return (f'<path d="M{x0:.1f} {y0:.1f}L{b[0]:.1f} {b[1]:.1f}" stroke="{col}" stroke-width="{w}" fill="none" stroke-linecap="round"/>'
            f'<path d="M{x1:.1f} {y1:.1f}L{p1[0]:.1f} {p1[1]:.1f}L{p2[0]:.1f} {p2[1]:.1f}Z" fill="{col}"/>')
def svg_wrap(body,vb,bg=PAPER,radius=28,extra_defs=''):
    x,y,w,h=vb
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:.0f} {y:.0f} {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}">'
            f'<defs>{extra_defs}</defs>'
            f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{radius}" fill="{bg}"/>'
            f'<g fill="none" stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>')
def centroid(Q,names): return np.concatenate([Q[n][0].reshape(-1,3) for n in names]).mean(0)
