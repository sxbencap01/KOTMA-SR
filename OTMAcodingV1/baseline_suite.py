"""Fair small-data baseline benchmark under physical-board grouped folds."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Callable, Sequence
import warnings

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from .trusted_recommender import TrustedConfig, TrustedRecommender, board_descriptor, stable_similarity_weights
from .validation_protocols import make_folds, physical_board_id


PRESSURE_LOW, PRESSURE_HIGH, PRESSURE_STEP = 5.0, 8.0, 0.1


def executable_pressure(value: float) -> float:
    value = float(np.clip(value, PRESSURE_LOW, PRESSURE_HIGH))
    return float(np.round(value / PRESSURE_STEP) * PRESSURE_STEP)


def _xy(cases: Sequence):
    return np.vstack([board_descriptor(case) for case in cases]), np.asarray([case.press_raw for case in cases], dtype=float)


def _scaled_descriptor_distances(target, train_cases: Sequence) -> np.ndarray:
    x, _ = _xy(train_cases)
    xt = board_descriptor(target)
    center = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-9] = 1.0
    return np.linalg.norm((x - center) / scale - (xt - center) / scale, axis=1)


def _local_pressure(target, train_cases: Sequence, k: int, reducer: str) -> float:
    distances = _scaled_descriptor_distances(target, train_cases)
    order = np.argsort(distances)[: min(k, len(train_cases))]
    values = np.asarray([train_cases[index].press_raw for index in order], dtype=float)
    if reducer == "weighted":
        weights = stable_similarity_weights(distances[order])
        return executable_pressure(np.average(values, weights=weights))
    if reducer == "median":
        return executable_pressure(np.median(values))
    unique, counts = np.unique(np.round(values, 6), return_counts=True)
    return executable_pressure(unique[int(np.argmax(counts))])


@dataclass(frozen=True)
class BaselineSpec:
    name: str
    kind: str
    params: tuple[dict, ...]


def _specs(smoke: bool = False) -> list[BaselineSpec]:
    specs = [
        BaselineSpec("Training median", "simple", ({"reducer": "median"},)),
        BaselineSpec("Training mode", "simple", ({"reducer": "mode"},)),
        BaselineSpec("Top-1 CBR", "local", ({"k": 1, "reducer": "weighted"},)),
        BaselineSpec("Weighted kNN-CBR", "local", tuple({"k": k, "reducer": "weighted"} for k in [3, 5, 8])),
        BaselineSpec("Local median CBR", "local", tuple({"k": k, "reducer": "median"} for k in [3, 5, 8])),
        BaselineSpec("Local mode CBR", "local", tuple({"k": k, "reducer": "mode"} for k in [3, 5, 8])),
        BaselineSpec("Ridge", "sklearn", tuple({"alpha": alpha} for alpha in [0.1, 1.0, 10.0])),
        BaselineSpec("Elastic Net", "sklearn", tuple({"alpha": alpha, "l1_ratio": ratio} for alpha in [0.01, 0.1] for ratio in [0.2, 0.8])),
        BaselineSpec("RBF-SVR", "sklearn", tuple({"C": c, "gamma": gamma} for c in [1.0, 10.0] for gamma in ["scale", 0.1])),
        BaselineSpec("Gaussian Process", "sklearn", ({"alpha": 1e-4}, {"alpha": 1e-2})),
        BaselineSpec("Random Forest", "sklearn", ({"max_depth": None}, {"max_depth": 4})),
        BaselineSpec("ExtraTrees", "sklearn", ({"max_depth": None}, {"max_depth": 4})),
        BaselineSpec("XGBoost", "optional", ({"max_depth": 2}, {"max_depth": 3})),
        BaselineSpec("CatBoost", "optional", ({"depth": 2}, {"depth": 3})),
        BaselineSpec("LightGBM", "optional", ({"max_depth": 2}, {"max_depth": 3})),
        BaselineSpec("Wasserstein-only", "ot", ({"descriptor_weight": 0.0, "ot_alpha": 0.0},)),
        BaselineSpec("GW-only", "ot", ({"descriptor_weight": 0.0, "ot_alpha": 1.0},)),
        BaselineSpec("FGW-only", "ot", ({"descriptor_weight": 0.0, "ot_alpha": None},)),
        BaselineSpec("Descriptor + FGW", "ot", ({"descriptor_weight": 0.5, "ot_alpha": None},)),
    ]
    if smoke:
        keep = {"Training median", "Top-1 CBR", "Weighted kNN-CBR", "Ridge", "ExtraTrees", "CatBoost", "Descriptor + FGW"}
        specs = [spec for spec in specs if spec.name in keep]
    return specs


def _make_model(name: str, params: dict):
    if name == "Ridge":
        return make_pipeline(StandardScaler(), Ridge(**params))
    if name == "Elastic Net":
        return make_pipeline(StandardScaler(), ElasticNet(max_iter=5000, random_state=2026, **params))
    if name == "RBF-SVR":
        return make_pipeline(StandardScaler(), SVR(kernel="rbf", epsilon=0.05, **params))
    if name == "Gaussian Process":
        kernel = ConstantKernel(1.0) * RBF(length_scale=1.0) + WhiteKernel(noise_level=1e-4)
        return make_pipeline(StandardScaler(), GaussianProcessRegressor(kernel=kernel, normalize_y=True, random_state=2026, **params))
    if name == "Random Forest":
        return RandomForestRegressor(n_estimators=160, min_samples_leaf=2, random_state=2026, n_jobs=-1, **params)
    if name == "ExtraTrees":
        return ExtraTreesRegressor(n_estimators=160, min_samples_leaf=2, random_state=2026, n_jobs=-1, **params)
    if name == "XGBoost":
        from xgboost import XGBRegressor

        return XGBRegressor(n_estimators=100, learning_rate=0.05, min_child_weight=2, subsample=0.9, colsample_bytree=0.9, random_state=2026, n_jobs=1, verbosity=0, **params)
    if name == "CatBoost":
        from catboost import CatBoostRegressor

        return CatBoostRegressor(iterations=120, learning_rate=0.05, loss_function="MAE", random_seed=2026, verbose=False, allow_writing_files=False, **params)
    if name == "LightGBM":
        from lightgbm import LGBMRegressor

        return LGBMRegressor(n_estimators=100, learning_rate=0.05, num_leaves=7, min_child_samples=4, random_state=2026, verbosity=-1, **params)
    raise ValueError(f"Unknown sklearn baseline: {name}")


def _predict(spec: BaselineSpec, params: dict, engine, train_cases: Sequence, test_cases: Sequence) -> list[float]:
    if spec.kind == "simple":
        values = np.asarray([case.press_raw for case in train_cases], dtype=float)
        pred = np.median(values) if params["reducer"] == "median" else pd.Series(values).mode().iloc[0]
        return [executable_pressure(pred)] * len(test_cases)
    if spec.kind == "local":
        return [_local_pressure(held, train_cases, **params) for held in test_cases]
    if spec.kind in {"sklearn", "optional"}:
        model = _make_model(spec.name, params)
        x, y = _xy(train_cases)
        model.fit(x, y)
        return [executable_pressure(value) for value in model.predict(np.vstack([board_descriptor(case) for case in test_cases]))]
    if spec.kind == "ot":
        config = TrustedConfig(
            top_k=8,
            descriptor_weight=float(params["descriptor_weight"]),
            prior_weight=0.0,
            use_fgw=True,
            use_prior=False,
            sparse_tail_shrink=False,
        )
        old_alpha = engine.config.ot_alpha
        engine.config.ot_alpha = params["ot_alpha"]
        try:
            recommender = TrustedRecommender(engine, config)
            return [executable_pressure(recommender.recommend(held, train_cases).recommended_pressure_raw) for held in test_cases]
        finally:
            engine.config.ot_alpha = old_alpha
    raise ValueError(f"Unsupported baseline kind: {spec.kind}")


def _select_params(spec: BaselineSpec, engine, train_cases: Sequence, protocol: str, max_inner_folds: int | None):
    rows = []
    for param_id, params in enumerate(spec.params):
        errors = []
        for fold in make_folds(train_cases, protocol=protocol, max_folds=max_inner_folds):
            if len(fold.train_cases) < 3:
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    predictions = _predict(spec, params, engine, fold.train_cases, fold.test_cases)
            except ImportError as exc:
                return None, pd.DataFrame([{"method": spec.name, "status": "skipped_dependency", "detail": str(exc)}])
            errors.extend(abs(pred - held.press_raw) for pred, held in zip(predictions, fold.test_cases))
        rows.append({"method": spec.name, "param_id": param_id, "params": repr(params), "inner_mae": float(np.mean(errors)) if errors else np.nan})
    selection = pd.DataFrame(rows)
    valid = selection.dropna(subset=["inner_mae"]).sort_values(["inner_mae", "param_id"])
    if valid.empty:
        return None, selection
    selected_id = int(valid.iloc[0]["param_id"])
    selection["selected"] = (selection["param_id"] == selected_id).astype(int)
    return spec.params[selected_id], selection


def _holm_adjust(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    valid = frame["p_wilcoxon"].notna()
    pvals = frame.loc[valid, "p_wilcoxon"].sort_values()
    adjusted = {}
    running = 0.0
    count = len(pvals)
    for rank, (index, value) in enumerate(pvals.items()):
        running = max(running, min(1.0, (count - rank) * float(value)))
        adjusted[index] = running
    frame["p_wilcoxon_holm"] = np.nan
    for index, value in adjusted.items():
        frame.loc[index, "p_wilcoxon_holm"] = value
    return frame


def benchmark_statistics(results: pd.DataFrame, reference: str = "KOTMA-SR", seed: int = 2026) -> pd.DataFrame:
    wide = results.pivot(index=["physical_board_id", "board_id"], columns="method", values="pressure_abs_error_raw")
    rng = np.random.default_rng(seed)
    groups = sorted(wide.index.get_level_values(0).unique())
    rows = []
    for comparator in wide.columns:
        if comparator == reference:
            continue
        diff = (wide[comparator] - wide[reference]).dropna()
        boots = []
        for _ in range(5000):
            chosen = rng.choice(groups, len(groups), replace=True)
            values = np.concatenate([np.atleast_1d(diff.loc[group].to_numpy(dtype=float)) for group in chosen if group in diff.index.get_level_values(0)])
            boots.append(float(values.mean()) if len(values) else np.nan)
        values = diff.to_numpy(dtype=float)
        try:
            p = float(wilcoxon(values).pvalue)
        except ValueError:
            p = np.nan
        rows.append(
            {
                "reference": reference,
                "comparator": comparator,
                "n_sides": len(values),
                "n_physical_boards": len(groups),
                "mean_advantage_raw": float(values.mean()),
                "cluster_bootstrap_ci_low": float(np.nanquantile(boots, 0.025)),
                "cluster_bootstrap_ci_high": float(np.nanquantile(boots, 0.975)),
                "p_wilcoxon": p,
                "reference_wins": int(np.sum(values > 1e-9)),
                "ties": int(np.sum(np.abs(values) <= 1e-9)),
                "comparator_wins": int(np.sum(values < -1e-9)),
            }
        )
    return _holm_adjust(pd.DataFrame(rows))


def evaluate_baseline_suite(
    records: Sequence,
    engine,
    safe_results: pd.DataFrame,
    output_dir: str | Path,
    protocol: str = "pcb_group_lobo",
    smoke: bool = False,
    max_outer_folds: int | None = None,
    max_inner_folds: int | None = None,
) -> dict[str, pd.DataFrame]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows, selection_rows = [], []
    for fold_index, fold in enumerate(make_folds(records, protocol, max_outer_folds), start=1):
        print(f"[benchmark] outer {fold_index} group={fold.fold_id}", flush=True)
        for spec in _specs(smoke=smoke):
            params, selection = _select_params(spec, engine, fold.train_cases, protocol, max_inner_folds)
            if not selection.empty:
                selection.insert(0, "outer_fold_id", fold.fold_id)
                selection_rows.append(selection)
            if params is None:
                continue
            started = perf_counter()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                predictions = _predict(spec, params, engine, fold.train_cases, fold.test_cases)
            elapsed = 1000.0 * (perf_counter() - started)
            for held, prediction in zip(fold.test_cases, predictions):
                error = float(abs(prediction - held.press_raw))
                rows.append(
                    {
                        "protocol": protocol,
                        "outer_fold_id": fold.fold_id,
                        "physical_board_id": physical_board_id(str(held.board_id)),
                        "board_id": str(held.board_id),
                        "method": spec.name,
                        "real_pressure_raw": held.press_raw,
                        "recommended_pressure_raw": prediction,
                        "pressure_abs_error_raw": error,
                        "within_0_2_raw": float(error <= 0.2 + 1e-9),
                        "within_0_4_raw": float(error <= 0.4 + 1e-9),
                        "runtime_ms": elapsed / max(len(fold.test_cases), 1),
                    }
                )
    baseline = pd.DataFrame(rows)
    safe = safe_results[safe_results["method"].eq("KOTMA-SR")][baseline.columns].copy()
    combined = pd.concat([safe, baseline], ignore_index=True)
    summary = (
        combined.groupby("method", as_index=False)
        .agg(
            n_sides=("board_id", "size"),
            n_physical_boards=("physical_board_id", "nunique"),
            pressure_mae_raw=("pressure_abs_error_raw", "mean"),
            pressure_median_abs_error_raw=("pressure_abs_error_raw", "median"),
            within_0_2_raw_rate=("within_0_2_raw", "mean"),
            within_0_4_raw_rate=("within_0_4_raw", "mean"),
            median_runtime_ms=("runtime_ms", "median"),
        )
        .sort_values("pressure_mae_raw")
    )
    statistics = benchmark_statistics(combined)
    selections = pd.concat(selection_rows, ignore_index=True) if selection_rows else pd.DataFrame()
    combined.to_csv(output_dir / "benchmark_outer_results.csv", index=False)
    summary.to_csv(output_dir / "benchmark_summary.csv", index=False)
    statistics.to_csv(output_dir / "benchmark_paired_statistics.csv", index=False)
    selections.to_csv(output_dir / "benchmark_nested_selection.csv", index=False)
    return {"benchmark_results": combined, "benchmark_summary": summary, "benchmark_paired": statistics, "benchmark_selections": selections}

