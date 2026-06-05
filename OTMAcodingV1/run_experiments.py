"""Run V1 leakage-safe recommendation experiments and manuscript figures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import pickle
import platform
import sys

import numpy as np
import pandas as pd

try:
    from .data_loader import load_print_spi, write_data_inventory
    from .db_audit import audit_database, audit_database_fast
    from .otma_engine import OTMAConfig, OTMAEngine
    from .v1_evaluation import (
        evaluate_clean_ablations,
        evaluate_explanations_and_robustness,
        evaluate_negative_controls,
        evaluate_sample_efficiency,
        evaluate_strict_nested_lobo,
        summarize_interval_calibration,
        selective_risk_curve,
        write_action_case_table,
    )
    from .v1_figures import generate_profile_figures
    from .baseline_suite import evaluate_baseline_suite
    from .evidence_suite import (
        evaluate_gate_sensitivity,
        evaluate_grouped_sample_efficiency,
        evaluate_interval_comparators,
        evaluate_robustness_suite,
        mechanism_strata,
        summarize_conditional_intervals,
        summarize_velocity_policy,
    )
    from .exploratory_gnn import evaluate_exploratory_gnn
    from .grouped_evaluation import evaluate_grouped_nested
    from .prospective_eval import evaluate_engineer_review_csv, evaluate_prospective_csv, write_collection_templates
    from .supplementary_figures import generate_supplementary_figures
except ImportError:
    from data_loader import load_print_spi, write_data_inventory
    from db_audit import audit_database, audit_database_fast
    from otma_engine import OTMAConfig, OTMAEngine
    from v1_evaluation import evaluate_clean_ablations, evaluate_explanations_and_robustness, evaluate_negative_controls, evaluate_sample_efficiency, evaluate_strict_nested_lobo, selective_risk_curve, summarize_interval_calibration, write_action_case_table
    from v1_figures import generate_profile_figures
    from baseline_suite import evaluate_baseline_suite
    from evidence_suite import evaluate_gate_sensitivity, evaluate_grouped_sample_efficiency, evaluate_interval_comparators, evaluate_robustness_suite, mechanism_strata, summarize_conditional_intervals, summarize_velocity_policy
    from exploratory_gnn import evaluate_exploratory_gnn
    from grouped_evaluation import evaluate_grouped_nested
    from prospective_eval import evaluate_engineer_review_csv, evaluate_prospective_csv, write_collection_templates
    from supplementary_figures import generate_supplementary_figures


def parse_args():
    parser = argparse.ArgumentParser(description="Run trustworthy KOTMA-SR retrospective validation.")
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--db", default=str(root / "test.db"))
    parser.add_argument("--output", default=str(root / "OTMA_V1_Results"))
    parser.add_argument("--paper-profile", choices=["kbs", "jms", "both"], default="both")
    parser.add_argument("--strict-nested-lobo", action="store_true", help="Document that manuscript-mode strict nested LOBO is requested.")
    parser.add_argument("--smoke", action="store_true", help="Use a bounded subset for pipeline validation only.")
    parser.add_argument("--base-k", type=int, default=80)
    parser.add_argument("--max-outer-boards", type=int, default=None)
    parser.add_argument("--max-inner-boards", type=int, default=None)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--fgw-device", choices=["auto", "cpu", "cuda"], default="cpu", help="Use CPU by default: POT FGW is faster on these small graph pairs.")
    parser.add_argument("--full-db-audit", action="store_true", help="Run expensive all-table distinct and join audits.")
    parser.add_argument("--legacy-side-primary", action="store_true", help="Use the legacy side-level primary analysis instead of physical-board grouped LOBO.")
    parser.add_argument("--skip-extended-benchmarks", action="store_true")
    parser.add_argument("--skip-full-robustness", action="store_true")
    parser.add_argument("--run-exploratory-gnn", action="store_true")
    parser.add_argument("--resume-prebenchmark", action="store_true", help="Reuse completed pre-benchmark CSV artifacts from the output directory.")
    parser.add_argument("--prospective-csv", default=None)
    parser.add_argument("--engineer-review-csv", default=None)
    return parser.parse_args()


def _save_fgw_cache(engine, shared: Path) -> None:
    cache = getattr(engine, "fgw_pair_cache", {})
    with (shared / "fgw_pair_cache.pkl").open("wb") as handle:
        pickle.dump(cache, handle, protocol=pickle.HIGHEST_PROTOCOL)


def _load_fgw_cache(engine, shared: Path) -> int:
    path = shared / "fgw_pair_cache.pkl"
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        cache = pickle.load(handle)
    engine.fgw_pair_cache.update(cache)
    return len(cache)


def _load_prebenchmark_artifacts(shared: Path) -> dict[str, pd.DataFrame]:
    pcb_summary = pd.read_csv(shared / "pcb_group_lobo_primary_statistics.csv")
    side_summary = pd.read_csv(shared / "side_lobo_primary_statistics.csv")
    grouped_sample_efficiency = pd.read_csv(shared / "grouped_sample_efficiency.csv")
    return {
        "results": pd.read_csv(shared / "pcb_group_lobo_outer_results.csv"),
        "traces": pd.read_csv(shared / "pcb_group_lobo_traces.csv"),
        "summary": pcb_summary,
        "paired": pd.read_csv(shared / "pcb_group_lobo_paired_statistics.csv"),
        "protocol_summary": pd.concat(
            [
                pcb_summary.assign(protocol="pcb_group_lobo"),
                side_summary.assign(protocol="side_lobo_diagnostic"),
            ],
            ignore_index=True,
        ),
        "ablation": pd.read_csv(shared / "clean_ablation_results.csv"),
        "robustness": pd.read_csv(shared / "perturbation_robustness.csv"),
        "intervals": pd.read_csv(shared / "interval_calibration_summary.csv"),
        "selective": pd.read_csv(shared / "selective_risk_curve.csv"),
        "cases": pd.read_csv(shared / "action_case_table.csv"),
        "mechanism_cases": pd.read_csv(shared / "mechanism_case_table.csv"),
        "mechanism_summary": pd.read_csv(shared / "mechanism_strata_summary.csv"),
        "pressure_bins": pd.read_csv(shared / "pressure_bin_summary.csv"),
        "gate_sensitivity": pd.read_csv(shared / "gate_sensitivity.csv"),
        "conditional_intervals": pd.read_csv(shared / "conditional_interval_calibration.csv"),
        "interval_comparators": pd.read_csv(shared / "interval_comparator_summary.csv"),
        "grouped_sample_efficiency": grouped_sample_efficiency,
        "sample_efficiency": grouped_sample_efficiency.rename(columns={"train_physical_boards": "train_boards"}),
        "negative_controls": pd.read_csv(shared / "negative_control_results.csv"),
        "robustness_v2": pd.read_csv(shared / "robustness_suite.csv"),
        "velocity_policy": pd.read_csv(shared / "velocity_policy_summary.csv"),
    }


def _dependency_versions() -> dict:
    import matplotlib
    import pandas
    import scipy
    import seaborn
    import sklearn
    import ot

    return {
        "python": platform.python_version(),
        "executable": sys.executable,
        "numpy": np.__version__,
        "pandas": pandas.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "matplotlib": matplotlib.__version__,
        "seaborn": seaborn.__version__,
        "pot": getattr(ot, "__version__", "installed"),
    }


def _readiness_audit(artifacts: dict[str, pd.DataFrame], smoke: bool) -> pd.DataFrame:
    summary = artifacts["summary"].set_index("method")
    main = summary.loc["KOTMA-SR"] if "KOTMA-SR" in summary.index else pd.Series(dtype=float)
    paired = artifacts["paired"]
    paired_cbr = paired.loc[paired["comparator"] == "CBR"]
    paired_cbr = paired_cbr.iloc[0] if not paired_cbr.empty else pd.Series(dtype=float)
    ablation = artifacts["ablation"].groupby("method")["pressure_abs_error_raw"].mean()
    descriptor = float(ablation.get("Descriptor CBR", np.nan))
    full = float(ablation.get("Sparse-tail correction", np.nan))
    better_window_methods = summary.index[
        summary["within_0_4_raw_rate"].fillna(-np.inf) > float(main.get("within_0_4_raw_rate", np.nan))
    ].tolist()
    benchmark = artifacts.get("benchmark_summary", pd.DataFrame())
    benchmark = benchmark.loc[benchmark["method"] != "KOTMA-SR"] if "method" in benchmark else pd.DataFrame()
    best_baseline = benchmark.sort_values("pressure_mae_raw").iloc[0] if not benchmark.empty else pd.Series(dtype=float)
    benchmark_paired = artifacts.get("benchmark_paired", pd.DataFrame())
    paired_best = benchmark_paired.loc[benchmark_paired["comparator"] == best_baseline.get("method", "")]
    paired_best = paired_best.iloc[0] if not paired_best.empty else pd.Series(dtype=float)
    rows = [
        {
            "criterion": "physical_board_grouped_nested_lobo",
            "status": "smoke_only" if smoke else "pass",
            "evidence": "Outer folds hold out both A/B sides of each physical board; held-out boards are excluded from tuning, scaling and calibration.",
            "claim_action": "Use manuscript claims only for a complete non-smoke run.",
        },
        {
            "criterion": "strong_baseline_benchmark",
            "status": "candidate" if float(main.get("pressure_mae_raw", np.inf)) <= float(best_baseline.get("pressure_mae_raw", -np.inf)) else "risk",
            "evidence": (
                f"KOTMA-SR MAE={main.get('pressure_mae_raw', np.nan):.4g}; "
                f"best non-KOTMA-SR baseline={best_baseline.get('method', 'unavailable')} "
                f"MAE={best_baseline.get('pressure_mae_raw', np.nan):.4g}; "
                f"paired advantage={paired_best.get('mean_advantage_raw', np.nan):.4g}."
            ),
            "claim_action": "Claim broad superiority only when the grouped benchmark supports it; otherwise present the method as a trustworthy selective strategy with explicit trade-offs.",
        },
        {
            "criterion": "engineering_usability",
            "status": "pass" if float(main.get("accepted_within_0_4_rate", np.nan)) >= 0.85 else "risk",
            "evidence": f"accepted coverage={main.get('accepted_coverage', np.nan):.3g}; accepted within +/-0.4={main.get('accepted_within_0_4_rate', np.nan):.3g}.",
            "claim_action": "Claim trustworthy selective recommendation only if accepted coverage and usability remain adequate.",
        },
        {
            "criterion": "bounded_structural_correction",
            "status": "candidate" if np.isfinite(full) and np.isfinite(descriptor) and full < descriptor else "demote",
            "evidence": f"descriptor CBR MAE={descriptor:.4g}; bounded sparse-tail correction MAE={full:.4g}.",
            "claim_action": "Describe FGW as a bounded sparse-tail correction unless paired analysis supports a stronger claim.",
        },
        {
            "criterion": "paired_cbr_evidence",
            "status": "pass" if float(paired_cbr.get("cluster_bootstrap_ci_low", paired_cbr.get("bootstrap_ci_low", np.nan))) > 0 else "risk",
            "evidence": (
                f"mean MAE advantage={paired_cbr.get('mean_advantage_raw', np.nan):.4g}; "
                f"side-level Wilcoxon p={paired_cbr.get('p_wilcoxon', np.nan):.4g}; "
                f"physical-board cluster-bootstrap CI=[{paired_cbr.get('cluster_bootstrap_ci_low', paired_cbr.get('bootstrap_ci_low', np.nan)):.4g}, "
                f"{paired_cbr.get('cluster_bootstrap_ci_high', paired_cbr.get('bootstrap_ci_high', np.nan)):.4g}]."
            ),
            "claim_action": "Use the physical-board cluster-bootstrap interval as primary inference and report the side-level Wilcoxon test as a supplementary diagnostic.",
        },
        {
            "criterion": "universal_metric_dominance",
            "status": "prohibited" if better_window_methods else "candidate",
            "evidence": f"Methods with higher within +/-0.4 recovery than KOTMA-SR: {better_window_methods or 'none'}.",
            "claim_action": "Do not claim superiority on every metric; state the primary MAE endpoint and trade-offs explicitly.",
        },
        {
            "criterion": "current_database_only_scope",
            "status": "limitation",
            "evidence": "All experiments are intentionally restricted to the current local historical database. The available database has no usable acquisition timestamp, batch-time or site field for a defensible temporal or external split.",
            "claim_action": "State the single-database retrospective scope explicitly. Do not fabricate temporal ordering or present prospective/external validation as completed evidence.",
        },
        {
            "criterion": "future_deployment_validation",
            "status": "future_work",
            "evidence": "Engineer-supervised prospective verification and external-site validation require data outside the declared current-database-only experiment scope.",
            "claim_action": "Describe these as future deployment-validation directions, not as missing experiments within the present retrospective study.",
        },
        {
            "criterion": "quality_optimization_claim",
            "status": "prohibited",
            "evidence": "Each board has one historically executed setting; counterfactual quality is unavailable.",
            "claim_action": "Use recommendation, recovery and manual-review language only.",
        },
    ]
    return pd.DataFrame(rows)


def _qa_figures(profile: str, figure_dir: Path) -> pd.DataFrame:
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


def _write_readiness_report(output: Path, artifacts: dict[str, pd.DataFrame], readiness: pd.DataFrame, figure_qa: pd.DataFrame) -> None:
    summary = artifacts["summary"].set_index("method")
    safe = summary.loc["KOTMA-SR"]
    cbr = summary.loc["CBR"]
    paired = artifacts["paired"].loc[artifacts["paired"]["comparator"] == "CBR"].iloc[0]
    actions = artifacts["traces"]["safety_action"].value_counts()
    benchmark = artifacts.get("benchmark_summary", pd.DataFrame())
    benchmark = benchmark.loc[benchmark["method"] != "KOTMA-SR"] if "method" in benchmark else pd.DataFrame()
    best_baseline = benchmark.sort_values("pressure_mae_raw").iloc[0] if not benchmark.empty else pd.Series(dtype=float)
    lines = [
        "# KOTMA-SR manuscript readiness report",
        "",
        "## Scope",
        "",
        "Retrospective recovery of historically executed first-article printing pressure settings for independent PCB sides. "
        "This is not counterfactual quality optimization or autonomous process control.",
        "",
        "## Primary evidence",
        "",
        f"- Independent PCB sides: {int(safe.get('n_sides', safe['n_boards']))}; physical boards: {int(safe.get('n_physical_boards', safe['n_boards']))}.",
        "- Primary protocol: physical-board grouped nested LOBO; A/B sides are evaluated independently but held out together.",
        f"- Pressure MAE: KOTMA-SR {safe['pressure_mae_raw']:.4f} versus CBR {cbr['pressure_mae_raw']:.4f}.",
        f"- Best non-KOTMA-SR grouped benchmark: {best_baseline.get('method', 'unavailable')} with MAE {best_baseline.get('pressure_mae_raw', np.nan):.4f}.",
        f"- Relative MAE reduction: {100 * (cbr['pressure_mae_raw'] - safe['pressure_mae_raw']) / cbr['pressure_mae_raw']:.1f}%.",
        f"- Within +/-0.2: KOTMA-SR {100 * safe['within_0_2_raw_rate']:.1f}% versus CBR {100 * cbr['within_0_2_raw_rate']:.1f}%.",
        f"- Within +/-0.4: KOTMA-SR {100 * safe['within_0_4_raw_rate']:.1f}% versus CBR {100 * cbr['within_0_4_raw_rate']:.1f}%.",
        f"- Side-level paired Wilcoxon p: {paired['p_wilcoxon']:.4g}. Physical-board cluster-bootstrap CI for mean MAE advantage: "
        f"[{paired.get('cluster_bootstrap_ci_low', paired['bootstrap_ci_low']):.4f}, {paired.get('cluster_bootstrap_ci_high', paired['bootstrap_ci_high']):.4f}].",
        "",
        "## Selective reasoning",
        "",
        f"- Descriptor CBR safeguard: {int(actions.get('descriptor_cbr_safeguard', 0))} PCB sides.",
        f"- Bounded structural tail correction: {int(actions.get('bounded_structural_tail_correction', 0))} PCB sides.",
        f"- Accepted coverage: {100 * safe['accepted_coverage']:.1f}%.",
        f"- Accepted within +/-0.4: {100 * safe['accepted_within_0_4_rate']:.1f}%.",
        "",
        "## Reviewer boundary",
        "",
    ]
    for _, row in readiness.iterrows():
        lines.append(f"- [{row['status']}] {row['criterion']}: {row['evidence']} Action: {row['claim_action']}")
    lines.extend(
        [
            "",
            "## Figure QA",
            "",
            f"- Publication figures passed export and source-data QA: {int(figure_qa['qa_status'].eq('pass').sum())}/{len(figure_qa)}.",
            "- Each figure is exported as PNG, SVG, PDF, TIFF, and a source-data CSV.",
            "",
        ]
    )
    (output / "MANUSCRIPT_READINESS_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    args = parse_args()
    np.random.seed(args.seed)
    output = Path(args.output)
    shared = output / "shared"
    audits = output / "audits"
    shared.mkdir(parents=True, exist_ok=True)
    audits.mkdir(parents=True, exist_ok=True)
    manifest = {
        "mode": "smoke" if args.smoke else "manuscript",
        "paper_profile": args.paper_profile,
        "seed": args.seed,
        "requested_device": args.device,
        "requested_fgw_device": args.fgw_device,
        "db": str(Path(args.db).resolve()),
        "dependencies": _dependency_versions(),
        "claim_boundary": "Retrospective historically-executed pressure recovery; not quality optimization.",
    }
    (output / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if args.full_db_audit:
        audit_database(args.db, audits)
    else:
        audit_database_fast(args.db, audits)
    engine = OTMAEngine(OTMAConfig(base_k=args.base_k, require_pot=True, compute_device=args.device, fgw_device=args.fgw_device))
    manifest["resolved_device"] = engine.resolved_device()
    manifest["resolved_fgw_device"] = engine.resolved_fgw_device()
    (output / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    records = load_print_spi(args.db, ot_engine=engine, base_k=args.base_k, precompute_stability=False)
    write_data_inventory(records, audits)
    restored_cache_entries = _load_fgw_cache(engine, shared)
    if restored_cache_entries:
        print(f"Restored FGW cache entries: {restored_cache_entries}", flush=True)

    max_outer = args.max_outer_boards
    max_inner = args.max_inner_boards
    if args.smoke:
        max_outer = max_outer or 6
        max_inner = max_inner or 5
    if args.resume_prebenchmark:
        artifacts = _load_prebenchmark_artifacts(shared)
        print("Reused completed pre-benchmark artifacts.", flush=True)
    elif args.legacy_side_primary:
        artifacts = evaluate_strict_nested_lobo(
            records,
            engine,
            shared,
            smoke=args.smoke,
            max_outer_boards=max_outer,
            max_inner_boards=max_inner,
        )
        artifacts["protocol_summary"] = artifacts["summary"].assign(protocol="side_lobo")
    else:
        artifacts = evaluate_grouped_nested(
            records,
            engine,
            shared,
            protocol="pcb_group_lobo",
            smoke=args.smoke,
            max_outer_folds=max_outer,
            max_inner_folds=max_inner,
        )
        diagnostic = evaluate_grouped_nested(
            records,
            engine,
            shared,
            protocol="side_lobo",
            smoke=True,
            max_outer_folds=max_outer if args.smoke else None,
            max_inner_folds=max_inner or 5,
        )
        artifacts["protocol_summary"] = pd.concat(
            [
                artifacts["summary"].assign(protocol="pcb_group_lobo"),
                diagnostic["summary"].assign(protocol="side_lobo_diagnostic"),
            ],
            ignore_index=True,
        )
    if not args.resume_prebenchmark:
        _save_fgw_cache(engine, shared)
        artifacts["ablation"] = evaluate_clean_ablations(records, engine, shared, smoke=args.smoke)
        extra = evaluate_explanations_and_robustness(records, engine, artifacts["traces"], shared, smoke=args.smoke)
        artifacts.update(extra)
        artifacts["intervals"] = summarize_interval_calibration(artifacts["results"], artifacts["traces"], shared)
        artifacts["selective"] = selective_risk_curve(artifacts["results"])
        artifacts["selective"].to_csv(shared / "selective_risk_curve.csv", index=False)
        artifacts["cases"] = write_action_case_table(artifacts["results"], artifacts["traces"], shared)
        artifacts.update(mechanism_strata(artifacts["results"], artifacts["traces"], shared))
        artifacts["gate_sensitivity"] = evaluate_gate_sensitivity(records, engine, shared, smoke=args.smoke)
        artifacts["conditional_intervals"] = summarize_conditional_intervals(artifacts["results"], artifacts["traces"], shared)
        artifacts["interval_comparators"] = evaluate_interval_comparators(records, engine, shared, smoke=args.smoke)
        artifacts["grouped_sample_efficiency"] = evaluate_grouped_sample_efficiency(records, engine, shared, smoke=args.smoke, seed=args.seed)
        artifacts["sample_efficiency"] = artifacts["grouped_sample_efficiency"].rename(columns={"train_physical_boards": "train_boards"})
        artifacts["negative_controls"] = evaluate_negative_controls(records, engine, shared, smoke=args.smoke, seed=args.seed)
        artifacts["robustness_v2"] = evaluate_robustness_suite(records, engine, shared, smoke=args.smoke or args.skip_full_robustness, seed=args.seed)
        artifacts["velocity_policy"] = summarize_velocity_policy(records, shared)
        _save_fgw_cache(engine, shared)
    if args.skip_extended_benchmarks:
        artifacts["benchmark_results"] = artifacts["results"]
        artifacts["benchmark_summary"] = artifacts["summary"]
        artifacts["benchmark_paired"] = artifacts["paired"]
        artifacts["benchmark_selections"] = pd.DataFrame()
    else:
        artifacts.update(
            evaluate_baseline_suite(
                records,
                engine,
                artifacts["results"],
                shared,
                protocol="pcb_group_lobo",
                smoke=args.smoke,
                max_outer_folds=max_outer,
                max_inner_folds=max_inner,
            )
        )
        _save_fgw_cache(engine, shared)
    if args.run_exploratory_gnn:
        artifacts["exploratory_gnn"] = evaluate_exploratory_gnn(records, shared, smoke=args.smoke)
    else:
        artifacts["exploratory_gnn"] = pd.DataFrame([{"status": "skipped_not_requested"}])
        artifacts["exploratory_gnn"].to_csv(shared / "exploratory_gnn_results.csv", index=False)
    write_collection_templates(shared)
    if args.prospective_csv:
        evaluate_prospective_csv(args.prospective_csv, shared)
    if args.engineer_review_csv:
        evaluate_engineer_review_csv(args.engineer_review_csv, shared)
    readiness = _readiness_audit(artifacts, smoke=args.smoke)
    readiness.to_csv(output / "claim_readiness_audit.csv", index=False)

    profiles = ["kbs", "jms"] if args.paper_profile == "both" else [args.paper_profile]
    qa_rows = []
    for profile in profiles:
        figure_dir = output / f"figures_{profile}"
        generate_profile_figures(profile, records, artifacts, figure_dir, engine=engine)
        qa_rows.append(_qa_figures(profile, figure_dir))
    supplementary_dir = output / "supplementary_figures"
    generate_supplementary_figures(artifacts, supplementary_dir)
    qa_rows.append(_qa_figures("supplementary", supplementary_dir))
    figure_qa = pd.concat(qa_rows, ignore_index=True)
    figure_qa.to_csv(output / "figure_qa_audit.csv", index=False)
    _write_readiness_report(output, artifacts, readiness, figure_qa)
    print(f"Loaded boards: {len({record.board_id for record in records})}")
    print(f"Mode: {'smoke' if args.smoke else 'manuscript'}")
    print(f"Results: {output.resolve()}")
    print(f"Figure QA pass: {int(figure_qa['qa_status'].eq('pass').sum())}/{len(figure_qa)}")


if __name__ == "__main__":
    main()

