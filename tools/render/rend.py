import numpy as np
np.seterr(all="ignore")
from stl import load
import os
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','hardware','stl','')
def rot(az,el):
    a,e=np.radians(az),np.radians(el)
    Rz=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
    Rx=np.array([[1,0,0],[0,np.cos(e),-np.sin(e)],[0,np.sin(e),np.cos(e)]])
    return Rx@Rz
def raster(parts,R,W=1400,H=1400,pad=40,scale=None,center=None):
    # parts: list of (tris Nx3x3, rgb, partid)
    allv=np.concatenate([p[0].reshape(-1,3) for p in parts])@R.T
    lo,hi=allv[:,:2].min(0),allv[:,:2].max(0)
    if scale is None: scale=min((W-2*pad)/(hi[0]-lo[0]),(H-2*pad)/(hi[1]-lo[1]))
    c=(lo+hi)/2 if center is None else center
    img=np.ones((H,W,3)); zb=np.full((H,W),-1e9); idb=np.full((H,W),-1)
    L=np.array([-0.3,0.45,0.85]); L/=np.linalg.norm(L)
    proj=[]
    for tris,col,pid in parts:
        v=tris@R.T
        P=np.empty_like(v); P[...,0]=(v[...,0]-c[0])*scale+W/2; P[...,1]=H/2-(v[...,1]-c[1])*scale; P[...,2]=v[...,2]
        n=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]); nl=np.linalg.norm(n,axis=1); ok=nl>1e-12
        n[ok]/=nl[ok,None]
        sh=np.clip(0.35+0.65*np.abs(n@L),0,1)
        proj.append(P)
        for i in np.where(ok)[0]:
            t=P[i]; x0,y0=np.floor(t[:,:2].min(0)).astype(int); x1,y1=np.ceil(t[:,:2].max(0)).astype(int)
            x0=max(x0,0);y0=max(y0,0);x1=min(x1,W-1);y1=min(y1,H-1)
            if x1<x0 or y1<y0: continue
            xs,ys=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
            (ax,ay,az),(bx,by,bz),(cx,cy,cz)=t
            d=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
            if abs(d)<1e-12: continue
            w0=((by-cy)*(xs-cx)+(cx-bx)*(ys-cy))/d; w1=((cy-ay)*(xs-cx)+(ax-cx)*(ys-cy))/d; w2=1-w0-w1
            m=(w0>=-1e-4)&(w1>=-1e-4)&(w2>=-1e-4)
            if not m.any(): continue
            z=w0*az+w1*bz+w2*cz
            sub=zb[y0:y1+1,x0:x1+1]; m&=z>sub
            sub[m]=z[m]; img[y0:y1+1,x0:x1+1][m]=np.array(col)*sh[i]; idb[y0:y1+1,x0:x1+1][m]=pid
    return img,zb,idb,proj,scale,c
def cam(yaw,pitch,roll=0):
    y,p,r=np.radians([yaw,pitch,roll])
    Ry=np.array([[np.cos(y),0,np.sin(y)],[0,1,0],[-np.sin(y),0,np.cos(y)]])
    Rx=np.array([[1,0,0],[0,np.cos(p),-np.sin(p)],[0,np.sin(p),np.cos(p)]])
    Rz=np.array([[np.cos(r),-np.sin(r),0],[np.sin(r),np.cos(r),0],[0,0,1]])
    return Rz@Rx@Ry
