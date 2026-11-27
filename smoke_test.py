"""One-command end-to-end smoke test for KOTMA-SR on the 8-board synthetic demo.

Exercises the exact core pipeline without any proprietary customer data:
  1. Read-only SQLite ingestion & single-board unique-pad deduplication (code/prepare.py)
  2. 12-D descriptor extraction, M<=80 super-node coarsening, and POT FGW matching (code/geometry.py)
  3. Physical-board grouped nested LOBO validation & rare-setting frequency gate (code/evaluate.py)
  4. Tabular ML baselines (CatBoost, ExtraTrees, Weighted kNN) under identical folds (code/benchmark.py)
  5. Recommendation card generation for a new canonical pad CSV (code/recommend.py)
  6. Pre-print CAD vs observed SPI equivalence & outer-fold replay (audit/compare_preprint.py)

Usage:
  python smoke_test.py
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
SYN_DIR = ROOT / "data" / "synthetic_demo_8boards"
OUT_DIR = ROOT / "smoke_out"


def run_step(label: str, cmd: list[str], env: dict[str, str]) -> None:
    print(f"[STEP] {label}...")
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        print("STDOUT:\n", proc.stdout)
        print("STDERR:\n", proc.stderr)
        raise SystemExit(f"FAILED at step: {label} (exit {proc.returncode})")
    print(f"  -> OK")


def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["KOTMA_ROOT"] = str(ROOT)
    env["KOTMA_CONFIG"] = str(ROOT / "config.json")
    env["KOTMA_DB"] = str(SYN_DIR / "synthetic_demo.db")
    env["KOTMA_OUT"] = str(OUT_DIR)
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"

    py = sys.executable

    # 1. Deduplication & schema audit
    run_step("1/6 Single-board unique-pad deduplication (prepare.py)", [py, str(ROOT / "code" / "prepare.py")], env)
    cases = pd.read_csv(OUT_DIR / "cases.csv")
    assert len(cases) == 12 and cases["group"].nunique() == 8, f"Expected 12 sides / 8 boards, got {len(cases)} / {cases['group'].nunique()}"

    # 2. 12-D descriptors + M<=80 coarsening + POT FGW pairwise costs
    run_step("2/6 Descriptors & POT FGW geometry costs (geometry.py)", [py, str(ROOT / "code" / "geometry.py")], env)
    pair_audit = pd.read_csv(OUT_DIR / "pair_audit.csv")
    assert len(pair_audit) == 12 * 11 // 2
    assert pair_audit["marginal_error"].max() <= 1e-5
    assert pair_audit["outer_error"].max() <= 1e-9

    # 3. Physical-board grouped nested LOBO CV (primary cohort)
    run_step(
        "3/6 Physical-board grouped nested LOBO CV (evaluate.py)",
        [
            py,
            "-c",
            "import sys; sys.path.insert(0, r'" + str(ROOT / "code") + "'); "
            "from common import OUT; from evaluate import Study; "
            "outs = Study('primary').evaluate(); "
            "[f.to_csv(OUT / f'primary_{n}.csv', index=False) for n, f in zip(('predictions','inner_selection','folds','cards'), outs)]",
        ],
        env,
    )
    preds = pd.read_csv(OUT_DIR / "primary_predictions.csv")
    cards = pd.read_csv(OUT_DIR / "primary_cards.csv")
    assert len(cards) == 12
    assert int(cards["gate"].sum()) >= 1, "Expected rare-setting frequency gate (s_i < 3) to fire on rare synthetic board"

    # 4. Tabular ML baselines (CatBoost, ExtraTrees, Weighted kNN)
    run_step(
        "4/6 Matched tabular ML baselines (benchmark.py)",
        [
            py,
            "-c",
            "import sys; sys.path.insert(0, r'" + str(ROOT / "code") + "'); "
            "from benchmark import run_cohort; run_cohort('primary')",
        ],
        env,
    )
    bench = pd.read_csv(OUT_DIR / "benchmark_predictions.csv")
    assert set(["CatBoost", "ExtraTrees", "Weighted kNN"]).issubset(set(bench["method"].unique()))

    # 5. New-board CLI recommendation card
    rec_json = OUT_DIR / "demo_recommendation.json"
    run_step(
        "5/6 New-board CLI recommendation (recommend.py)",
        [
            py,
            str(ROOT / "code" / "recommend.py"),
            str(SYN_DIR / "synthetic_preprint_S01.csv"),
            "--dimensions",
            "220",
            "160",
            "1.6",
            "--output",
            str(rec_json),
        ],
        env,
    )
    rec = json.loads(rec_json.read_text(encoding="utf-8"))
    assert 5.0 <= rec["pressure_candidate"] <= 8.0

    # 6. Pre-print CAD vs SPI equivalence audit
    pre_out = OUT_DIR / "preprint_audit"
    run_step(
        "6/6 Pre-print CAD vs observed SPI audit (compare_preprint.py)",
        [
            py,
            str(ROOT / "audit" / "compare_preprint.py"),
            str(SYN_DIR / "synthetic_preprint_manifest.json"),
            str(pre_out),
        ],
        env,
    )
    pre_summary = json.loads((pre_out / "comparison.json").read_text(encoding="utf-8"))
    assert pre_summary["observed_match_fraction"] == 1.0

    # Print clean summary table
    mae_tbl = preds.groupby("method")["error"].mean().sort_values()
    bench_tbl = bench.groupby("method")["error"].mean().sort_values()
    print("\n=== SYNTHETIC 8-BOARD (12-SIDE) SMOKE TEST SUMMARY ===")
    print(f"Rare-setting gate activations: {int(cards['gate'].sum())}/12 sides")
    print(f"FGW max marginal err: {pair_audit['marginal_error'].max():.2e}, max outer err: {pair_audit['outer_error'].max():.2e}")
    print(f"CLI recommendation candidate for S01 preprint: {rec['pressure_candidate']:.1f} kgf")
    print(f"Pre-print CAD vs SPI replay delta: {pre_summary['frozen_outer_fold_replay']['delta']:+.1f} kgf")
    print("LOBO MAE (kgf) — Core & Controls:")
    for m, v in mae_tbl.items():
        print(f"  {m:18s}: {v:.4f}")
    print("LOBO MAE (kgf) — Tabular ML Baselines:")
    for m, v in bench_tbl.items():
        print(f"  {m:18s}: {v:.4f}")
    print("ALL 6 SMOKE-TEST CHECKS PASSED!")


if __name__ == "__main__":
    main()
