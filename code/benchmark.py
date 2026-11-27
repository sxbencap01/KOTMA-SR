"""Strong baselines, train-only selection with each unordered pair of excluded boards fit once."""
from common import OUT
from itertools import combinations
from evaluate import Study, grid
from sklearn.ensemble import ExtraTreesRegressor
from catboost import CatBoostRegressor
import numpy as np
import pandas as pd


def fits(s, excluded):
    train = ~np.isin(s.g,excluded)
    idx = np.flatnonzero(~train)
    for name,params in (("ExtraTrees",(4,None)),("CatBoost",(2,3)),("Weighted kNN",(3,5,8))):
        for rank,par in enumerate(params):
            if name=="ExtraTrees":
                model=ExtraTreesRegressor(n_estimators=160,min_samples_leaf=2,max_depth=par,random_state=2026,n_jobs=1)
            elif name=="CatBoost":
                model=CatBoostRegressor(depth=par,iterations=120,learning_rate=.05,loss_function="MAE",
                                        random_seed=2026,verbose=False,thread_count=1,allow_writing_files=False)
            else:
                _,dist=s.arrays(tuple(s.groups[~np.isin(s.groups,excluded)]))
                order=np.argsort(dist[idx],axis=1,kind="stable")[:,:par]
                w=1/(1e-9+np.take_along_axis(dist[idx],order,axis=1))
                pred=grid(np.sum(w*s.y[train][order],axis=1)/w.sum(1))
            if name!="Weighted kNN":
                model.fit(s.x[train],s.y[train]/10)
                pred=grid(10*model.predict(s.x[idx]))
            for i,p in zip(idx,pred):
                yield dict(i=i,group=s.g[i],method=name,rank=rank,param=str(par),pred=p,loss=abs(s.y[i]-p))


def run_cohort(cohort):
    s=Study(cohort)
    inner=[]
    for pair in combinations(s.groups,2):
        for record in fits(s,pair):
            outer=pair[1] if record["group"]==pair[0] else pair[0]
            inner.append(dict(outer=outer,**record))
    inner=pd.DataFrame(inner)
    scores=inner.groupby(["outer","method","rank","param"],as_index=False).loss.mean()
    scores["inner_mae"]=scores.loss/10
    scores["selected"]=False
    scores.loc[scores.groupby(["outer","method"]).loss.idxmin(),"selected"]=True
    sel_name = "benchmark_selection.csv" if cohort=="primary" else f"{cohort}_benchmark_selection.csv"
    pred_name = "benchmark_predictions.csv" if cohort=="primary" else f"{cohort}_benchmark_predictions.csv"
    scores.to_csv(OUT/sel_name,index=False)
    best=set(scores.loc[scores.selected,["outer","method","rank"]].itertuples(index=False,name=None))
    rows=[]
    for outer in s.groups:
        for r in fits(s,[outer]):
            if (outer,r["method"],r["rank"]) in best:
                i=r["i"]
                rows.append(dict(side=s.cases.side[i],group=outer,reference=s.y[i]/10,method=r["method"],
                                 prediction=r["pred"]/10,error=r["loss"]/10))
    pd.DataFrame(rows).to_csv(OUT/pred_name,index=False)


if __name__=="__main__":
    for cohort in ("primary","qualified","small_layout","unambiguous","speed08"):
        run_cohort(cohort)
