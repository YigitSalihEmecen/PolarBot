import numpy as np, struct, sys
def load(p):
    b=open(p,'rb').read()
    n=struct.unpack('<I',b[80:84])[0]
    if 84+n*50==len(b):
        a=np.frombuffer(b[84:84+n*50],dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]))
        return a['v'].astype(float)
    import re
    v=np.array(re.findall(rb'vertex\s+(\S+)\s+(\S+)\s+(\S+)',b),dtype=float)
    return v.reshape(-1,3,3)
