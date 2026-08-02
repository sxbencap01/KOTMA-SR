"""Regenerate manuscript figures from completed CSV artifacts.

This utility is used when figure styling changes but the numerical experiment
artifacts have already been produced. It avoids recomputing the expensive
nested validation and evidence suites while still exercising the publication
figure code in the same Python environment.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .data_loader import load_print_spi
from .otma_engine import OTMAConfig, OTMAEngine
from .supplementary_figures import generate_supplementary_figures
from .v1_figures import generate_profile_figures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate KOTMA-SR figures from existing CSV artifacts.")
    parser.add_argument("--db", required=True, help="Authorized local SMT database used to rebuild geometry objects for structural-memory figures.")
    parser.add_argument("--results", required=True, help="Existing result package directory containing the shared CSV artifacts.")
    parser.add_argument("--paper-profile", choices=["kbs", "jms", "both"], default="both")
    parser.add_argument("--base-k", type=int, default=80)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--fgw-device", choices=["auto", "cpu", "cuda"], default="cpu")
    return parser.parse_args()


def read_csv(shared: Path, name: str) -> pd.DataFrame:
    path = shared / name
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return pd.read_csv(path)


def load_artifacts(shared: Path) -> dict[str, pd.DataFrame]:
    pcb_summary = read_csv(shared, "pcb_group_lobo_primary_statistics.csv")
    side_summary = read_csv(shared, "side_lobo_primary_statistics.csv")
    grouped_sample = read_csv(shared, "grouped_sample_efficiency.csv")
    return {
        "summary": pcb_summary,
        "results": read_csv(shared, "pcb_group_lobo_outer_results.csv"),
        "traces": read_csv(shared, "pcb_group_lobo_traces.csv"),
        "paired": read_csv(shared, "pcb_group_lobo_paired_statistics.csv"),
        "protocol_summary": pd.concat(
            [
                pcb_summary.assign(protocol="pcb_group_lobo"),
                side_summary.assign(protocol="side_lobo_diagnostic"),
            ],
            ignore_index=True,
        ),
        "cases": read_csv(shared, "action_case_table.csv"),
        "ablation": read_csv(shared, "clean_ablation_results.csv"),
        "robustness": read_csv(shared, "perturbation_robustness.csv"),
        "sample_efficiency": grouped_sample.rename(columns={"train_physical_boards": "train_boards"}),
        "negative_controls": read_csv(shared, "negative_control_results.csv"),
        "selective": read_csv(shared, "selective_risk_curve.csv"),
        "intervals": read_csv(shared, "interval_calibration_summary.csv"),
        "benchmark_summary": read_csv(shared, "benchmark_summary.csv"),
        "benchmark_paired": read_csv(shared, "benchmark_paired_statistics.csv"),
        "mechanism_cases": read_csv(shared, "mechanism_case_table.csv"),
        "gate_sensitivity": read_csv(shared, "gate_sensitivity.csv"),
        "robustness_v2": read_csv(shared, "robustness_suite.csv"),
        "conditional_intervals": read_csv(shared, "conditional_interval_calibration.csv"),
        "velocity_policy": read_csv(shared, "velocity_policy_summary.csv"),
        "exploratory_gnn": read_csv(shared, "exploratory_gnn_results.csv"),
        "interval_comparators": read_csv(shared, "interval_comparator_summary.csv"),
    }


def qa_figures(profile: str, figure_dir: Path) -> pd.DataFrame:
    manifest = pd.read_csv(figure_dir / "figure_manifest.csv")
    rows = []
    for _, row in manifest.iterrows():
        source = figure_dir / row["source_data"]
        source_rows = len(pd.read_csv(source)) if source.exists() else 0
        rows.append(
            {
                "profile": profile,
                "figure": row["figure"],
                "source_rows": source_rows,
                "all_exports_exist": int(all(int(row[col]) == 1 for col in ["svg_exists", "pdf_exists", "tiff_exists", "png_exists"])),
                "source_nonempty": int(source_rows > 0),
                "qa_status": "pass" if source_rows > 0 and all(int(row[col]) == 1 for col in ["svg_exists", "pdf_exists", "tiff_exists", "png_exists"]) else "risk",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    results = Path(args.results)
    shared = results / "shared"
    engine = OTMAEngine(OTMAConfig(base_k=args.base_k, require_pot=True, compute_device=args.device, fgw_device=args.fgw_device))
    records = load_print_spi(args.db, ot_engine=engine, base_k=args.base_k, precompute_stability=False)
    artifacts = load_artifacts(shared)

    profiles = ["kbs", "jms"] if args.paper_profile == "both" else [args.paper_profile]
    qa_rows = []
    for profile in profiles:
        figure_dir = results / f"figures_{profile}"
        generate_profile_figures(profile, records, artifacts, figure_dir, engine=engine)
        qa_rows.append(qa_figures(profile, figure_dir))

    supplementary_dir = results / "supplementary_figures"
    generate_supplementary_figures(artifacts, supplementary_dir)
    qa_rows.append(qa_figures("supplementary", supplementary_dir))

    figure_qa = pd.concat(qa_rows, ignore_index=True)
    figure_qa.to_csv(results / "figure_qa_audit.csv", index=False)
    print(f"Regenerated figures in {results}")
    print(f"Figure QA pass: {int(figure_qa['qa_status'].eq('pass').sum())}/{len(figure_qa)}")


if __name__ == "__main__":
    main()
