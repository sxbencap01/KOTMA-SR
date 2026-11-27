"""Audit source tables and extract one copy of each pad definition. Read-only DB."""
from common import DB, OUT, sha, write_json
from contextlib import closing
import sqlite3
import numpy as np
import pandas as pd

GEO = ["PosX", "PosY", "SizeX", "SizeY", "Rotation"]
PARAM = ["press", "out", "length", "width", "height"]


def prepare():
    layouts, cases, archives, detail = [], [], {}, []
    with closing(sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("pragma query_only=on")
        schema = pd.read_sql_query("select name,sql from sqlite_master where type='table'", db)
        schema.to_csv(OUT / "schema.csv", index=False)
        recipes = pd.read_sql_query('select no,press,"out",length,width,height,partNumber,label,JudgeRes from printdb order by no', db)
        assert recipes.no.is_unique
        labels = pd.read_sql_query("select JudgeRes,count(*) as n from print_spi group by JudgeRes", db)
        labels.to_csv(OUT / "inspection_labels.csv", index=False)
        for number, recipe in recipes.iterrows():
            side = recipe.no
            q = 'select PCBID, PadID, PosX,PosY,SizeX,SizeY,Rotation,press,"out",length,width,height from print_spi where no=?'
            f = pd.read_sql_query(q, db, params=(side,))
            if f.empty:
                detail.append(dict(side=side, status="recipe_only",rows=0))
                continue
            pars = f[PARAM].drop_duplicates()
            assert len(pars) == 1 and np.allclose(pars.iloc[0], recipe[PARAM].to_numpy(float))
            assert not f.isna().any().any() and np.isfinite(f.to_numpy(float)).all()
            assert (f[["SizeX","SizeY","length","width","height"]] > 0).all().all()
            unique = f[["PadID", *GEO]].drop_duplicates()
            collision = int(unique.PadID.duplicated(keep=False).groupby(unique.PadID).any().sum())
            # If a pad identifier changes meaning, use observed complete instance layouts.
            # Identical input rows in different inspections must not reweight the geometry.
            variations = {}
            for instance, g in f.groupby("PCBID",sort=True):
                pad = g[["PadID", *GEO]].drop_duplicates().sort_values("PadID")
                assert pad.PadID.is_unique
                key = pad.to_numpy(dtype="<f8").tobytes()
                variations.setdefault(key, []).append(int(instance))
            side_code = f"S{number+1:02d}"
            group = side.rsplit("-", 1)[0]
            codes = sorted(variations, key=lambda b: (len(b),b))
            if not collision:
                sources = [(unique.sort_values("PadID"), "clear")]
            else:
                sources = [(pd.DataFrame(np.frombuffer(b,dtype="<f8").reshape(-1,6),columns=["PadID",*GEO]),f"layout{i+1}") for i,b in enumerate(codes)]
            for i,b in enumerate(codes):
                layouts.append(dict(side=side_code,unique_layout=i+1,pads=len(b)//48,
                                    instances=len(variations[b]),min_pcbid=min(variations[b]),max_pcbid=max(variations[b])))
            for pads, version in sources:
                key = side_code+"_"+version
                archives[key] = pads[GEO].to_numpy(float)
                cases.append(dict(side=side_code,group=group,layout=version,key=key,pressure=recipe.press,
                                  speed=recipe["out"],L=recipe.length,W=recipe.width,H=recipe.height,
                                  pads=len(pads),label=int(recipe.label),recipe_judge=float(recipe.JudgeRes)))
            detail.append(dict(side=side,code=side_code,status="layout_conflict" if collision else "matched",
                               rows=len(f),pcbid=f.PCBID.nunique(),pad_ids=f.PadID.nunique(),pad_definitions=len(unique),
                               conflicting_pad_ids=collision,observed_layouts=len(variations),
                               duplicate_instance_pad_rows=int(f.duplicated(["PCBID","PadID"]).sum()),
                               pressure=recipe.press,speed=recipe["out"],partNumber=recipe.partNumber,
                               printdb_label=recipe.label))
        missed = db.execute("select no from print_spi except select no from printdb").fetchall()
        assert not missed
    pd.DataFrame(detail).to_csv(OUT/"private_cohort_audit.csv",index=False)
    pd.DataFrame(layouts).to_csv(OUT/"instance_layout_counts.csv",index=False)
    index = pd.DataFrame(cases)
    index["group"] = index.group.map({v:f"B{i+1:02d}" for i,v in enumerate(sorted(index.group.unique()))})
    index.to_csv(OUT/"cases.csv",index=False)
    np.savez_compressed(OUT/"private_pad_geometry.npz", **archives)
    write_json("input_manifest.json",dict(database=DB.name,sha256=sha(DB),size=DB.stat().st_size,
               archive_sha256=sha(OUT/"private_pad_geometry.npz"),recipes=len(recipes),
               input_columns=GEO, label="printdb.press verified against print_spi.press",
               pressure_unit="kgf",speed_unit="cm/s",length_unit="mm",stencil_thickness_mm=0.15))


if __name__ == "__main__":
    prepare()
