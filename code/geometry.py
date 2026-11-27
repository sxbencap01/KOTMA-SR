"""Strict, geometry-only distances. No pressure or inspection outcome enters a pair cost."""
from common import OUT, sha, write_json
from types import SimpleNamespace
import warnings
import numpy as np
import pandas as pd
import ot
from scipy.spatial.distance import cdist
from primitives import GeometryEngine, board_descriptor
from common import CONFIG

ENGINE = GeometryEngine(base_k=80)


def represent(raw, dims, nodes=80):
    x, y, a, b, angle = raw.T
    L, W, _ = dims
    t = float(CONFIG["stencil_thickness_assumed"])
    comp = np.column_stack((x/L, y/W, a/L, b/W, angle/360,
                            (a/L)*(b/W), a*b/(2*(a+b)*t+1e-9), np.minimum(a,b)/(t+1e-9)))
    desc = board_descriptor(SimpleNamespace(comps_raw=comp, board_dim=dims))
    pos, feat, mass = ENGINE.coarsen_pcb(comp, n_clusters=nodes, seed=2026)
    geometry = cdist(pos,pos,"sqeuclidean")
    return desc, (geometry/(geometry.max()+1e-9), feat*ENGINE._feature_weight_vector(8), mass/mass.sum())


def distance(left, right):
    c1, a, p = left
    c2, b, q = right
    cost = cdist(a,b,"sqeuclidean")
    heterogeneity = (p.std()*np.sqrt(len(p))+q.std()*np.sqrt(len(q)))/2
    alpha = 0.3+0.6*np.clip(heterogeneity/.5,0,1)
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        value, log = ot.gromov.entropic_fused_gromov_wasserstein2(
            cost/(cost.max()+1e-9), c1,c2,p,q,loss_fun="square_loss",
            alpha=alpha,epsilon=.05,max_iter=1000,tol=1e-9,numItermax=2000,stopThr=1e-5,log=True)
    plan = log["T"] if "T" in log else log["G"]
    residual = max(abs(plan.sum(1)-p).max(),abs(plan.sum(0)-q).max())
    err = log["err"][-1]
    if not np.isfinite([value,residual,err]).all() or residual>1e-5 or err>1e-9:
        raise RuntimeError(f"FGW convergence failure: value={value}, marginal={residual}, error={err}")
    return float(value),float(residual),float(err)," | ".join(sorted({str(w.message) for w in recorded}))


def main():
    cases = pd.read_csv(OUT/"cases.csv")
    desc, reps, rows = [], [], []
    with np.load(OUT/"private_pad_geometry.npz") as data:
        for c in cases.itertuples():
            x, rep = represent(data[c.key], (c.L,c.W,c.H))
            desc.append(x)
            reps.append(rep)
    mat = np.zeros((len(desc),len(desc)))
    for i in range(len(desc)):
        for j in range(i):
            d,res,err,warn = distance(reps[i],reps[j])
            mat[i,j] = mat[j,i] = d
            rows.append((cases.key[i],cases.key[j],d,res,err,warn))
    pd.DataFrame(rows,columns=["left","right","distance","marginal_error","outer_error","warnings"]).to_csv(OUT/"pair_audit.csv",index=False)
    np.savez_compressed(OUT/"geometry_costs.npz", keys=cases.key.to_numpy(str),desc=desc,mat=mat)
    write_json("geometry_manifest.json", {"source":sha(OUT/"private_pad_geometry.npz"),"POT":ot.__version__,"pairs":len(rows),"fallback":False})


if __name__ == "__main__":
    main()
