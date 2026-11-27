"""Physical-board outer and inner splits. Integer deciticks throughout pressure decisions."""
from common import OUT
from itertools import product
from functools import lru_cache
import numpy as np
import pandas as pd
from primitives import stable_similarity_weights

# Ordered by the prespecified tie breaks: cap, k, then descriptor weight.
CONFIGS = list(product((2,4,5),(5,8),(.5,.75)))
METHODS = ("Full","CBR","Median","Gated median","Gated descriptor","Always capped","Always uncapped","Shuffled cost","Ridge")


def grid(values):
    return np.clip(np.rint(np.round(values,10)),50,80).astype(int)


def scaled(d):
    pos = d[d>1e-12]
    return d/(np.median(pos) if pos.size else 1.)


class Study:
    def __init__(self, cohort):
        index = pd.read_csv(OUT/"cases.csv")
        with np.load(OUT/"geometry_costs.npz") as archive:
            assert np.array_equal(index.key,archive["keys"])
            eligible = index.layout.ne("layout1")
            if cohort=="small_layout":
                eligible = index.layout.ne("layout2")
            elif cohort=="unambiguous":
                eligible = index.layout.eq("clear")
            elif cohort=="speed08":
                eligible &= index.speed.eq(.8)
            elif cohort=="qualified":
                eligible &= index.label.eq(1)
            elif cohort!="primary":
                raise ValueError(cohort)
            self.cases = index.loc[eligible].reset_index(drop=True)
            self.x = archive["desc"][eligible]
            self.f = archive["mat"][np.ix_(eligible,eligible)]
        self.g = self.cases.group.to_numpy()
        self.y = grid(10*self.cases.pressure.to_numpy())
        assert self.cases.side.is_unique and np.allclose(self.y,10*self.cases.pressure)
        self.groups = np.unique(self.g)

    @lru_cache(maxsize=2048)
    def arrays(self, groups):
        train = np.flatnonzero(np.isin(self.g,groups))
        x = self.x[train]
        scale = x.std(0)
        scale[scale<1e-9] = 1.
        delta = (self.x[:,None,:]-x)/scale
        return train, np.linalg.norm(delta,axis=2)

    def predict(self, i, groups, config, structural=None, descriptor=None, shuffle_seed=7001):
        train, dists = self.arrays(groups)
        cap,k,weight = config
        d = scaled(dists[i] if descriptor is None else descriptor)
        s = scaled(self.f[i,train] if structural is None else structural)
        y = self.y[train]
        nearest = y[np.argmin(d)]
        support = (y==nearest).sum()
        gate = support<3  # Rare-setting frequency in the complete training fold.
        median = np.median(y)
        def retrieve(cost):
            idx = np.argsort(cost,kind="stable")[:k]
            w = stable_similarity_weights(cost[idx])
            return w@y[idx], 1/(w@w),cost[idx[0]],idx,w
        mixed,neff,dmin,neighbors,weights = retrieve(weight*d+(1-weight)*s)
        desc = retrieve(d)[0]
        rng = np.random.default_rng([shuffle_seed,i,*train.tolist()])
        shuffled = retrieve(weight*d+(1-weight)*rng.permutation(s))[0]
        def bounded(candidate):
            return int(np.clip(grid(candidate),nearest-cap,nearest+cap))
        full = bounded(mixed) if gate else nearest
        preds = {"Full":full,"CBR":nearest,"Median":grid(median),"Gated median":bounded(median) if gate else nearest,
                 "Gated descriptor":bounded(desc) if gate else nearest,"Always capped":bounded(mixed),
                 "Always uncapped":grid(mixed),"Shuffled cost":bounded(shuffled) if gate else nearest}
        return preds,dict(gate=bool(gate),support=int(support),neff=neff,dmin=dmin,
                          median=median/10,candidate=mixed/10,disagreement=abs(mixed-median)/10,
                          nearest=self.cases.side.iloc[train[np.argmin(d)]],
                          neighbors="|".join(self.cases.side.iloc[train[neighbors]]),
                          weights="|".join(f"{v:.6f}" for v in weights))

    def ridge(self,i,groups,alpha):
        idx,_ = self.arrays(groups)
        x = self.x[idx]
        sd = x.std(0)
        sd[sd<1e-9]=1
        z = (x-x.mean(0))/sd
        y = self.y[idx]
        coef = np.linalg.solve(z.T@z+alpha*np.eye(z.shape[1]),z.T@(y-y.mean()))
        return int(grid(y.mean()+((self.x[i]-x.mean(0))/sd)@coef))

    def evaluate(self):
        rows, configs, split, cards = [],[],[],[]
        # Overlapping inner training sets have identical training data for a given held side.
        cached = {}
        for group in self.groups:
            groups = tuple(self.groups[self.groups!=group])
            held = np.flatnonzero(self.g==group)
            inner = [(i,tuple(g for g in groups if g!=self.g[i])) for i in np.flatnonzero(self.g!=group)]
            sums = np.zeros(len(CONFIGS),int)
            ridge_losses = np.zeros(3,int)
            for i,tr in inner:
                key = (i,tr)
                if key not in cached:
                    cached[key]=[self.predict(i,tr,c) for c in CONFIGS]
                sums += [abs(p["Full"]-self.y[i]) for p,_ in cached[key]]
                ridge_losses += [abs(self.ridge(i,tr,a)-self.y[i]) for a in (.1,1,10)]
            best = sums.argmin()
            config = CONFIGS[best]
            alpha = (.1,1,10)[ridge_losses.argmin()]
            for n,(cap,k,w) in enumerate(CONFIGS):
                configs.append(dict(group=group,cap=cap/10,k=k,weight=w,inner_sides=len(inner),
                                    inner_mae=sums[n]/(10*len(inner)),selected=n==best,ridge_alpha=alpha))
            residuals, mins, conf0 = [],[],[]
            for i,tr in inner:
                p,t = cached[i,tr][best]
                residuals.append(abs(p["Full"]-self.y[i])/10)
                mins.append(t["dmin"])
                conf0.append(confidence(t,config[1],np.inf))
            q80,q90 = np.quantile(residuals,[.8,.9])
            qd = np.quantile(mins,.95)
            qc = min(.35,np.quantile(conf0,.1))
            for i in held:
                p,t = self.predict(i,groups,config)
                p["Ridge"] = self.ridge(i,groups,alpha)
                for method,pred in p.items():
                    rows.append(dict(side=self.cases.side[i],group=group,reference=self.y[i]/10,
                                     method=method,prediction=pred/10,error=abs(pred-self.y[i])/10))
                point=p["Full"]/10
                conf=confidence(t,config[1],qd)
                reasons=[key for key,fired in (("low_support",t["neff"]<2),("distance",t["dmin"]>qd),
                         ("median_disagreement",t["disagreement"]>.4+1e-10),("score",conf<qc)) if fired]
                cards.append(dict(side=self.cases.side[i],group=group,**t,reference=self.y[i]/10,
                                  point=point,confidence=conf,review=bool(reasons),reasons="|".join(reasons),
                                  pressure_candidate=point,review_required=bool(reasons),
                                  advisory_warning="wide_empirical_interval" if 2*q90>.8+1e-10 else "",
                                  gate_name="rare-setting frequency gate",
                                  wide_warning=2*q90>.8+1e-10,low80=max(5,point-q80),high80=min(8,point+q80),
                                  low90=max(5,point-q90),high90=min(8,point+q90),q95_distance=qd,q10_score=qc))
            split.append(dict(test_group=group,train_groups="|".join(groups),test_sides="|".join(self.cases.side.iloc[held])))
        self.arrays.cache_clear()
        return map(pd.DataFrame,(rows,configs,split,cards))


def confidence(t,k,scale):
    return .45*np.exp(-t["dmin"]/max(scale,1e-9))+.35*t["neff"]/k+.20*(1-min(t["disagreement"]/.4,1))


if __name__ == "__main__":
    for cohort in ("primary","qualified","small_layout","unambiguous","speed08"):
        outputs = Study(cohort).evaluate()
        for name,frame in zip(("predictions","inner_selection","folds","cards"),outputs):
            frame.to_csv(OUT/f"{cohort}_{name}.csv",index=False)
