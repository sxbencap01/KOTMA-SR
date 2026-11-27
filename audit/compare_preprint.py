"""Compare a documented pre-print export (one layout, in the verified common coordinate frame)
with one frozen observed layout. Evidence of availability must be checked independently.
Usage: python compare_preprint.py export_manifest.json output_directory
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "code"))
from common import DB, OUT, CONFIG, sha
from geometry import represent, distance
from prepare import GEO
from evaluate import Study
import numpy as np
import pandas as pd
from scipy.stats import wasserstein_distance

DESCRIPTORS = ("log_count","log_L","log_W","log_H","area_mean","area_sd","AR_mean","AR_sd",
               "aspect_mean","aspect_sd","x_extent","y_extent")
NODE_FEATURES = ("relative_size_x","relative_size_y","angle","relative_area","area_ratio","aspect_ratio",
                 "fill_risk_proxy","release_risk_proxy")


def observed_pads(con, code, archived_geometry):
    mapping = pd.read_csv(OUT/"private_cohort_audit.csv").set_index("code")
    fields = ["PadID",*GEO]
    f = pd.read_sql_query("select PCBID, PadID, PosX, PosY, SizeX, SizeY, Rotation from print_spi where no=?",
                          con,params=(mapping.loc[code,"side"],))
    for _,instance in f.groupby("PCBID",sort=True):
        p = instance[fields].drop_duplicates().sort_values("PadID")
        if np.array_equal(p[GEO].to_numpy(),archived_geometry):
            return p
    raise ValueError("No single inspection matches the selected frozen layout; resolve revision before comparing.")


def compare(manifest, dest):
    meta = json.loads(manifest.read_text(encoding="utf-8-sig"))
    for key in ("side","layout_key","revision","evidence_ref","coordinate_mapping_ref","length_unit",
                "angle_convention","pad_id_mapping_ref","source_sha256"):
        if not str(meta.get(key) or "").strip():
            raise ValueError(f"Missing evidence field {key}")
    if meta.get("preprint_available_at") or meta.get("first_print_at"):
        before,first=(pd.Timestamp(meta.get(key)) for key in ("preprint_available_at","first_print_at"))
        if pd.isna(before) or pd.isna(first) or before.tzinfo is None or first.tzinfo is None or before>=first:
            raise ValueError("Timestamp evidence must identify availability before first print.")
    elif not str(meta.get("documented_preprint_order_ref") or "").strip():
        raise ValueError("Provide either dated records or a traceable document establishing precedence for this revision.")
    file = manifest.parent/meta["csv"]
    if sha(file)!=meta["source_sha256"]:
        raise ValueError("Supplied export differs from the manifest hash.")
    raw = pd.read_csv(file)
    cols = ["PadID",*GEO]
    if raw.empty or not set(cols)<=set(raw.columns):
        raise ValueError("One nonempty, canonical pad layout is required.")
    raw = raw[cols].apply(pd.to_numeric,errors="raise").sort_values("PadID")
    dims = np.asarray(meta["board_dimensions"],float)
    if (dims.shape!=(3,) or not np.isfinite(dims).all() or (dims<=0).any() or
        not np.isfinite(raw.to_numpy()).all() or raw.PadID.duplicated().any() or
        (raw.PadID % 1 != 0).any() or (raw[["SizeX","SizeY"]]<=0).any().any()):
        raise ValueError("Invalid dimensions, pad keys or numerical geometry.")
    cases = pd.read_csv(OUT/"cases.csv").set_index("key")
    key,side = meta["layout_key"],meta["side"]
    case = cases.loc[key]
    if side!=case.side:
        raise ValueError("Side / layout mismatch.")
    with np.load(OUT/"private_pad_geometry.npz") as archive:
        geometry = archive[key]
    with closing(sqlite3.connect(DB.as_uri()+"?mode=ro",uri=True)) as con:
        observed = observed_pads(con,side,geometry)
    pads = observed.merge(raw,on="PadID",how="outer",indicator=True,suffixes=("_spi","_preprint"))
    both = pads._merge.eq("both")
    if not both.any():
        raise ValueError("Zero matched canonical pad IDs. Supply an independently checked ID crosswalk.")
    for field in GEO:
        diff = pads[field+"_preprint"]-pads[field+"_spi"]
        pads[field+"_abs_diff"] = (((diff+180)%360)-180).abs() if field=="Rotation" else diff.abs()
    orig,rep_obs = represent(geometry,(case.L,case.W,case.H))
    new,rep_pre = represent(raw[GEO].to_numpy(),dims)
    # Same-side entropic costs can be nonzero; publish both self-costs alongside the cross-cost.
    cross_cost = distance(rep_obs,rep_pre)[0]
    # Node labels are arbitrary between independent clusterings. Compare distributions
    # in the actual standardized and weighted FGW feature space, without an ID match.
    node_differences = [
        wasserstein_distance(rep_obs[1][:,j],rep_pre[1][:,j],rep_obs[2],rep_pre[2])
        for j in range(len(NODE_FEATURES))
    ]
    result = dict(side=side,layout=key,revision=meta["revision"],input_sha256=sha(file),
                  manifest_sha256=sha(manifest),joined=int(both.sum()),observed=len(observed),preprint=len(raw),
                  observed_match_fraction=both.sum()/len(observed),preprint_match_fraction=both.sum()/len(raw),
                  observed_dimensions=[case.L,case.W,case.H],preprint_dimensions=dims.tolist(),
                  cross_cost=cross_cost,observed_self_cost=distance(rep_obs,rep_obs)[0],
                  preprint_self_cost=distance(rep_pre,rep_pre)[0],
                  thickness_assumption_in_model=CONFIG["stencil_thickness_assumed"],
                  status="numerical comparison; referenced engineering evidence requires independent review")
    study = Study("primary")
    selected = study.cases.index[study.cases.side.eq(side)]
    if len(selected)!=1 or study.cases.loc[selected[0],"key"]!=key:
        raise ValueError("Decision replay requires the exact layout used by the primary cohort.")
    i = int(selected[0])
    group = study.g[i]
    groups = tuple(g for g in study.groups if g!=group)
    train, _ = study.arrays(groups)
    parameters = pd.read_csv(OUT/"primary_inner_selection.csv").query("selected").set_index("group").loc[group]
    cfg = (round(parameters.cap*10),int(parameters.k),parameters.weight)
    scale = study.x[train].std(0)
    scale[scale<1e-9]=1
    descriptor = np.linalg.norm((study.x[train]-new)/scale,axis=1)
    with np.load(OUT/"private_pad_geometry.npz") as archive:
        costs = np.array([distance(rep_pre,represent(archive[c.key],(c.L,c.W,c.H))[1])[0]
                          for c in study.cases.iloc[train].itertuples()])
    clean,clean_trace = study.predict(i,groups,cfg)
    changed,changed_trace = study.predict(i,groups,cfg,structural=costs,descriptor=descriptor)
    result["frozen_outer_fold_replay"] = dict(clean_pressure=clean["Full"]/10,
        preprint_pressure=changed["Full"]/10,delta=(changed["Full"]-clean["Full"])/10,
        clean_gate=clean_trace["gate"],preprint_gate=changed_trace["gate"],
        clean_nearest=clean_trace["nearest"],preprint_nearest=changed_trace["nearest"],
        clean_continuous=clean_trace["candidate"],preprint_continuous=changed_trace["candidate"])
    dest.mkdir(parents=True,exist_ok=True)
    pads.to_csv(dest/"private_paired_geometry.csv",index=False)
    pd.DataFrame(dict(feature=DESCRIPTORS,observed=orig,preprint=new,delta=new-orig)).to_csv(dest/"descriptor_difference.csv",index=False)
    pd.DataFrame(dict(feature=NODE_FEATURES,mass_weighted_wasserstein=node_differences)).to_csv(
        dest/"node_feature_difference.csv",index=False)
    (dest/"comparison.json").write_text(json.dumps(result,indent=2),encoding="utf-8")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest",type=Path)
    parser.add_argument("output_directory",type=Path)
    args=parser.parse_args()
    compare(args.manifest,args.output_directory)
