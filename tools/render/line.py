import numpy as np
from rend import raster, rot
from scipy.ndimage import minimum_filter
def feature_edges(T, V, ang=32):
    n=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]); nl=np.linalg.norm(n,axis=1); keep=nl>1e-10
    T=T[keep]; n=n[keep]/nl[keep,None]
    q=np.round(T.reshape(-1,3)/1e-3).astype(np.int64)
    _,vid=np.unique(q,axis=0,return_inverse=True); vid=vid.reshape(-1,3)
    E=np.concatenate([vid[:,[0,1]],vid[:,[1,2]],vid[:,[2,0]]]); F=np.tile(np.arange(len(T)),3)
    P=np.concatenate([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]])
    Es=np.sort(E,1); key=Es[:,0]*(vid.max()+1)+Es[:,1]
    o=np.argsort(key,kind='stable'); key=key[o]; F=F[o]; P=P[o]
    u,st,cnt=np.unique(key,return_index=True,return_counts=True)
    facing=(n@V)>0
    out=[];kinds=[]
    two=cnt==2
    a=F[st[two]]; b=F[st[two]+1]
    crease=(n[a]*n[b]).sum(1)<np.cos(np.radians(ang))
    sil=facing[a]!=facing[b]
    vis_side=facing[a]|facing[b]
    sel=(crease&vis_side)|sil
    out.append(P[st[two]][sel]); kinds.append(np.where(sil[sel],1,0))
    oth=~two
    out.append(P[st[oth]]); kinds.append(np.ones(oth.sum(),int))
    return np.concatenate(out),np.concatenate(kinds)

def render_lines(parts,R,W,H,pad=60,scale=None,center=None,eps=0.25,ang=32,hidden=()):
    """parts: dict name->(tris,color). returns dict name->list of segments (x0,y0,x1,y1,kind), project fn"""
    L=[(t,c,i) for i,(k,(t,c)) in enumerate(parts.items())]
    img,zb,idb,proj,scale,c=raster(L,R,W,H,pad,scale,center)
    zmin=minimum_filter(zb,size=3)
    V=R[2]  # view axis in model coords (towards viewer)
    def project(p):
        p=np.atleast_2d(p)@R.T
        return np.stack([(p[:,0]-c[0])*scale+W/2,H/2-(p[:,1]-c[1])*scale,p[:,2]],1)
    res={}
    for name,(t,col) in parts.items():
        segs,kind=feature_edges(t,V,ang)
        A=project(segs[:,0]); B=project(segs[:,1])
        ln=np.hypot(*(B[:,:2]-A[:,:2]).T); ns=np.maximum(2,np.ceil(ln/1.0).astype(int)+1)
        out=[]
        for i in range(len(segs)):
            s=np.linspace(0,1,ns[i]); p=A[i]+(B[i]-A[i])*s[:,None]
            x=np.clip(p[:,0].astype(int),0,W-1); y=np.clip(p[:,1].astype(int),0,H-1)
            vis=p[:,2]>=zmin[y,x]-eps
            for flag,kd in ((vis,kind[i]),(~vis,2)):
                if kd==2 and name not in hidden: continue
                if not flag.any(): continue
                d=np.diff(np.concatenate([[0],flag.astype(int),[0]]))
                for s0,s1 in zip(np.where(d==1)[0],np.where(d==-1)[0]-1):
                    if s1==s0: continue
                    out.append((p[s0,0],p[s0,1],p[s1,0],p[s1,1],kd))
        res[name]=out
    return res,project,img,idb,zb,scale,c

def chain(segs,tol=0.6):
    # join segments sharing endpoints into polylines
    from collections import defaultdict
    segs=[s for s in segs]
    key=lambda x,y:(round(x/tol),round(y/tol))
    ends=defaultdict(list)
    for i,s in enumerate(segs): ends[key(s[0],s[1])].append(i); ends[key(s[2],s[3])].append(i)
    used=[False]*len(segs); lines=[]
    for i in range(len(segs)):
        if used[i]: continue
        used[i]=True; s=segs[i]; pts=[(s[0],s[1]),(s[2],s[3])]
        for direction in (1,0):
            while True:
                tail=pts[-1] if direction else pts[0]; nxt=None
                for j in ends[key(*tail)]:
                    if not used[j]: nxt=j;break
                if nxt is None: break
                used[nxt]=True; t=segs[nxt]
                a,b=(t[0],t[1]),(t[2],t[3])
                if key(*a)!=key(*tail): a,b=b,a
                if direction: pts.append(b)
                else: pts.insert(0,b)
        lines.append(pts)
    return lines

def path_d(lines):
    out=[]
    for pts in lines:
        # drop collinear points
        q=[pts[0]]
        for k in range(1,len(pts)-1):
            ax,ay=q[-1]; bx,by=pts[k]; cx,cy=pts[k+1]
            if abs((bx-ax)*(cy-ay)-(by-ay)*(cx-ax))>0.35*max(1,np.hypot(cx-ax,cy-ay)): q.append(pts[k])
        q.append(pts[-1])
        out.append('M'+'L'.join(f'{x:.1f} {y:.1f}' for x,y in q))
    return ''.join(out).replace('.0 ',' ').replace('.0L','L').replace('.0M','M')
