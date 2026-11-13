import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from rend import raster, rot, cam
from line import render_lines, chain, path_d
from scene import parts, GROUPS
from scipy.ndimage import zoom as ndzoom

def rdp(pts,eps):
    if len(pts)<3: return pts
    a,b=pts[0],pts[-1]; d=b-a; n=np.hypot(*d)
    if n<1e-9: dist=np.hypot(*(pts-a).T)
    else: dist=np.abs(d[0]*(pts[:,1]-a[1])-d[1]*(pts[:,0]-a[0]))/n
    i=np.argmax(dist)
    if dist[i]>eps: return np.vstack([rdp(pts[:i+1],eps)[:-1],rdp(pts[i:],eps)])
    return np.array([a,b])

def mask_path(mask,f=1.0,eps=0.6):
    if mask.sum()<4: return ''
    m=np.pad(mask.astype(float),1)
    fig=plt.figure(); cs=plt.contourf(m,levels=[0.5,1.5]); plt.close(fig)
    out=[]
    for p in cs.get_paths():
        for poly in p.to_polygons(closed_only=True):
            if len(poly)<4: continue
            poly=rdp(poly,eps)
            if len(poly)<3: continue
            poly=(poly-1+0.5)*f
            out.append('M'+'L'.join(f'{x:.1f} {y:.1f}' for x,y in poly)+'Z')
    return ''.join(out)

def lighten(c,k): return tuple(1-(1-np.array(c))*k)
def hexc(c): return '#%02x%02x%02x'%tuple(int(round(v*255)) for v in np.clip(c,0,1))

def draw(Q,R,W,H,fill=None,stroke=None,sw=(1.1,2.1),pad=60,scale=None,center=None,hidden=False,ang=32,eps=0.25):
    """Q: dict name->(tris,color). fill(name,color)->(lit,shade) hex or None. stroke(name)->hex"""
    res,project,img,idb,zb,scale,c=render_lines(Q,R,W,H,pad,scale,center,eps=eps,ang=ang)
    names=list(Q.keys())
    body=[]
    if fill:
        # luminance ratio -> two bands
        for i,n in enumerate(names):
            m=idb==i
            if not m.any(): continue
            col=np.array(Q[n][1]); lum=img[...,:3].mean(2)/max(col.mean(),1e-3)
            lit,shade=fill(n,Q[n][1])
            body.append(f'<path d="{mask_path(m)}" fill="{shade}"/>')
            m2=m&(lum>0.78)
            if lit!=shade and m2.any(): body.append(f'<path d="{mask_path(m2)}" fill="{lit}"/>')
    ys,xs=np.where(idb>=0)
    bbox=(xs.min(),ys.min(),xs.max(),ys.max())
    for n in names:
        segs=res[n]
        if not segs: continue
        st=stroke(n) if stroke else '#1d1d1f'
        for k,w in ((0,sw[0]),(1,sw[1])):
            s=[x for x in segs if x[4]==k]
            if s: body.append(f'<path d="{path_d(chain(s))}" stroke="{st}" stroke-width="{w}"/>')
    return '\n'.join(body),project,bbox,scale,c

def place(P,offsets):
    Q={}
    for g,names in GROUPS.items():
        for n in names:
            t,c=P[n]; t=t.copy()
            if g in offsets: t+=np.array(offsets[g],float)
            Q[n]=(t,c)
    return Q
