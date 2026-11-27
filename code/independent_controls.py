"""Separately tune each adaptation policy as a deployable method, in addition to matched ablations."""
from common import OUT
from evaluate import Study,CONFIGS
import numpy as np
import pandas as pd


if __name__=="__main__":
    s=Study("primary")
    methods=["Gated median","Gated descriptor","Always capped","Always uncapped","Full"]
    rows=[]
    for g in s.groups:
        tr=tuple(s.groups[s.groups!=g])
        losses=np.zeros((len(CONFIGS),len(methods)),int)
        for inner in tr:
            base=tuple(x for x in tr if x!=inner)
            for i in np.flatnonzero(s.g==inner):
                for n,cfg in enumerate(CONFIGS):
                    p,_=s.predict(i,base,cfg)
                    losses[n]+=np.abs(np.array([p[m] for m in methods])-s.y[i])
        for m,best in zip(methods,losses.argmin(axis=0)):
            cfg=CONFIGS[best]
            for i in np.flatnonzero(s.g==g):
                p,_=s.predict(i,tr,cfg)
                rows.append(dict(side=s.cases.side[i],group=g,method=m,reference=s.y[i]/10,prediction=p[m]/10,
                                 error=abs(p[m]-s.y[i])/10,cap=cfg[0]/10,k=cfg[1],weight=cfg[2]))
    frame=pd.DataFrame(rows)
    frame.to_csv(OUT/"independent_controls.csv",index=False)
    frame.groupby("method").error.agg(["size","mean"]).to_csv(OUT/"independent_controls_summary.csv")
