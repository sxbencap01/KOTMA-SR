"""Strict retrospective validation for trustworthy first-article recommendation."""

from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
from time import perf_counter
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

try:
    from .trusted_recommender import CalibrationProfile, TrustedConfig, TrustedRecommender
except ImportError:
    from trusted_recommender import CalibrationProfile, TrustedConfig, TrustedRecommender


def _unique_board_cases(records: Sequence) -> list:
    cases = {}
    for record in records:
        cases.setdefault(record.board_id, record)
    return [cases[key] for key in sorted(cases)]


def _raw_pressure_error(trace, observed) -> float:
    return float(abs(trace.recommended_pressure_raw - observed.press_raw))


def _config_grid(smoke: bool = False) -> list[TrustedConfig]:
    if smoke:
        return [
            TrustedConfig(top_k=5, descriptor_weight=0.5, prior_weight=0.0, use_fgw=True, use_prior=False, sparse_tail_shrink=True),
        ]
    configs = []
    # Tune only the bounded structural correction. The CBR safeguard remains
    # fixed and auditable under sparse production histories.
    for top_k in [5, 8]:
        for descriptor_weight in [0.5, 0.75]:
            for max_tail_adjustment_raw in [0.2, 0.4]:
                for min_supported_pressure_cases in [3]:
                    configs.append(
                        TrustedConfig(
                            top_k=top_k,
                            descriptor_weight=descriptor_weight,
                            prior_weight=0.0,
                            kde_weight=0.0,
                            use_fgw=True,
                            use_prior=False,
                            use_kde=False,
                            sparse_tail_shrink=True,
                            min_supported_pressure_cases=min_supported_pressure_cases,
                            max_tail_adjustment_raw=max_tail_adjustment_raw,
                        )
                    )
    return configs


def _complexity(config: TrustedConfig) -> tuple:
    return (
        int(config.use_fgw),
        int(config.use_prior),
        int(config.use_kde),
        int(config.sparse_tail_shrink),
        config.top_k,
        config.max_tail_adjustment_raw,
    )


def calibrate_profile(engine, train_cases: Sequence, config: TrustedConfig, max_cases: int | None = None) -> CalibrationProfile:
    cases = list(train_cases)
    if max_cases is not None:
        cases = cases[:max_cases]
    rows = []
    for held in cases:
        inner_train = [case for case in train_cases if case.board_id != held.board_id]
        if len(inner_train) < 2:
            continue
        trace = TrustedRecommender(engine, config).recommend(held, inner_train, CalibrationProfile())
        rows.append(
            {
                "board_id": held.board_id,
                "pressure_abs_error_raw": _raw_pressure_error(trace, held),
                "min_normalized_distance": trace.min_normalized_distance,
                "effective_neighbor_count": trace.effective_neighbor_count,
                "confidence_uncalibrated": trace.confidence,
            }
        )
    if not rows:
        return CalibrationProfile()
    frame = pd.DataFrame(rows)
    errors = frame["pressure_abs_error_raw"].to_numpy(dtype=float)
    distances = frame["min_normalized_distance"].to_numpy(dtype=float)
    # OOF confidence is intentionally conservative, but the threshold must not
    # collapse deployment coverage when the calibrated distance penalty is
    # introduced on the outer fold.
    confidence_threshold = min(float(np.quantile(frame["confidence_uncalibrated"], 0.10)), 0.35)
    return CalibrationProfile(
        residual_q80_raw=float(np.quantile(errors, 0.80)),
        residual_q90_raw=float(np.quantile(errors, 0.90)),
        distance_q95=float(np.quantile(distances, 0.95)),
        confidence_threshold=confidence_threshold,
        oof_rows=rows,
    )


def select_nested_config(
    engine,
    train_cases: Sequence,
    smoke: bool = False,
    max_inner_boards: int | None = None,
) -> tuple[TrustedConfig, pd.DataFrame]:
    candidates = _config_grid(smoke=smoke)
    inner_cases = list(train_cases)
    if max_inner_boards is not None:
        inner_cases = inner_cases[:max_inner_boards]
    rows = []
    for config_id, config in enumerate(candidates):
        errors = []
        started = perf_counter()
        recommender = TrustedRecommender(engine, config)
        for held in inner_cases:
            pool = [case for case in train_cases if case.board_id != held.board_id]
            if len(pool) < 2:
                continue
            trace = recommender.recommend(held, pool, CalibrationProfile())
            errors.append(_raw_pressure_error(trace, held))
        rows.append(
            {
                "config_id": config_id,
                **asdict(config),
                "inner_boards": len(errors),
                "inner_pressure_mae_raw": float(np.mean(errors)) if errors else np.nan,
                "runtime_ms": 1000.0 * (perf_counter() - started),
                "complexity": str(_complexity(config)),
            }
        )
    frame = pd.DataFrame(rows)
    valid = frame.dropna(subset=["inner_pressure_mae_raw"]).copy()
    if valid.empty:
        raise ValueError("Nested configuration selection has no evaluable configurations.")
    valid = valid.sort_values(["inner_pressure_mae_raw", "use_fgw", "use_prior", "use_kde", "top_k"])
    selected_id = int(valid.iloc[0]["config_id"])
    frame["selected"] = (frame["config_id"] == selected_id).astype(int)
    return candidates[selected_id], frame


