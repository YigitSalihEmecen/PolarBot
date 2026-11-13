import numpy as np
def rose(n=420):
    """A sample plot on the paper: a 7-petal rose inside a spiral border, in plate mm."""
    t=np.linspace(0,4*np.pi,n*8)
    r=48*np.cos(7*t/2)
    a=np.stack([r*np.cos(t),r*np.sin(t)],1)
    s=np.linspace(0,6*2*np.pi,n*6); rs=54+s/(2*np.pi)*1.6
    b=np.stack([rs*np.cos(s),rs*np.sin(s)],1)
    return [a,b]
