import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scene import parts, GROUPS
from svgkit import place
from rend import rot
from line import render_lines
from drawing import rose
def paper_texture(N=1600,R=75):
    im=Image.new('L',(N,N),255); d=ImageDraw.Draw(im)
    for pts in rose():
        q=[((x+R)/(2*R)*N,(R-y)/(2*R)*N) for x,y in pts]; d.line(q,fill=40,width=4,joint='curve')
    return np.asarray(im)/255.0
def render(Q,R,W,H,fn,ss=2,pad=80,tex=True):
    names=list(Q.keys())
    res,proj,img,idb,zb,scale,c=render_lines(Q,R,W*ss,H*ss,pad*ss)
    img=img.copy()
    if tex and 'paper' in Q:
        i=names.index('paper'); ys,xs=np.where(idb==i)
        X=(xs+0.5-W*ss/2)/scale+c[0]; Y=(H*ss/2-ys-0.5)/scale+c[1]; Z=zb[ys,xs]
        M=np.stack([X,Y,Z],1)@R; T=paper_texture(); N=T.shape[0]
        u=np.clip(((M[:,0]+75)/150*N).astype(int),0,N-1); v=np.clip(((75-M[:,1])/150*N).astype(int),0,N-1)
        img[ys,xs]=img[ys,xs]*T[v,u][:,None]+np.array([.12,.2,.45])*(1-T[v,u][:,None])
    rgb=(np.clip(img,0,1)*255).astype(np.uint8); a=((idb>=0)*255).astype(np.uint8)
    im=Image.fromarray(np.dstack([rgb,a])); d=ImageDraw.Draw(im)
    for n,segs in res.items():
        for x0,y0,x1,y1,k in segs: d.line([(x0,y0),(x1,y1)],fill=(24,24,26,255),width=int(ss*(1.6 if k else 0.9)+0.5))
    sh=Image.new('RGBA',im.size,(0,0,0,0)); al=Image.fromarray(a).filter(ImageFilter.GaussianBlur(18*ss))
    sh.putalpha(al.point(lambda v:int(v*0.35))); sh=sh.transform(sh.size,Image.AFFINE,(1,0,-14*ss,0,1,-22*ss))
    out=Image.alpha_composite(sh,im).resize((W,H),Image.LANCZOS)
    bb=out.getbbox(); out=out.crop((max(bb[0]-30,0),max(bb[1]-30,0),min(bb[2]+30,W),min(bb[3]+30,H)))
    out.save(fn,optimize=True); print(fn,out.size)
P=parts(); Q=place(P,{})
render(Q,rot(150,-56),1300,1100,'out/render-hero.png')
inside={k:v for k,v in Q.items() if k not in('plate','magP','paper','clamp','magC','bearing')}
render(inside,rot(150,-50),1300,1100,'out/render-inside.png',tex=False)