def _median_baseline(train_cases: Sequence) -> float:
    return float(np.median([case.press_raw for case in train_cases]))


def _mode_baseline(train_cases: Sequence) -> float:
    values, counts = np.unique(np.round([case.press_raw for case in train_cases], 6), return_counts=True)
    return float(values[int(np.argmax(counts))])


def _descriptor_cbr(engine, held, train_cases: Sequence) -> float:
    config = TrustedConfig(top_k=1, descriptor_weight=1.0, prior_weight=0.0, use_fgw=False, use_prior=False)
    return float(TrustedRecommender(engine, config).recommend(held, train_cases).recommended_pressure_raw)


def evaluate_strict_nested_lobo(
    records: Sequence,
    engine,
    output_dir: str | Path,
    smoke: bool = False,
    max_outer_boards: int | None = None,
    max_inner_boards: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Run outer LOBO with fold-local nested tuning and confidence calibration."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    all_cases = _unique_board_cases(records)
    outer_cases = all_cases[:max_outer_boards] if max_outer_boards else all_cases
    result_rows = []
    trace_rows = []
    selection_rows = []
    calibration_rows = []
    for outer_index, held in enumerate(outer_cases, start=1):
        print(f"[nested-lobo] outer {outer_index}/{len(outer_cases)} board={held.board_id}", flush=True)
        train_cases = [case for case in all_cases if case.board_id != held.board_id]
        selected, selections = select_nested_config(
            engine,
            train_cases,
            smoke=smoke,
            max_inner_boards=max_inner_boards,
        )
        selections.insert(0, "outer_board_id", held.board_id)
        selection_rows.append(selections)
        calibration = calibrate_profile(
            engine,
            train_cases,
            selected,
            max_cases=max_inner_boards if smoke else None,
        )
        for row in calibration.oof_rows:
            calibration_rows.append({"outer_board_id": held.board_id, **row})
        trace = TrustedRecommender(engine, selected).recommend(held, train_cases, calibration)
        unconstrained = TrustedRecommender(
            engine,
            TrustedConfig(top_k=8, descriptor_weight=0.5, prior_weight=0.0, use_fgw=True, use_prior=False),
        ).recommend(held, train_cases, calibration)
        trace_row = trace.as_dict()
        trace_rows.append(trace_row)
        methods = {
            "KOTMA-SR": trace.recommended_pressure_raw,
            "KOTMA-SR (unconstrained)": unconstrained.recommended_pressure_raw,
            "CBR": _descriptor_cbr(engine, held, train_cases),
            "Training median": _median_baseline(train_cases),
            "Training mode": _mode_baseline(train_cases),
        }
        for method, pressure in methods.items():
            error = float(abs(pressure - held.press_raw))
            result_rows.append(
                {
                    "board_id": held.board_id,
                    "method": method,
                    "real_pressure_raw": held.press_raw,
                    "recommended_pressure_raw": pressure,
                    "pressure_abs_error_raw": error,
                    "within_0_2_raw": float(error <= 0.2 + 1e-9),
                    "within_0_4_raw": float(error <= 0.4 + 1e-9),
                    "manual_review": float(trace.manual_review) if method == "KOTMA-SR" else np.nan,
                    "accepted": float(not trace.manual_review) if method == "KOTMA-SR" else np.nan,
                    "confidence": trace.confidence if method == "KOTMA-SR" else np.nan,
                    "runtime_ms": trace.runtime_ms if method == "KOTMA-SR" else np.nan,
                    "effective_neighbor_count": trace.effective_neighbor_count if method == "KOTMA-SR" else np.nan,
                    "min_normalized_distance": trace.min_normalized_distance if method == "KOTMA-SR" else np.nan,
                }
            )
    results = pd.DataFrame(result_rows)
    traces = pd.DataFrame(trace_rows)
    selections = pd.concat(selection_rows, ignore_index=True) if selection_rows else pd.DataFrame()
    calibration = pd.DataFrame(calibration_rows)
    results.to_csv(output_dir / "nested_outer_fold_results.csv", index=False)
    traces.to_csv(output_dir / "recommendation_traces.csv", index=False)
    selections.to_csv(output_dir / "nested_config_selection.csv", index=False)
    calibration.to_csv(output_dir / "interval_calibration_oof.csv", index=False)
    summary = summarize_primary_results(results)
    summary.to_csv(output_dir / "primary_endpoint_statistics.csv", index=False)
    selective = selective_risk_curve(results)
    selective.to_csv(output_dir / "selective_risk_curve.csv", index=False)
    paired = paired_transparency_report(results)
    paired.to_csv(output_dir / "paired_board_level_statistics.csv", index=False)
    return {
        "results": results,
        "traces": traces,
        "selections": selections,
        "calibration": calibration,
        "summary": summary,
        "selective": selective,
        "paired": paired,
    }


def summarize_primary_results(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method, frame in results.groupby("method"):
        rows.append(
            {
                "method": method,
                "n_boards": int(len(frame)),
                "pressure_mae_raw": float(frame["pressure_abs_error_raw"].mean()),
                "pressure_median_abs_error_raw": float(frame["pressure_abs_error_raw"].median()),
                "within_0_2_raw_rate": float(frame["within_0_2_raw"].mean()),
                "within_0_4_raw_rate": float(frame["within_0_4_raw"].mean()),
                "accepted_coverage": float(frame["accepted"].mean()) if frame["accepted"].notna().any() else np.nan,
                "accepted_within_0_4_rate": float(frame.loc[frame["accepted"].eq(1), "within_0_4_raw"].mean())
                if frame["accepted"].eq(1).any()
                else np.nan,
                "median_runtime_ms": float(frame["runtime_ms"].median()) if frame["runtime_ms"].notna().any() else np.nan,
            }
        )
    return pd.DataFrame(rows)


def selective_risk_curve(results: pd.DataFrame) -> pd.DataFrame:
    frame = results[results["method"].eq("KOTMA-SR")].copy()
    rows = []
    for threshold in np.linspace(0.0, 1.0, 21):
        accepted = frame[frame["confidence"] >= threshold]
        rows.append(
            {
                "confidence_threshold": float(threshold),
                "accepted_boards": int(len(accepted)),
                "coverage": float(len(accepted) / len(frame)) if len(frame) else np.nan,
                "pressure_mae_raw": float(accepted["pressure_abs_error_raw"].mean()) if len(accepted) else np.nan,
                "within_0_4_raw_rate": float(accepted["within_0_4_raw"].mean()) if len(accepted) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def paired_transparency_report(results: pd.DataFrame, reference: str = "KOTMA-SR") -> pd.DataFrame:
    wide = results.pivot(index="board_id", columns="method", values="pressure_abs_error_raw")
    if reference not in wide:
        return pd.DataFrame()
    rng = np.random.default_rng(2026)
    rows = []
    for comparator in wide.columns:
        if comparator == reference:
            continue
        diff = (wide[comparator] - wide[reference]).dropna().to_numpy(dtype=float)
        boots = np.array([np.mean(rng.choice(diff, size=len(diff), replace=True)) for _ in range(10000)])
        try:
            p_wilcoxon = float(wilcoxon(diff).pvalue)
        except ValueError:
            p_wilcoxon = np.nan
        rows.append(
            {
                "reference": reference,
                "comparator": comparator,
                "difference_definition": f"{comparator} error minus {reference} error; positive favors {reference}",
                "n_boards": int(len(diff)),
                "mean_advantage_raw": float(np.mean(diff)),
                "bootstrap_ci_low": float(np.quantile(boots, 0.025)),
                "bootstrap_ci_high": float(np.quantile(boots, 0.975)),
                "prob_reference_better_bootstrap": float(np.mean(boots > 0.0)),
                "p_wilcoxon": p_wilcoxon,
                "reference_wins": int(np.sum(diff > 1e-9)),
                "ties": int(np.sum(np.abs(diff) <= 1e-9)),
                "comparator_wins": int(np.sum(diff < -1e-9)),
            }
        )
    return pd.DataFrame(rows)


def evaluate_clean_ablations(records: Sequence, engine, output_dir: str | Path, smoke: bool = False) -> pd.DataFrame:
    output_dir = Path(output_dir)
    cases = _unique_board_cases(records)
    if smoke:
        cases = cases[: min(8, len(cases))]
    configs = {
        "Descriptor CBR": TrustedConfig(top_k=1, descriptor_weight=1.0, prior_weight=0.0, use_fgw=False, use_prior=False),
        "FGW only": TrustedConfig(top_k=5, descriptor_weight=0.0, prior_weight=0.0, use_fgw=True, use_prior=False),
        "Descriptor + FGW": TrustedConfig(top_k=8, descriptor_weight=0.5, prior_weight=0.0, use_fgw=True, use_prior=False),
        "Sparse-tail correction": TrustedConfig(top_k=8, descriptor_weight=0.5, prior_weight=0.0, use_fgw=True, use_prior=False, sparse_tail_shrink=True),
    }
    rows = []
    for held in cases:
        train = [case for case in _unique_board_cases(records) if case.board_id != held.board_id]
        for method, config in configs.items():
            trace = TrustedRecommender(engine, config).recommend(held, train)
            error = _raw_pressure_error(trace, held)
            rows.append(
                {
                    "board_id": held.board_id,
                    "method": method,
                    "pressure_abs_error_raw": error,
                    "within_0_4_raw": float(error <= 0.4 + 1e-9),
                    "runtime_ms": trace.runtime_ms,
                }
            )
    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "clean_ablation_results.csv", index=False)
    return frame


def evaluate_explanations_and_robustness(records: Sequence, engine, traces: pd.DataFrame, output_dir: str | Path, smoke: bool = False) -> dict[str, pd.DataFrame]:
    output_dir = Path(output_dir)
    cases = _unique_board_cases(records)
    if smoke:
        cases = cases[: min(8, len(cases))]
    fidelity_rows = []
    perturbation_rows = []
    config = TrustedConfig(top_k=8, descriptor_weight=0.5, prior_weight=0.0, use_fgw=True, use_prior=False, sparse_tail_shrink=True)
    for held in cases:
        train = [case for case in _unique_board_cases(records) if case.board_id != held.board_id]
        base = TrustedRecommender(engine, config).recommend(held, train)
        if base.neighbor_ids:
            removed = base.neighbor_ids[0]
            reduced = [case for case in train if str(case.board_id) != str(removed)]
            after = TrustedRecommender(engine, config).recommend(held, reduced)
            fidelity_rows.append(
                {
                    "board_id": held.board_id,
                    "removed_neighbor_id": removed,
                    "removed_neighbor_rank": 1,
                    "pressure_shift_raw": abs(after.recommended_pressure_raw - base.recommended_pressure_raw),
                    "baseline_pressure_raw": base.recommended_pressure_raw,
                    "after_removal_pressure_raw": after.recommended_pressure_raw,
                }
            )
        for pct in [0.01, 0.03, 0.05]:
            perturbed = replace(held, comps_raw=np.asarray(held.comps_raw, dtype=float).copy())
            perturbed.comps_raw[:, :4] *= 1.0 + pct
            perturbed.ot_repr = engine.coarsen_pcb(perturbed.comps_raw, n_clusters=min(engine.config.base_k, len(perturbed.comps_raw)))
            after = TrustedRecommender(engine, config).recommend(perturbed, train)
            perturbation_rows.append(
                {
                    "board_id": held.board_id,
                    "perturbation_pct": pct,
                    "recommended_pressure_shift_raw": abs(after.recommended_pressure_raw - base.recommended_pressure_raw),
                }
            )
    fidelity = pd.DataFrame(fidelity_rows)
    robustness = pd.DataFrame(perturbation_rows)
    fidelity.to_csv(output_dir / "explanation_fidelity.csv", index=False)
    robustness.to_csv(output_dir / "perturbation_robustness.csv", index=False)
    return {"fidelity": fidelity, "robustness": robustness}


def summarize_interval_calibration(results: pd.DataFrame, traces: pd.DataFrame, output_dir: str | Path) -> pd.DataFrame:
    safe = results[results["method"].eq("KOTMA-SR")].set_index("board_id")
    trace = traces.set_index("board_id")
    observed = safe["real_pressure_raw"]
    rows = []
    for nominal, low, high in [
        (0.80, "interval_80_low_raw", "interval_80_high_raw"),
        (0.90, "interval_90_low_raw", "interval_90_high_raw"),
    ]:
        covered = (observed >= trace[low]) & (observed <= trace[high])
        rows.append(
            {
                "nominal_coverage": nominal,
                "empirical_coverage": float(covered.mean()),
                "mean_interval_width_raw": float((trace[high] - trace[low]).mean()),
                "n_boards": int(len(covered)),
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(Path(output_dir) / "interval_calibration_summary.csv", index=False)
    return frame


def write_action_case_table(results: pd.DataFrame, traces: pd.DataFrame, output_dir: str | Path) -> pd.DataFrame:
    safe = results[results["method"].eq("KOTMA-SR")].set_index("board_id")
    cbr = results[results["method"].eq("CBR")].set_index("board_id")
    trace = traces.set_index("board_id")
    frame = pd.DataFrame(
        {
            "board_id": safe.index,
            "real_pressure_raw": safe["real_pressure_raw"],
            "safe_pressure_raw": safe["recommended_pressure_raw"],
            "cbr_pressure_raw": cbr["recommended_pressure_raw"],
            "safe_error_raw": safe["pressure_abs_error_raw"],
            "cbr_error_raw": cbr["pressure_abs_error_raw"],
            "gain_vs_cbr_raw": cbr["pressure_abs_error_raw"] - safe["pressure_abs_error_raw"],
            "safety_action": trace["safety_action"],
            "descriptor_cbr_support": trace["descriptor_cbr_support"],
            "confidence": trace["confidence"],
            "manual_review": trace["manual_review"],
            "review_reasons": trace["review_reasons"],
        }
    ).reset_index(drop=True)
    frame.to_csv(Path(output_dir) / "action_case_table.csv", index=False)
    return frame


def evaluate_sample_efficiency(records: Sequence, engine, output_dir: str | Path, smoke: bool = False, seed: int = 2026) -> pd.DataFrame:
    cases = _unique_board_cases(records)
    sizes = [5, 10, 20, len(cases) - 1]
    repeats = 1 if smoke else 3
    rng = np.random.default_rng(seed)
    safe_config = TrustedConfig(top_k=8, descriptor_weight=0.5, prior_weight=0.0, use_fgw=True, use_prior=False, sparse_tail_shrink=True)
    cbr_config = TrustedConfig(top_k=1, descriptor_weight=1.0, prior_weight=0.0, use_fgw=False, use_prior=False)
    rows = []
    eval_cases = cases[: min(8, len(cases))] if smoke else cases
    for train_size in sizes:
        for repeat in range(repeats):
            for held in eval_cases:
                pool = [case for case in cases if case.board_id != held.board_id]
                chosen = pool if train_size >= len(pool) else [pool[idx] for idx in rng.choice(len(pool), size=train_size, replace=False)]
                for method, config in [("KOTMA-SR", safe_config), ("CBR", cbr_config)]:
                    trace = TrustedRecommender(engine, config).recommend(held, chosen)
                    error = _raw_pressure_error(trace, held)
                    rows.append(
                        {
                            "method": method,
                            "train_boards": int(len(chosen)),
                            "repeat": repeat,
                            "board_id": held.board_id,
                            "pressure_abs_error_raw": error,
                            "within_0_4_raw": float(error <= 0.4 + 1e-9),
                        }
                    )
    frame = pd.DataFrame(rows)
    frame.to_csv(Path(output_dir) / "sample_efficiency_results.csv", index=False)
    return frame


def evaluate_negative_controls(records: Sequence, engine, output_dir: str | Path, smoke: bool = False, seed: int = 2026) -> pd.DataFrame:
    cases = _unique_board_cases(records)
    eval_cases = cases[: min(8, len(cases))] if smoke else cases
    safe_config = TrustedConfig(top_k=8, descriptor_weight=0.5, prior_weight=0.0, use_fgw=True, use_prior=False, sparse_tail_shrink=True)
    rng = np.random.default_rng(seed)
    rows = []
    for held in eval_cases:
        train = [case for case in cases if case.board_id != held.board_id]
        safe = TrustedRecommender(engine, safe_config).recommend(held, train).recommended_pressure_raw
        shuffled = float(rng.choice([case.press_raw for case in train]))
        pad_nearest = min(train, key=lambda case: abs(len(case.comps_raw) - len(held.comps_raw))).press_raw
        median = float(np.median([case.press_raw for case in train]))
        for method, pressure in [
            ("KOTMA-SR", safe),
            ("Random historical pressure", shuffled),
            ("Nearest pad-count only", pad_nearest),
            ("Training median", median),
        ]:
            error = float(abs(pressure - held.press_raw))
            rows.append(
                {
                    "board_id": held.board_id,
                    "method": method,
                    "pressure_abs_error_raw": error,
                    "within_0_4_raw": float(error <= 0.4 + 1e-9),
                }
            )
    frame = pd.DataFrame(rows)
    frame.to_csv(Path(output_dir) / "negative_control_results.csv", index=False)
    return frame

