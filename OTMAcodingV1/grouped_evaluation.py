"""Physical-board grouped nested validation for KOTMA-SR."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from .trusted_recommender import CalibrationProfile, TrustedConfig, TrustedRecommender
from .validation_protocols import make_folds, physical_board_id, write_fold_manifest, assert_no_physical_board_leakage


def safe_config_grid(smoke: bool = False) -> list[TrustedConfig]:
    if smoke:
        return [
            TrustedConfig(
                top_k=5,
                descriptor_weight=0.5,
                prior_weight=0.0,
                use_fgw=True,
                use_prior=False,
                sparse_tail_shrink=True,
            )
        ]
    return [
        TrustedConfig(
            top_k=top_k,
            descriptor_weight=descriptor_weight,
            prior_weight=0.0,
            kde_weight=0.0,
            use_fgw=True,
            use_prior=False,
            use_kde=False,
            sparse_tail_shrink=True,
            min_supported_pressure_cases=min_support,
            max_tail_adjustment_raw=max_adjustment,
        )
        for top_k in [5, 8]
        for descriptor_weight in [0.5, 0.75]
        for min_support in [3]
        for max_adjustment in [0.2, 0.4, 0.5]
    ]


def _error(trace, observed) -> float:
    return float(abs(trace.recommended_pressure_raw - observed.press_raw))


def _median(train_cases: Sequence) -> float:
    return float(np.median([case.press_raw for case in train_cases]))


def _mode(train_cases: Sequence) -> float:
    values, counts = np.unique(np.round([case.press_raw for case in train_cases], 6), return_counts=True)
    return float(values[int(np.argmax(counts))])


def _descriptor_cbr(engine, held, train_cases: Sequence) -> float:
    config = TrustedConfig(top_k=1, descriptor_weight=1.0, prior_weight=0.0, use_fgw=False, use_prior=False)
    return float(TrustedRecommender(engine, config).recommend(held, train_cases).recommended_pressure_raw)


def select_grouped_config(engine, train_cases: Sequence, protocol: str, smoke: bool = False, max_inner_folds: int | None = None):
    candidates = safe_config_grid(smoke=smoke)
    folds = make_folds(train_cases, protocol=protocol, max_folds=max_inner_folds)
    rows = []
    for config_id, config in enumerate(candidates):
        errors = []
        started = perf_counter()
        for fold in folds:
            if len(fold.train_cases) < 2:
                continue
            recommender = TrustedRecommender(engine, config)
            for held in fold.test_cases:
                errors.append(_error(recommender.recommend(held, fold.train_cases, CalibrationProfile()), held))
        rows.append(
            {
                "config_id": config_id,
                **asdict(config),
                "inner_test_sides": len(errors),
                "inner_pressure_mae_raw": float(np.mean(errors)) if errors else np.nan,
                "runtime_ms": 1000.0 * (perf_counter() - started),
            }
        )
    frame = pd.DataFrame(rows)
    valid = frame.dropna(subset=["inner_pressure_mae_raw"]).copy()
    if valid.empty:
        raise ValueError("Grouped configuration selection has no evaluable configuration.")
    valid = valid.sort_values(
        [
            "inner_pressure_mae_raw",
            "max_tail_adjustment_raw",
            "min_supported_pressure_cases",
            "top_k",
            "descriptor_weight",
        ]
    )
    selected_id = int(valid.iloc[0]["config_id"])
    frame["selected"] = (frame["config_id"] == selected_id).astype(int)
    return candidates[selected_id], frame


def calibrate_grouped_profile(engine, train_cases: Sequence, config: TrustedConfig, protocol: str, max_inner_folds: int | None = None) -> CalibrationProfile:
    rows = []
    for fold in make_folds(train_cases, protocol=protocol, max_folds=max_inner_folds):
        if len(fold.train_cases) < 2:
            continue
        recommender = TrustedRecommender(engine, config)
        for held in fold.test_cases:
            trace = recommender.recommend(held, fold.train_cases, CalibrationProfile())
            rows.append(
                {
                    "board_id": str(held.board_id),
                    "physical_board_id": physical_board_id(str(held.board_id)),
                    "pressure_abs_error_raw": _error(trace, held),
                    "min_normalized_distance": trace.min_normalized_distance,
                    "effective_neighbor_count": trace.effective_neighbor_count,
                    "confidence_uncalibrated": trace.confidence,
                }
            )
    if not rows:
        return CalibrationProfile()
    frame = pd.DataFrame(rows)
    return CalibrationProfile(
        residual_q80_raw=float(frame["pressure_abs_error_raw"].quantile(0.80)),
        residual_q90_raw=float(frame["pressure_abs_error_raw"].quantile(0.90)),
        distance_q95=float(frame["min_normalized_distance"].quantile(0.95)),
        confidence_threshold=min(float(frame["confidence_uncalibrated"].quantile(0.10)), 0.35),
        oof_rows=rows,
    )


def summarize_results(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method, frame in results.groupby("method"):
        rows.append(
            {
                "method": method,
                "n_boards": int(len(frame)),
                "n_sides": int(len(frame)),
                "n_physical_boards": int(frame["physical_board_id"].nunique()),
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


def clustered_paired_report(results: pd.DataFrame, reference: str = "KOTMA-SR", seed: int = 2026) -> pd.DataFrame:
    wide = results.pivot(index=["physical_board_id", "board_id"], columns="method", values="pressure_abs_error_raw")
    if reference not in wide:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    groups = sorted(wide.index.get_level_values("physical_board_id").unique())
    rows = []
    for comparator in wide.columns:
        if comparator == reference:
            continue
        diff = (wide[comparator] - wide[reference]).dropna()
        side_values = diff.to_numpy(dtype=float)
        boots = []
        for _ in range(10000):
            chosen = rng.choice(groups, size=len(groups), replace=True)
            sample = np.concatenate(
                [np.atleast_1d(diff.loc[group].to_numpy(dtype=float)) if group in diff.index.get_level_values(0) else np.array([]) for group in chosen]
            )
            boots.append(float(np.mean(sample)) if len(sample) else np.nan)
        boots = np.asarray(boots, dtype=float)
        try:
            p = float(wilcoxon(side_values).pvalue)
        except ValueError:
            p = np.nan
        rows.append(
            {
                "reference": reference,
                "comparator": comparator,
                "n_sides": int(len(side_values)),
                "n_physical_boards": int(len(groups)),
                "mean_advantage_raw": float(np.mean(side_values)),
                "cluster_bootstrap_ci_low": float(np.nanquantile(boots, 0.025)),
                "cluster_bootstrap_ci_high": float(np.nanquantile(boots, 0.975)),
                "prob_reference_better_cluster_bootstrap": float(np.nanmean(boots > 0)),
                "bootstrap_ci_low": float(np.nanquantile(boots, 0.025)),
                "bootstrap_ci_high": float(np.nanquantile(boots, 0.975)),
                "prob_reference_better_bootstrap": float(np.nanmean(boots > 0)),
                "p_wilcoxon": p,
                "reference_wins": int(np.sum(side_values > 1e-9)),
                "ties": int(np.sum(np.abs(side_values) <= 1e-9)),
                "comparator_wins": int(np.sum(side_values < -1e-9)),
            }
        )
    return pd.DataFrame(rows)


def evaluate_grouped_nested(
    records: Sequence,
    engine,
    output_dir: str | Path,
    protocol: str = "pcb_group_lobo",
    smoke: bool = False,
    max_outer_folds: int | None = None,
    max_inner_folds: int | None = None,
) -> dict[str, pd.DataFrame]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    folds = make_folds(records, protocol=protocol, max_folds=max_outer_folds)
    if protocol == "pcb_group_lobo":
        assert_no_physical_board_leakage(folds)
    manifest = write_fold_manifest(folds, output_dir / f"{protocol}_fold_manifest.csv")
    result_rows, trace_rows, selection_rows, calibration_rows = [], [], [], []
    for fold_index, fold in enumerate(folds, start=1):
        print(f"[{protocol}] outer {fold_index}/{len(folds)} group={fold.fold_id}", flush=True)
        selected, selection = select_grouped_config(
            engine,
            fold.train_cases,
            protocol=protocol,
            smoke=smoke,
            max_inner_folds=max_inner_folds,
        )
        selection.insert(0, "outer_fold_id", fold.fold_id)
        selection_rows.append(selection)
        calibration = calibrate_grouped_profile(
            engine,
            fold.train_cases,
            selected,
            protocol=protocol,
            max_inner_folds=max_inner_folds if smoke else None,
        )
        calibration_rows.extend({"outer_fold_id": fold.fold_id, **row} for row in calibration.oof_rows)
        for held in fold.test_cases:
            trace = TrustedRecommender(engine, selected).recommend(held, fold.train_cases, calibration)
            unconstrained = TrustedRecommender(
                engine,
                TrustedConfig(top_k=8, descriptor_weight=0.5, prior_weight=0.0, use_fgw=True, use_prior=False),
            ).recommend(held, fold.train_cases, calibration)
            trace_rows.append({"outer_fold_id": fold.fold_id, **trace.as_dict()})
            methods = {
                "KOTMA-SR": trace.recommended_pressure_raw,
                "KOTMA-SR (unconstrained)": unconstrained.recommended_pressure_raw,
                "CBR": _descriptor_cbr(engine, held, fold.train_cases),
                "Training median": _median(fold.train_cases),
                "Training mode": _mode(fold.train_cases),
            }
            for method, pressure in methods.items():
                error = float(abs(pressure - held.press_raw))
                result_rows.append(
                    {
                        "protocol": protocol,
                        "outer_fold_id": fold.fold_id,
                        "physical_board_id": physical_board_id(str(held.board_id)),
                        "board_id": str(held.board_id),
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
                    }
                )
    results = pd.DataFrame(result_rows)
    traces = pd.DataFrame(trace_rows)
    selections = pd.concat(selection_rows, ignore_index=True)
    calibration = pd.DataFrame(calibration_rows)
    summary = summarize_results(results)
    paired = clustered_paired_report(results)
    results.to_csv(output_dir / f"{protocol}_outer_results.csv", index=False)
    traces.to_csv(output_dir / f"{protocol}_traces.csv", index=False)
    selections.to_csv(output_dir / f"{protocol}_config_selection.csv", index=False)
    calibration.to_csv(output_dir / f"{protocol}_calibration_oof.csv", index=False)
    summary.to_csv(output_dir / f"{protocol}_primary_statistics.csv", index=False)
    paired.to_csv(output_dir / f"{protocol}_paired_statistics.csv", index=False)
    return {
        "fold_manifest": manifest,
        "results": results,
        "traces": traces,
        "selections": selections,
        "calibration": calibration,
        "summary": summary,
        "paired": paired,
    }

