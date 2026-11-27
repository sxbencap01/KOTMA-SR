"""Matched subset curves, common held boards, both fixed and subset-retuned policies."""
from common import OUT
from evaluate import Study, CONFIGS, scaled, grid
from primitives import stable_similarity_weights
import numpy as np
import pandas as pd


def tune(study,groups):
    totals=np.zeros(len(CONFIGS),int)
    for val in groups:
        tr=tuple(g for g in groups if g!=val)
        train,ds=study.arrays(tr)
        y=study.y[train]
        for i in np.flatnonzero(study.g==val):
            d=scaled(ds[i])
            cbr=y[np.argmin(d)]
            if (y==cbr).sum()>=3:
                totals += abs(cbr-study.y[i])
                continue
            mixed={}
            for weight in (.5,.75):
                cost=weight*d+(1-weight)*scaled(study.f[i,train])
                order=np.argsort(cost,kind="stable")
                for k in (5,8):
                    j=order[:k]
                    mixed[k,weight]=grid(stable_similarity_weights(cost[j])@y[j])
            preds=[np.clip(mixed[k,w],cbr-cap,cbr+cap) for cap,k,w in CONFIGS]
            totals += np.abs(np.asarray(preds)-study.y[i])
    return CONFIGS[totals.argmin()]


if __name__=="__main__":
    s=Study("primary")
    rows=[]
    for j,g in enumerate(s.groups):
        available=s.groups[s.groups!=g]
        for rep in range(10):
            perm=np.random.default_rng([20261124,j,rep]).permutation(available)
            for n in (5,10,15,20):
                if n==20 and rep>0:
                    continue
                groups=tuple(sorted(perm[:n]))
                chosen=tune(s,groups)
                for i in np.flatnonzero(s.g==g):
                    for name,cfg in (("Fixed",(4,5,.5)),("Retuned",chosen)):
                        p,_=s.predict(i,groups,cfg)
                        rows.append(dict(group=g,side=s.cases.side[i],training_boards=n,replicate=rep,
                                         subset="|".join(groups),policy=name,cap=cfg[0]/10,k=cfg[1],weight=cfg[2],
                                         error=abs(p["Full"]-s.y[i])/10,cbr_error=abs(p["CBR"]-s.y[i])/10))
    pd.DataFrame(rows).to_csv(OUT/"learning_cases.csv",index=False)
