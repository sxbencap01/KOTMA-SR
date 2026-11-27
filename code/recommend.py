"""Research recommendation for a new, canonical geometry export, using the full historical library."""
import argparse
import json
from pathlib import Path
from common import OUT, CONFIG, sha
from evaluate import Study
from learning import tune
from geometry import represent, distance
from prepare import GEO
import numpy as np
import pandas as pd


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("geometry",type=Path,help="CSV columns PadID, PosX, PosY, SizeX, SizeY, Rotation")
    parser.add_argument("--dimensions",type=float,nargs=3,required=True,metavar=("L","W","H"))
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    frame=pd.read_csv(args.geometry)
    if not {"PadID",*GEO}<=set(frame.columns) or frame.empty or frame.PadID.duplicated().any():
        raise ValueError("A single layout with unique pad identifiers and complete geometry is required.")
    raw=frame.sort_values("PadID")[GEO].to_numpy(float)
    dims=np.asarray(args.dimensions)
    if not np.isfinite(raw).all() or not np.isfinite(dims).all() or (dims<=0).any() or (raw[:,2:4]<=0).any():
        raise ValueError("Geometry and dimensions must be finite, and sizes positive.")
    study=Study("primary")
    groups=tuple(study.groups)
    config=tune(study,groups)
    desc,representation=represent(raw,dims)
    sd=study.x.std(0)
    sd[sd<1e-9]=1
    descriptor=np.linalg.norm((study.x-desc)/sd,axis=1)
    with np.load(OUT/"private_pad_geometry.npz") as archive:
        costs=np.array([distance(representation,represent(archive[c.key],(c.L,c.W,c.H))[1])[0]
                        for c in study.cases.itertuples()])
    points,trace=study.predict(0,groups,config,structural=costs,descriptor=descriptor)
    result=dict(pressure_candidate=points["Full"]/10,advisory_warnings=[
        "historical observed geometry library","engineering units and layout revision require confirmation",
        "no prospective first-print validation"],review_required=True,
        gate_name="rare-setting frequency gate",config=dict(cap=config[0]/10,k=config[1],weight=config[2]),
        retrieval=trace,source_sha256=sha(args.geometry),conditions=CONFIG)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
