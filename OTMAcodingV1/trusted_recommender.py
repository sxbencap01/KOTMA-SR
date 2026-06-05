"""Leakage-safe, traceable first-article process-parameter recommendation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from time import perf_counter
from typing import Sequence

import numpy as np
try:
    import torch
except Exception:  # pragma: no cover - optional GPU dependency
    torch = None

try:
    from .data_loader import ProcessRanges, build_board_record
except ImportError:
    from data_loader import ProcessRanges, build_board_record


PRESSURE_RANGE = ProcessRanges().pressure
VELOCITY_RANGE = ProcessRanges().velocity


def _raw_pressure(norm_pressure: float) -> float:
    lo, hi = PRESSURE_RANGE
    return float(lo + norm_pressure * (hi - lo))


def _raw_velocity(norm_velocity: float) -> float:
    lo, hi = VELOCITY_RANGE
    return float(lo + norm_velocity * (hi - lo))


def stable_similarity_weights(distances: np.ndarray, temperature: float | None = None) -> np.ndarray:
    distances = np.asarray(distances, dtype=float)
    if distances.size == 0:
        return distances
    if not np.all(np.isfinite(distances)):
        raise ValueError("Similarity distances must be finite.")
    positive = distances[distances > np.min(distances) + 1e-12]
    if temperature is None:
        temperature = float(np.median(positive - np.min(distances))) if positive.size else 1.0
    temperature = max(float(temperature), 1e-6)
    logits = -(distances - np.min(distances)) / temperature
    logits = np.clip(logits, -700.0, 0.0)
    weights = np.exp(logits)
    total = float(np.sum(weights))
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Similarity weights could not be normalized.")
    weights /= total
    return weights


def board_descriptor(record) -> np.ndarray:
    comps = np.asarray(record.comps_raw, dtype=float)
    dims = np.asarray(record.board_dim, dtype=float)
    pad_area = np.asarray(comps[:, 5], dtype=float)
    aperture_ratio = np.asarray(comps[:, 6], dtype=float)
    aspect = np.asarray(comps[:, 7], dtype=float)
    return np.array(
        [
            np.log1p(len(comps)),
            np.log1p(max(dims[0], 0.0)),
            np.log1p(max(dims[1], 0.0)),
            np.log1p(max(dims[2], 0.0)),
            float(np.mean(pad_area)),
            float(np.std(pad_area)),
            float(np.mean(aperture_ratio)),
            float(np.std(aperture_ratio)),
            float(np.mean(aspect)),
            float(np.std(aspect)),
            float(np.ptp(comps[:, 0])),
            float(np.ptp(comps[:, 1])),
        ],
        dtype=float,
    )


@dataclass(frozen=True)
class TrustedConfig:
    top_k: int = 8
    descriptor_weight: float = 0.75
    prior_weight: float = 0.40
    kde_weight: float = 0.0
    use_fgw: bool = True
    use_prior: bool = True
    use_kde: bool = False
    engineering_tolerance_raw: float = 0.4
    strict_tolerance_raw: float = 0.2
    min_effective_neighbors: float = 2.0
    interval_review_width_raw: float = 0.8
    disagreement_review_raw: float = 0.4
    sparse_tail_shrink: bool = False
    min_supported_pressure_cases: int = 3
    max_tail_adjustment_raw: float = 0.5
    pressure_grid_raw: float = 0.1


@dataclass
class CalibrationProfile:
    residual_q80_raw: float = 0.4
    residual_q90_raw: float = 0.6
    distance_q95: float = np.inf
    confidence_threshold: float = 0.35
    oof_rows: list[dict] = field(default_factory=list)


@dataclass
class RecommendationTrace:
    board_id: str
    recommended_pressure_raw: float
    recommended_velocity_raw: float
    recommended_pressure_norm: float
    recommended_velocity_norm: float
    interval_80_low_raw: float
    interval_80_high_raw: float
    interval_90_low_raw: float
    interval_90_high_raw: float
    confidence: float
    manual_review: bool
    review_reasons: list[str]
    fired_rules: list[str]
    neighbor_ids: list[str]
    neighbor_weights: list[float]
    neighbor_distances: list[float]
    effective_neighbor_count: float
    min_normalized_distance: float
    retrieval_pressure_raw: float
    prior_pressure_raw: float
    retrieval_contribution: float
    prior_contribution: float
    descriptor_cbr_pressure_raw: float
    structural_pressure_raw: float
    descriptor_cbr_support: int
    supported_pressure_low_raw: float
    supported_pressure_high_raw: float
    safety_action: str
    runtime_ms: float

    def as_dict(self) -> dict:
        row = asdict(self)
        for key in ["review_reasons", "fired_rules", "neighbor_ids", "neighbor_weights", "neighbor_distances"]:
            row[key] = ";".join(map(str, row[key]))
        return row


class TrustedRecommender:
    """Traceable case reasoning with fold-local scaling and empirical policies."""

    def __init__(self, engine, config: TrustedConfig | None = None):
        self.engine = engine
        self.config = config or TrustedConfig()
        self._fgw_cache = getattr(engine, "fgw_pair_cache", {})
        if not hasattr(engine, "fgw_pair_cache"):
            engine.fgw_pair_cache = self._fgw_cache

    @staticmethod
    def _repr_signature(record) -> str:
        pos, feat, weights = record.ot_repr
        return "|".join(
            [
                str(record.board_id),
                str(np.asarray(pos).shape),
                f"{float(np.sum(pos)):.8g}",
                f"{float(np.sum(feat)):.8g}",
                f"{float(np.sum(weights)):.8g}",
            ]
        )

    def _unique_boards(self, records: Sequence) -> list:
        seen = {}
        for record in records:
            seen.setdefault(record.board_id, record)
        return [seen[key] for key in sorted(seen)]

    def _descriptor_distances(self, target, train_boards: Sequence) -> np.ndarray:
        x_train = np.vstack([board_descriptor(record) for record in train_boards])
        xt = board_descriptor(target)
        center = np.mean(x_train, axis=0)
        scale = np.std(x_train, axis=0)
        scale[scale < 1e-9] = 1.0
        xz = (x_train - center) / scale
        xtz = (xt - center) / scale
        if (
            getattr(self.engine, "resolved_device", lambda: "cpu")() == "cuda"
            and torch is not None
            and xz.size >= 100000
        ):
            device = "cuda"
            x_tensor = torch.as_tensor(xz, dtype=torch.float32, device=device)
            xt_tensor = torch.as_tensor(xtz, dtype=torch.float32, device=device)
            return torch.linalg.vector_norm(x_tensor - xt_tensor, dim=1).detach().cpu().numpy()
        return np.linalg.norm(xz - xtz, axis=1)

    def _fgw_distances(self, target, train_boards: Sequence) -> np.ndarray:
        if not self.config.use_fgw or self.config.descriptor_weight >= 1.0:
            return np.zeros(len(train_boards), dtype=float)
        rows = []
        for record in train_boards:
            key = (
                tuple(sorted((self._repr_signature(target), self._repr_signature(record)))),
                getattr(self.engine.config, "ot_alpha", None),
                getattr(self.engine.config, "ot_reg", None),
            )
            if key not in self._fgw_cache:
                self._fgw_cache[key] = float(self.engine.compute_fgw_distance(target.ot_repr, record.ot_repr))
            rows.append(self._fgw_cache[key])
        return np.asarray(rows, dtype=float)

    @staticmethod
    def _robust_scale(values: np.ndarray) -> np.ndarray:
        values = np.asarray(values, dtype=float)
        positive = values[values > 1e-12]
        scale = float(np.median(positive)) if positive.size else 1.0
        return values / max(scale, 1e-9)

    def retrieve(self, target, train_records: Sequence) -> list[dict]:
        boards = self._unique_boards(train_records)
        if not boards:
            return []
        descriptor = self._robust_scale(self._descriptor_distances(target, boards))
        fgw = self._robust_scale(self._fgw_distances(target, boards))
        alpha = float(np.clip(self.config.descriptor_weight, 0.0, 1.0))
        combined = alpha * descriptor + (1.0 - alpha) * fgw
        order = np.argsort(combined)[: min(self.config.top_k, len(boards))]
        weights = stable_similarity_weights(combined[order])
        return [
            {
                "board_id": boards[idx].board_id,
                "record": boards[idx],
                "distance": float(combined[idx]),
                "descriptor_distance": float(descriptor[idx]),
                "fgw_distance": float(fgw[idx]),
                "weight": float(weight),
            }
            for idx, weight in zip(order, weights)
        ]

    @staticmethod
    def _policy(train_records: Sequence) -> tuple[float, float, float]:
        params = np.vstack([record.params for record in train_records])
        velocities = np.round(params[:, 1], 6)
        values, counts = np.unique(velocities, return_counts=True)
        mode_idx = int(np.argmax(counts))
        velocity_mode = float(values[mode_idx])
        velocity_share = float(counts[mode_idx] / len(velocities))
        pressure_median = float(np.median(params[:, 0]))
        return pressure_median, velocity_mode, velocity_share

    def _prior_pressure(self, target, train_records: Sequence) -> float:
        if not self.config.use_prior or len(train_records) < 5:
            return float(np.median([record.params[0] for record in train_records]))
        x = np.vstack([board_descriptor(record) for record in train_records])
        y = np.asarray([record.params[0] for record in train_records], dtype=float)
        center = x.mean(axis=0)
        scale = x.std(axis=0)
        scale[scale < 1e-9] = 1.0
        xz = (x - center) / scale
        xt = (board_descriptor(target) - center) / scale
        xa = np.column_stack([np.ones(len(xz)), xz])
        reg = np.eye(xa.shape[1])
        reg[0, 0] = 0.0
        coef = np.linalg.solve(xa.T @ xa + reg, xa.T @ y)
        return float(np.clip(np.r_[1.0, xt] @ coef, 0.0, 1.0))

    def _descriptor_cbr_pressure(self, target, train_records: Sequence) -> tuple[float, int, float, float]:
        boards = self._unique_boards(train_records)
        distances = self._descriptor_distances(target, boards)
        nearest = boards[int(np.argmin(distances))]
        nearest_raw = _raw_pressure(float(nearest.params[0]))
        train_raw = np.round([_raw_pressure(float(record.params[0])) for record in boards], 6)
        values, counts = np.unique(train_raw, return_counts=True)
        support = int(counts[int(np.argmin(np.abs(values - nearest_raw)))])
        supported = values[counts >= max(int(self.config.min_supported_pressure_cases), 1)]
        if not supported.size:
            supported = values
        return nearest_raw, support, float(np.min(supported)), float(np.max(supported))

    def _apply_sparse_tail_shrink(
        self,
        target,
        train_records: Sequence,
        structural_pressure_raw: float,
    ) -> tuple[float, float, int, float, float, str]:
        cbr_raw, support, supported_low, supported_high = self._descriptor_cbr_pressure(target, train_records)
        if not self.config.sparse_tail_shrink:
            return structural_pressure_raw, cbr_raw, support, supported_low, supported_high, "structural_recommendation"
        is_sparse_tail = support < self.config.min_supported_pressure_cases or cbr_raw < supported_low or cbr_raw > supported_high
        if is_sparse_tail:
            delta = float(
                np.clip(
                    structural_pressure_raw - cbr_raw,
                    -self.config.max_tail_adjustment_raw,
                    self.config.max_tail_adjustment_raw,
                )
            )
            pressure_raw = cbr_raw + delta
            action = "bounded_structural_tail_correction"
        else:
            pressure_raw = cbr_raw
            action = "descriptor_cbr_safeguard"
        step = max(float(self.config.pressure_grid_raw), 1e-9)
        pressure_raw = float(np.round(pressure_raw / step) * step)
        if action == "bounded_structural_tail_correction":
            grid_low = float(np.ceil((cbr_raw - self.config.max_tail_adjustment_raw) / step) * step)
            grid_high = float(np.floor((cbr_raw + self.config.max_tail_adjustment_raw) / step) * step)
            if grid_low <= grid_high:
                pressure_raw = float(np.clip(pressure_raw, grid_low, grid_high))
        pressure_raw = float(np.clip(pressure_raw, PRESSURE_RANGE[0], PRESSURE_RANGE[1]))
        return pressure_raw, cbr_raw, support, supported_low, supported_high, action

    def recommend(self, target, train_records: Sequence, calibration: CalibrationProfile | None = None) -> RecommendationTrace:
        started = perf_counter()
        calibration = calibration or CalibrationProfile()
        neighbors = self.retrieve(target, train_records)
        if not neighbors:
            raise ValueError("At least one historical board is required for recommendation.")
        weights = np.asarray([row["weight"] for row in neighbors], dtype=float)
        pressures = np.asarray([row["record"].params[0] for row in neighbors], dtype=float)
        retrieval = float(np.average(pressures, weights=weights))
        prior = self._prior_pressure(target, train_records)
        prior_weight = float(np.clip(self.config.prior_weight if self.config.use_prior else 0.0, 0.0, 1.0))
        pressure = float((1.0 - prior_weight) * retrieval + prior_weight * prior)
        _, velocity_mode, velocity_share = self._policy(train_records)
        distances = np.asarray([row["distance"] for row in neighbors], dtype=float)
        effective_neighbors = float(1.0 / np.sum(np.square(weights)))
        min_distance = float(np.min(distances))
        distance_score = float(np.exp(-min_distance / max(calibration.distance_q95, 1e-9))) if np.isfinite(calibration.distance_q95) else 1.0
        support_score = float(np.clip(effective_neighbors / max(self.config.top_k, 1), 0.0, 1.0))
        agreement_score = float(1.0 - np.clip(abs(_raw_pressure(retrieval) - _raw_pressure(prior)) / self.config.disagreement_review_raw, 0.0, 1.0))
        confidence = float(np.clip(0.45 * distance_score + 0.35 * support_score + 0.20 * agreement_score, 0.0, 1.0))
        structural_pressure_raw = _raw_pressure(pressure)
        pressure_raw, cbr_raw, cbr_support, supported_low, supported_high, safety_action = self._apply_sparse_tail_shrink(
            target,
            train_records,
            structural_pressure_raw,
        )
        pressure = float((pressure_raw - PRESSURE_RANGE[0]) / (PRESSURE_RANGE[1] - PRESSURE_RANGE[0]))
        q80 = float(calibration.residual_q80_raw)
        q90 = float(calibration.residual_q90_raw)
        reasons = []
        if effective_neighbors < self.config.min_effective_neighbors:
            reasons.append("low_neighbor_support")
        if np.isfinite(calibration.distance_q95) and min_distance > calibration.distance_q95:
            reasons.append("ood_distance")
        if abs(_raw_pressure(retrieval) - _raw_pressure(prior)) > self.config.disagreement_review_raw:
            reasons.append("retrieval_prior_disagreement")
        wide_interval = bool(2.0 * q90 > self.config.interval_review_width_raw)
        if confidence < calibration.confidence_threshold:
            reasons.append("low_confidence")
        fired = [
            "training_fold_empirical_velocity_policy",
            "case_retrieval",
            "fold_local_descriptor_scaling",
        ]
        if self.config.use_fgw and self.config.descriptor_weight < 1.0:
            fired.append("optional_fgw_alignment")
        if self.config.use_prior:
            fired.append("empirical_pressure_prior")
        if self.config.sparse_tail_shrink:
            fired.append("fold_local_sparse_tail_safeguard")
        if wide_interval:
            fired.append("wide_prediction_interval_warning")
        return RecommendationTrace(
            board_id=str(target.board_id),
            recommended_pressure_raw=pressure_raw,
            recommended_velocity_raw=_raw_velocity(velocity_mode),
            recommended_pressure_norm=pressure,
            recommended_velocity_norm=velocity_mode,
            interval_80_low_raw=max(PRESSURE_RANGE[0], pressure_raw - q80),
            interval_80_high_raw=min(PRESSURE_RANGE[1], pressure_raw + q80),
            interval_90_low_raw=max(PRESSURE_RANGE[0], pressure_raw - q90),
            interval_90_high_raw=min(PRESSURE_RANGE[1], pressure_raw + q90),
            confidence=confidence,
            manual_review=bool(reasons),
            review_reasons=reasons,
            fired_rules=fired,
            neighbor_ids=[str(row["board_id"]) for row in neighbors],
            neighbor_weights=[float(row["weight"]) for row in neighbors],
            neighbor_distances=[float(row["distance"]) for row in neighbors],
            effective_neighbor_count=effective_neighbors,
            min_normalized_distance=min_distance,
            retrieval_pressure_raw=_raw_pressure(retrieval),
            prior_pressure_raw=_raw_pressure(prior),
            retrieval_contribution=1.0 - prior_weight,
            prior_contribution=prior_weight,
            descriptor_cbr_pressure_raw=cbr_raw,
            structural_pressure_raw=structural_pressure_raw,
            descriptor_cbr_support=cbr_support,
            supported_pressure_low_raw=supported_low,
            supported_pressure_high_raw=supported_high,
            safety_action=safety_action,
            runtime_ms=1000.0 * (perf_counter() - started),
        )


def board_records(records: Sequence, engine) -> list:
    grouped: dict[str, list] = {}
    for record in records:
        grouped.setdefault(record.board_id, []).append(record)
    boards = []
    for board_id in sorted(grouped):
        board = build_board_record(grouped[board_id], engine=engine)
        boards.append(board)
    return boards

