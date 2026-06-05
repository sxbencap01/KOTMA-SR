"""Mechanism, calibration, robustness, and engineering-policy evidence for KBS reporting."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from .grouped_evaluation import calibrate_grouped_profile
from .baseline_suite import executable_pressure
from .trusted_recommender import CalibrationProfile, TrustedConfig, TrustedRecommender, board_descriptor
from .validation_protocols import make_folds, physical_board_id, unique_side_cases


def default_safe_config(**overrides) -> TrustedConfig:
    values = {
        "top_k": 8,
        "descriptor_weight": 0.5,
        "prior_weight": 0.0,
        "use_fgw": True,
        "use_prior": False,
        "sparse_tail_shrink": True,
    }
    values.update(overrides)
    return TrustedConfig(**values)


def mechanism_strata(results: pd.DataFrame, traces: pd.DataFrame, output_dir: str | Path) -> dict[str, pd.DataFrame]:
    output_dir = Path(output_dir)
    safe = results[results["method"].eq("KOTMA-SR")].set_index("board_id")
    cbr = results[results["method"].eq("CBR")].set_index("board_id")
    trace = traces.set_index("board_id")
    frame = pd.DataFrame(
        {
            "board_id": safe.index,
            "physical_board_id": safe["physical_board_id"],
            "observed_pressure_raw": safe["real_pressure_raw"],
            "safe_pressure_raw": safe["recommended_pressure_raw"],
            "cbr_pressure_raw": cbr["recommended_pressure_raw"],
            "safe_error_raw": safe["pressure_abs_error_raw"],
            "cbr_error_raw": cbr["pressure_abs_error_raw"],
            "gain_vs_cbr_raw": cbr["pressure_abs_error_raw"] - safe["pressure_abs_error_raw"],
            "safety_action": trace["safety_action"],
            "descriptor_cbr_support": trace["descriptor_cbr_support"],
            "structural_pressure_raw": trace["structural_pressure_raw"],
            "manual_review": trace["manual_review"],
            "review_reasons": trace["review_reasons"],
            "confidence": trace["confidence"],
        }
    ).reset_index(drop=True)
    frame["stratum"] = np.where(frame["safety_action"].eq("bounded_structural_tail_correction"), "sparse_tail", "common_support")
    frame["ood"] = frame["review_reasons"].fillna("").str.contains("ood_distance")
    strata = (
        frame.groupby("stratum", as_index=False)
        .agg(
            n_sides=("board_id", "size"),
            n_physical_boards=("physical_board_id", "nunique"),
            safe_mae=("safe_error_raw", "mean"),
            cbr_mae=("cbr_error_raw", "mean"),
            mean_gain_vs_cbr=("gain_vs_cbr_raw", "mean"),
            manual_review_rate=("manual_review", "mean"),
        )
    )
    pressure = (
        frame.groupby("observed_pressure_raw", as_index=False)
        .agg(
            n_sides=("board_id", "size"),
            safe_mae=("safe_error_raw", "mean"),
            cbr_mae=("cbr_error_raw", "mean"),
            mean_gain_vs_cbr=("gain_vs_cbr_raw", "mean"),
        )
        .sort_values("observed_pressure_raw")
    )
    frame.to_csv(output_dir / "mechanism_case_table.csv", index=False)
    strata.to_csv(output_dir / "mechanism_strata_summary.csv", index=False)
    pressure.to_csv(output_dir / "pressure_bin_summary.csv", index=False)
    return {"mechanism_cases": frame, "mechanism_strata": strata, "pressure_bins": pressure}


def evaluate_gate_sensitivity(records: Sequence, engine, output_dir: str | Path, smoke: bool = False) -> pd.DataFrame:
    output_dir = Path(output_dir)
    supports = [2, 3] if smoke else [2, 3, 4, 5]
    caps = [0.2, 0.4] if smoke else [0.1, 0.2, 0.3, 0.4, 0.5]
    rows = []
    folds = make_folds(records, "pcb_group_lobo", max_folds=4 if smoke else None)
    for support in supports:
        for cap in caps:
            errors, within, review, corrections = [], [], [], []
            config = default_safe_config(min_supported_pressure_cases=support, max_tail_adjustment_raw=cap)
            for fold in folds:
                recommender = TrustedRecommender(engine, config)
                for held in fold.test_cases:
                    trace = recommender.recommend(held, fold.train_cases, CalibrationProfile())
                    error = abs(trace.recommended_pressure_raw - held.press_raw)
                    errors.append(error)
                    within.append(error <= 0.4 + 1e-9)
                    review.append(trace.manual_review)
                    corrections.append(trace.safety_action == "bounded_structural_tail_correction")
            rows.append(
                {
                    "min_supported_pressure_cases": support,
                    "max_tail_adjustment_raw": cap,
                    "n_sides": len(errors),
                    "pressure_mae_raw": float(np.mean(errors)),
                    "within_0_4_raw_rate": float(np.mean(within)),
                    "manual_review_rate": float(np.mean(review)),
                    "correction_rate": float(np.mean(corrections)),
                }
            )
    frame = pd.DataFrame(rows)
    pareto = []
    for index, row in frame.iterrows():
        dominated = (
            (frame["pressure_mae_raw"] <= row["pressure_mae_raw"])
            & (frame["within_0_4_raw_rate"] >= row["within_0_4_raw_rate"])
            & (
                (frame["pressure_mae_raw"] < row["pressure_mae_raw"])
                | (frame["within_0_4_raw_rate"] > row["within_0_4_raw_rate"])
            )
        ).any()
        pareto.append(not dominated)
    frame["pareto_front"] = pareto
    frame.to_csv(output_dir / "gate_sensitivity.csv", index=False)
    return frame


def summarize_conditional_intervals(results: pd.DataFrame, traces: pd.DataFrame, output_dir: str | Path) -> pd.DataFrame:
    safe = results[results["method"].eq("KOTMA-SR")].set_index("board_id")
    trace = traces.set_index("board_id")
    joined = safe.join(trace, rsuffix="_trace")
    joined["stratum"] = np.where(joined["safety_action"].eq("bounded_structural_tail_correction"), "sparse_tail", "common_support")
    joined["ood_group"] = np.where(joined["review_reasons"].fillna("").str.contains("ood_distance"), "ood", "non_ood")
    joined["review_group"] = np.where(joined["manual_review_trace"].astype(bool), "manual_review", "accepted")
    rows = []
    groupers = [("overall", None), ("stratum", "stratum"), ("ood", "ood_group"), ("review", "review_group"), ("pressure", "real_pressure_raw")]
    for layer, column in groupers:
        partitions = [("all", joined)] if column is None else list(joined.groupby(column))
        for value, frame in partitions:
            for nominal, low, high in [
                (0.80, "interval_80_low_raw", "interval_80_high_raw"),
                (0.90, "interval_90_low_raw", "interval_90_high_raw"),
            ]:
                covered = (frame["real_pressure_raw"] >= frame[low]) & (frame["real_pressure_raw"] <= frame[high])
                rows.append(
                    {
                        "layer": layer,
                        "group": value,
                        "nominal_coverage": nominal,
                        "empirical_coverage": float(covered.mean()),
                        "mean_interval_width_raw": float((frame[high] - frame[low]).mean()),
                        "n_sides": int(len(frame)),
                        "insufficient_n": int(len(frame) < 5),
                    }
                )
    result = pd.DataFrame(rows)
    result.to_csv(Path(output_dir) / "conditional_interval_calibration.csv", index=False)
    return result


def evaluate_grouped_sample_efficiency(records: Sequence, engine, output_dir: str | Path, smoke: bool = False, seed: int = 2026) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cases = unique_side_cases(records)
    physical_ids = sorted({physical_board_id(case.board_id) for case in cases})
    sizes = [5, 10, len(physical_ids) - 1] if smoke else [5, 10, 15, len(physical_ids) - 1]
    repeats = 1 if smoke else 3
    rows = []
    for repeat in range(repeats):
        for held_group in physical_ids:
            held_cases = [case for case in cases if physical_board_id(case.board_id) == held_group]
            available = [group for group in physical_ids if group != held_group]
            for train_size in sizes:
                chosen_ids = available if train_size >= len(available) else list(rng.choice(available, train_size, replace=False))
                train = [case for case in cases if physical_board_id(case.board_id) in chosen_ids]
                for method, config in [
                    ("KOTMA-SR", default_safe_config()),
                    ("Top-1 CBR", TrustedConfig(top_k=1, descriptor_weight=1.0, prior_weight=0.0, use_fgw=False, use_prior=False)),
                ]:
                    recommender = TrustedRecommender(engine, config)
                    for held in held_cases:
                        error = abs(recommender.recommend(held, train).recommended_pressure_raw - held.press_raw)
                        rows.append(
                            {
                                "repeat": repeat,
                                "train_physical_boards": len(chosen_ids),
                                "physical_board_id": held_group,
                                "board_id": held.board_id,
                                "method": method,
                                "pressure_abs_error_raw": error,
                                "within_0_4_raw": float(error <= 0.4 + 1e-9),
                            }
                        )
    frame = pd.DataFrame(rows)
    frame.to_csv(Path(output_dir) / "grouped_sample_efficiency.csv", index=False)
    return frame


def _perturbed_record(held, engine, perturbation: str, level: float, rng) -> object:
    comps = np.asarray(held.comps_raw, dtype=float).copy()
    if perturbation == "pad_missing":
        count = max(2, int(np.floor(len(comps) * (1.0 - level))))
        comps = comps[np.sort(rng.choice(len(comps), count, replace=False))]
    elif perturbation == "position_noise":
        comps[:, :2] += rng.normal(0.0, level, size=comps[:, :2].shape)
    elif perturbation == "size_noise":
        comps[:, 2:4] *= 1.0 + rng.normal(0.0, level, size=comps[:, 2:4].shape)
    elif perturbation == "shape_missing":
        count = max(1, int(np.floor(len(comps) * level)))
        indexes = rng.choice(len(comps), count, replace=False)
        comps[indexes, 6:8] = np.nanmedian(comps[:, 6:8], axis=0)
    perturbed = replace(held, comps_raw=comps)
    clusters = int(level) if perturbation == "super_node_count" else min(engine.config.base_k, len(comps))
    perturbed.ot_repr = engine.coarsen_pcb(comps, n_clusters=min(clusters, len(comps)))
    return perturbed


def evaluate_robustness_suite(records: Sequence, engine, output_dir: str | Path, smoke: bool = False, seed: int = 2026) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    plan = {
        "pad_missing": [0.01, 0.05, 0.10],
        "position_noise": [0.005, 0.01, 0.02],
        "size_noise": [0.01, 0.03, 0.05],
        "shape_missing": [0.10, 0.30, 1.00],
        "super_node_count": [40, 60, 80, 100],
    }
    folds = make_folds(records, "pcb_group_lobo", max_folds=3 if smoke else None)
    config = default_safe_config()
    rows = []
    for fold in folds:
        recommender = TrustedRecommender(engine, config)
        for held in fold.test_cases:
            base = recommender.recommend(held, fold.train_cases)
            for perturbation, levels in plan.items():
                for level in levels:
                    altered = _perturbed_record(held, engine, perturbation, level, rng)
                    trace = recommender.recommend(altered, fold.train_cases)
                    rows.append(
                        {
                            "physical_board_id": fold.fold_id,
                            "board_id": held.board_id,
                            "perturbation": perturbation,
                            "level": level,
                            "base_pressure_raw": base.recommended_pressure_raw,
                            "perturbed_pressure_raw": trace.recommended_pressure_raw,
                            "recommendation_shift_raw": abs(trace.recommended_pressure_raw - base.recommended_pressure_raw),
                            "base_error_raw": abs(base.recommended_pressure_raw - held.press_raw),
                            "perturbed_error_raw": abs(trace.recommended_pressure_raw - held.press_raw),
                            "review_flag_changed": int(trace.manual_review != base.manual_review),
                        }
                    )
    frame = pd.DataFrame(rows)
    frame.to_csv(Path(output_dir) / "robustness_suite.csv", index=False)
    return frame


def summarize_velocity_policy(records: Sequence, output_dir: str | Path) -> pd.DataFrame:
    cases = unique_side_cases(records)
    rows = []
    for fold in make_folds(cases, "pcb_group_lobo"):
        values = np.asarray([case.velocity_raw for case in fold.train_cases], dtype=float)
        modes = pd.Series(values).mode()
        train_mode = float(modes.iloc[0])
        for held in fold.test_cases:
            rows.append(
                {
                    "physical_board_id": fold.fold_id,
                    "board_id": held.board_id,
                    "observed_velocity": held.velocity_raw,
                    "fixed_0_8_velocity": 0.8,
                    "fold_mode_velocity": train_mode,
                    "fixed_0_8_abs_error": abs(held.velocity_raw - 0.8),
                    "fold_mode_abs_error": abs(held.velocity_raw - train_mode),
                    "engineer_override_supported": 1,
                }
            )
    frame = pd.DataFrame(rows)
    frame.to_csv(Path(output_dir) / "velocity_policy_summary.csv", index=False)
    return frame


def _fixed_method_prediction(method: str, engine, held, train_cases: Sequence) -> float:
    if method == "KOTMA-SR":
        return TrustedRecommender(engine, default_safe_config()).recommend(held, train_cases).recommended_pressure_raw
    if method == "Top-1 CBR":
        config = TrustedConfig(top_k=1, descriptor_weight=1.0, prior_weight=0.0, use_fgw=False, use_prior=False)
        return TrustedRecommender(engine, config).recommend(held, train_cases).recommended_pressure_raw
    if method == "Ridge":
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        x = np.vstack([board_descriptor(case) for case in train_cases])
        y = np.asarray([case.press_raw for case in train_cases], dtype=float)
        model = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(x, y)
        return executable_pressure(float(model.predict(board_descriptor(held)[None, :])[0]))
    raise ValueError(f"Unknown interval comparator: {method}")


def evaluate_interval_comparators(records: Sequence, engine, output_dir: str | Path, smoke: bool = False) -> pd.DataFrame:
    rows = []
    folds = make_folds(records, "pcb_group_lobo", max_folds=4 if smoke else None)
    for method in ["KOTMA-SR", "Top-1 CBR", "Ridge"]:
        for outer in folds:
            residuals = []
            for inner in make_folds(outer.train_cases, "pcb_group_lobo", max_folds=4 if smoke else None):
                if len(inner.train_cases) < 3:
                    continue
                for held in inner.test_cases:
                    residuals.append(abs(_fixed_method_prediction(method, engine, held, inner.train_cases) - held.press_raw))
            if not residuals:
                continue
            for nominal in [0.80, 0.90]:
                quantile = float(np.quantile(residuals, nominal))
                for held in outer.test_cases:
                    prediction = _fixed_method_prediction(method, engine, held, outer.train_cases)
                    low, high = max(5.0, prediction - quantile), min(8.0, prediction + quantile)
                    rows.append(
                        {
                            "method": method,
                            "outer_fold_id": outer.fold_id,
                            "board_id": held.board_id,
                            "nominal_coverage": nominal,
                            "interval_low_raw": low,
                            "interval_high_raw": high,
                            "interval_width_raw": high - low,
                            "covered": float(low <= held.press_raw <= high),
                        }
                    )
    cases = pd.DataFrame(rows)
    summary = (
        cases.groupby(["method", "nominal_coverage"], as_index=False)
        .agg(empirical_coverage=("covered", "mean"), mean_interval_width_raw=("interval_width_raw", "mean"), n_sides=("board_id", "size"))
    )
    output_dir = Path(output_dir)
    cases.to_csv(output_dir / "interval_comparator_cases.csv", index=False)
    summary.to_csv(output_dir / "interval_comparator_summary.csv", index=False)
    return summary

