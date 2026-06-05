"""OT-MA geometry engine and real-candidate ranking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

import numpy as np
import pandas as pd
try:
    import torch
except Exception:  # pragma: no cover - optional GPU dependency
    torch = None

try:
    import ot
except Exception:  # pragma: no cover - optional dependency
    ot = None

from sklearn.cluster import MiniBatchKMeans


DEFAULT_FEAT_WEIGHTS = {"pos": 0.1, "area": 0.4, "ar": 1.0, "aspect": 0.5, "height": 0.5}


@dataclass
class OTMAConfig:
    base_k: int = 200
    top_k: int = 10
    ot_alpha: float | None = None
    ot_reg: float = 0.05
    kde_bandwidth: float = 0.1
    prediction_bandwidth: float = 0.5
    param_tradeoff: float = 1.0
    alpha_physics: float = 0.1
    lambda_physics: float = 1.5
    reject_distance: float = 0.6
    use_fgw: bool = True
    use_kde: bool = True
    use_physics: bool = True
    use_uncertainty: bool = True
    require_pot: bool = True
    frozen_majority_threshold: float = 0.90
    kde_mean_hybrid_gamma: float = 0.30
    learned_prior_weight: float = 0.20
    feature_distance_blend: float = 1.00
    compute_device: str = "auto"
    fgw_device: str = "cpu"


class OTMAEngine:
    def __init__(self, config: OTMAConfig | None = None, feat_weights: Dict[str, float] | None = None):
        self.config = config or OTMAConfig()
        self.feat_weights = feat_weights or DEFAULT_FEAT_WEIGHTS.copy()
        self.last_transport_plan = None
        self.fgw_pair_cache: Dict[tuple, float] = {}

    def resolved_device(self) -> str:
        requested = str(getattr(self.config, "compute_device", "auto")).lower()
        if requested == "cpu":
            return "cpu"
        if requested in {"cuda", "auto"} and torch is not None and torch.cuda.is_available():
            return "cuda"
        if requested == "cuda":
            raise RuntimeError("CUDA was requested but PyTorch CUDA is unavailable.")
        return "cpu"

    def resolved_fgw_device(self) -> str:
        requested = str(getattr(self.config, "fgw_device", "cpu")).lower()
        if requested == "auto":
            return "cpu"
        if requested == "cuda":
            if torch is None or not torch.cuda.is_available():
                raise RuntimeError("CUDA FGW was requested but PyTorch CUDA is unavailable.")
            return "cuda"
        return "cpu"

    @staticmethod
    def quality_scales(train_records: Sequence) -> Dict[str, Dict[str, float]]:
        values = {
            "volume_error": np.array([r.quality.volume_error for r in train_records], dtype=float),
            "offset_error": np.array([r.quality.offset_error for r in train_records], dtype=float),
            "shape_error": np.array([r.quality.shape_error for r in train_records], dtype=float),
            "ng_risk": np.array([r.quality.ng_rate for r in train_records], dtype=float),
        }
        scales = {}
        for key, arr in values.items():
            scales[key] = {
                "mean": float(np.mean(arr)) if len(arr) else 0.0,
                "std": float(np.std(arr) + 1e-9) if len(arr) else 1.0,
            }
        return scales

    @staticmethod
    def normalized_predicted_objective(pred: dict, scales: Dict[str, Dict[str, float]]) -> float:
        total = 0.0
        for key in ["volume_error", "offset_error", "shape_error", "ng_risk"]:
            total += (pred[key] - scales[key]["mean"]) / scales[key]["std"]
        return float(total)

    def coarsen_pcb(self, comps: np.ndarray, n_clusters: int | None = None, seed: int | None = 2026):
        n_clusters = int(n_clusters or self.config.base_k)
        n_clusters = min(max(1, n_clusters), len(comps))
        pos_all = comps[:, :2]
        try:
            from scipy.spatial import cKDTree

            tree = cKDTree(pos_all)
            density = np.array([len(tree.query_ball_point(p, r=0.05)) for p in pos_all])
            density = (density - density.min()) / (density.max() - density.min() + 1e-9)
        except Exception:
            density = np.zeros(len(comps))

        comps_aug = np.hstack([comps, density[:, None]])
        fill_risk_all = np.maximum(0.0, 0.6 - comps_aug[:, 6])
        release_risk_all = np.maximum(0.0, 1.5 - comps_aug[:, 7])

        if len(comps_aug) <= n_clusters:
            pos = comps_aug[:, :2]
            feat = np.hstack([comps_aug[:, 2:8], fill_risk_all[:, None], release_risk_all[:, None]])
            feat = (feat - feat.mean(0)) / (feat.std(0) + 1e-9)
            weights = comps_aug[:, 5].copy()
            weights = weights / (weights.sum() + 1e-9)
            return pos, feat, weights

        area_norm = comps_aug[:, 5:6].copy()
        area_norm = (area_norm - area_norm.min()) / (area_norm.max() - area_norm.min() + 1e-9)
        x_cluster = np.hstack([comps_aug[:, :2], 0.5 * area_norm])
        labels = MiniBatchKMeans(n_clusters=n_clusters, random_state=seed, batch_size=256, n_init=3).fit_predict(x_cluster)

        k_pos, k_feat, k_weights = [], [], []
        for k in range(n_clusters):
            mask = labels == k
            if not np.any(mask):
                continue
            cluster = comps_aug[mask]
            areas = cluster[:, 5]
            w = areas / (areas.sum() + 1e-9)
            k_pos.append(np.sum(cluster[:, :2] * w[:, None], axis=0))
            raw = np.sum(cluster[:, 2:8] * w[:, None], axis=0)
            fill_risk = np.mean(np.maximum(0.0, 0.6 - cluster[:, 6]))
            release_risk = np.mean(np.maximum(0.0, 1.5 - cluster[:, 7]))
            k_feat.append(np.append(raw, [fill_risk, release_risk]))
            k_weights.append(areas.sum())

        pos = np.asarray(k_pos, dtype=float)
        feat = np.asarray(k_feat, dtype=float)
        feat = (feat - feat.mean(0)) / (feat.std(0) + 1e-9)
        weights = np.asarray(k_weights, dtype=float)
        weights = weights / (weights.sum() + 1e-9)
        return pos, feat, weights

    def _feature_weight_vector(self, n_features: int) -> np.ndarray:
        if n_features != 8:
            return np.ones(n_features)
        fw = self.feat_weights
        return np.array(
            [
                fw.get("pos", 1.0) ** 0.5,
                fw.get("pos", 1.0) ** 0.5,
                1.0,
                fw.get("area", 1.0) ** 0.5,
                fw.get("ar", 1.0) ** 0.5,
                fw.get("aspect", 1.0) ** 0.5,
                fw.get("ar", 1.0) ** 0.5,
                fw.get("aspect", 1.0) ** 0.5,
            ],
            dtype=float,
        )

    def compute_fgw_distance(self, b1_repr, b2_repr, alpha_override=None, reg_override=None) -> float:
        pos1, feat1, w1 = b1_repr
        pos2, feat2, w2 = b2_repr
        pos1, feat1, w1 = np.asarray(pos1), np.asarray(feat1), np.asarray(w1)
        pos2, feat2, w2 = np.asarray(pos2), np.asarray(feat2), np.asarray(w2)
        w1 = w1 / (w1.sum() + 1e-9)
        w2 = w2 / (w2.sum() + 1e-9)
        heterogeneity = (np.std(w1) * np.sqrt(len(w1)) + np.std(w2) * np.sqrt(len(w2))) / 2.0

        if ot is None:
            if self.config.use_fgw and self.config.require_pot:
                raise ImportError(
                    "POT is required for manuscript FGW OT-MA experiments. "
                    "Install POT or run with --allow-no-pot-fallback for non-manuscript smoke tests."
                )
            geom = np.linalg.norm(pos1.mean(0) - pos2.mean(0))
            feat = np.linalg.norm(feat1.mean(0) - feat2.mean(0))
            self.last_transport_plan = np.outer(w1, w2)
            return float(geom + feat)

        device = self.resolved_fgw_device()
        if device == "cuda":
            pos1 = torch.as_tensor(pos1, dtype=torch.float32, device=device)
            pos2 = torch.as_tensor(pos2, dtype=torch.float32, device=device)
            feat1 = torch.as_tensor(feat1, dtype=torch.float32, device=device)
            feat2 = torch.as_tensor(feat2, dtype=torch.float32, device=device)
            w1 = torch.as_tensor(w1, dtype=torch.float32, device=device)
            w2 = torch.as_tensor(w2, dtype=torch.float32, device=device)
        c1 = ot.dist(pos1, pos1, metric="sqeuclidean")
        c2 = ot.dist(pos2, pos2, metric="sqeuclidean")
        c1 = c1 / (c1.max() + 1e-9)
        c2 = c2 / (c2.max() + 1e-9)
        w_vec = self._feature_weight_vector(feat1.shape[1])
        if device == "cuda":
            w_vec = torch.as_tensor(w_vec, dtype=torch.float32, device=device)
        m = ot.dist(feat1 * w_vec, feat2 * w_vec, metric="sqeuclidean")
        m = m / (m.max() + 1e-9)

        alpha = alpha_override
        if alpha is None:
            alpha = self.config.ot_alpha
        if alpha is None:
            alpha = float(0.3 + 0.6 * np.clip(heterogeneity / 0.5, 0.0, 1.0))
        epsilon = float(reg_override or self.config.ot_reg)

        try:
            dist, log = ot.gromov.entropic_fused_gromov_wasserstein2(
                m, c1, c2, w1, w2, loss_fun="square_loss", alpha=alpha, epsilon=epsilon,
                numItermax=2000, log=True, stopThr=1e-5
            )
            plan = log.get("G")
            self.last_transport_plan = plan.detach().cpu().numpy() if hasattr(plan, "detach") else plan
            return float(dist.detach().cpu().item()) if hasattr(dist, "detach") else float(dist)
        except Exception:
            if device == "cuda":
                plan = torch.outer(w1, w2)
                self.last_transport_plan = plan.detach().cpu().numpy()
                return float((torch.sum(m * plan) * (1.0 - alpha)).detach().cpu().item())
            self.last_transport_plan = np.outer(w1, w2)
            return float(np.sum(m * self.last_transport_plan) * (1.0 - alpha))

    def compute_stability(self, comps: np.ndarray, base_k: int = 200) -> float:
        k1 = min(base_k, len(comps))
        k2 = min(max(k1 + 1, int(k1 * 1.2)), len(comps))
        if k1 == k2:
            return 0.0
        return self.compute_fgw_distance(self.coarsen_pcb(comps, k1), self.coarsen_pcb(comps, k2))

    def board_distance(self, a, b, cache: Dict[tuple, float] | None = None) -> float:
        key = tuple(sorted((a.board_id, b.board_id)))
        if cache is not None and key in cache:
            return cache[key]
        if not self.config.use_fgw or a.ot_repr is None or b.ot_repr is None:
            return float(np.linalg.norm(a.board_features() - b.board_features()))
        dist = self.compute_fgw_distance(a.ot_repr, b.ot_repr)
        blend = float(np.clip(getattr(self.config, "feature_distance_blend", 0.0), 0.0, 1.0))
        if blend > 0:
            feat_dist = float(np.linalg.norm(a.board_features() - b.board_features()))
            dist = (1.0 - blend) * dist + blend * feat_dist
        if cache is not None:
            cache[key] = dist
        return dist

    def similar_boards(self, test_record, train_records: Sequence, cache=None) -> pd.DataFrame:
        best_by_board = {}
        usable_records = [rec for rec in train_records if not rec.is_ng]
        if not usable_records:
            usable_records = list(train_records)
        for rec in usable_records:
            if rec.board_id not in best_by_board or rec.quality.score > best_by_board[rec.board_id].quality.score:
                best_by_board[rec.board_id] = rec
        rows = []
        blend = float(np.clip(getattr(self.config, "feature_distance_blend", 0.0), 0.0, 1.0))
        for rec in best_by_board.values():
            if self.config.use_fgw and test_record.ot_repr is not None and rec.ot_repr is not None and blend > 0:
                fgw_dist = self.compute_fgw_distance(test_record.ot_repr, rec.ot_repr)
                feat_dist = float(np.linalg.norm(test_record.board_features() - rec.board_features()))
                rows.append({"board_id": rec.board_id, "distance": fgw_dist, "fgw_distance": fgw_dist, "feature_distance": feat_dist, "record": rec})
            else:
                dist = self.board_distance(test_record, rec, cache)
                rows.append({"board_id": rec.board_id, "distance": dist, "fgw_distance": np.nan, "feature_distance": np.nan, "record": rec})
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        if self.config.use_fgw and blend > 0 and df["fgw_distance"].notna().any():
            fgw_scale = float(np.nanmedian(df["fgw_distance"]) + 1e-9)
            feat_scale = float(np.nanmedian(df["feature_distance"]) + 1e-9)
            df["distance"] = (
                (1.0 - blend) * df["fgw_distance"] / fgw_scale
                + blend * df["feature_distance"] / feat_scale
            )
        df = df.sort_values("distance").head(self.config.top_k).reset_index(drop=True)
        temp = 0.005 + 0.05 * max(float(df["distance"].median()), 1e-9)
        weights = np.exp(-df["distance"].to_numpy() / temp)
        df["weight"] = weights / (weights.sum() + 1e-9)
        return df

    def infer_process_policy(self, train_records: Sequence) -> dict:
        """Infer active/frozen process dimensions from training boards only."""
        if not train_records:
            return {
                "frozen_mask": np.array([False, False], dtype=bool),
                "mode_params": np.array([0.5, 0.5], dtype=float),
                "mode_share": np.array([0.0, 0.0], dtype=float),
                "std": np.array([1.0, 1.0], dtype=float),
            }
        params = np.vstack([r.params for r in train_records])
        mode_params = []
        mode_share = []
        for dim in range(params.shape[1]):
            rounded = np.round(params[:, dim], 6)
            values, counts = np.unique(rounded, return_counts=True)
            idx = int(np.argmax(counts))
            mode_params.append(float(values[idx]))
            mode_share.append(float(counts[idx] / len(rounded)))
        mode_params = np.asarray(mode_params, dtype=float)
        mode_share = np.asarray(mode_share, dtype=float)
        std = np.std(params, axis=0) + 1e-9
        frozen_mask = mode_share >= self.config.frozen_majority_threshold
        return {
            "frozen_mask": frozen_mask,
            "mode_params": mode_params,
            "mode_share": mode_share,
            "std": std,
        }

    def learned_safe_center(self, test_record, train_records: Sequence) -> np.ndarray:
        """Training-calibrated empirical process center from board geometry."""
        if len(train_records) < 5:
            return np.mean(np.vstack([r.params for r in train_records]), axis=0) if train_records else np.array([0.5, 0.5])
        x_train = np.vstack([r.board_features() for r in train_records])
        y_train = np.vstack([r.params for r in train_records])
        x_mean = x_train.mean(axis=0)
        x_std = x_train.std(axis=0) + 1e-9
        xz = (x_train - x_mean) / x_std
        xt = (np.asarray(test_record.board_features(), dtype=float) - x_mean) / x_std
        x_aug = np.column_stack([np.ones(len(xz)), xz])
        xt_aug = np.concatenate([[1.0], xt])
        alpha = 1.0
        reg = alpha * np.eye(x_aug.shape[1])
        reg[0, 0] = 0.0
        coef = np.linalg.solve(x_aug.T @ x_aug + reg, x_aug.T @ y_train)
        pred = xt_aug @ coef
        return np.clip(pred, 0.0, 1.0)

    @staticmethod
    def _weighted_kde_mode(params: np.ndarray, weights: np.ndarray, bandwidth: float) -> np.ndarray:
        if len(params) <= 1:
            return params[0].copy()
        p_min = params.min(0) - 0.05
        p_max = params.max(0) + 0.05
        axes = [np.linspace(p_min[d], p_max[d], 80 if params.shape[1] == 1 else 30) for d in range(params.shape[1])]
        mesh = np.meshgrid(*axes)
        grid = np.vstack([m.ravel() for m in mesh]).T
        diff = grid[:, None, :] - params[None, :, :]
        sq = np.sum(diff * diff, axis=2)
        scores = np.log(np.sum(weights[None, :] * np.exp(-0.5 * sq / (bandwidth ** 2 + 1e-12)), axis=1) + 1e-12)
        return grid[int(np.argmax(scores))]

    def physics_penalty(self, test_record, params: np.ndarray) -> float:
        if not self.config.use_physics:
            return 0.0
        ar_mean = float(test_record.comps_raw[:, 6].mean())
        ar_norm = np.clip((ar_mean - 1.0) / (5.0 - 1.0 + 1e-9), 0.0, 1.0)
        p_ideal = np.clip(0.9 - self.config.lambda_physics * 0.5 * ar_norm, 0.3, 0.9)
        v_ideal = np.clip(0.4 + self.config.lambda_physics * 0.4 * ar_norm, 0.4, 0.9)
        return float(np.sum(np.square(params - np.array([p_ideal, v_ideal]))))

    def recommend_continuous(self, test_record, train_records: Sequence, cache=None):
        sims = self.similar_boards(test_record, train_records, cache)
        if sims.empty:
            return test_record.params.copy(), {"ood_flag": True, "similar_boards": []}
        params = np.vstack([r.params for r in sims["record"]])
        weights = sims["weight"].to_numpy(dtype=float)
        weights = weights / (weights.sum() + 1e-9)
        process_policy = self.infer_process_policy(train_records)
        frozen_mask = process_policy["frozen_mask"]
        active_mask = ~frozen_mask
        weighted_mean = np.average(params, axis=0, weights=weights)
        rec = weighted_mean.copy()
        kde_mode = weighted_mean.copy()
        if np.any(active_mask) and len(params) > 1 and self.config.use_kde:
            kde_active = self._weighted_kde_mode(
                params[:, active_mask],
                weights,
                bandwidth=self.config.kde_bandwidth,
            )
            kde_mode[active_mask] = kde_active
            gamma = float(np.clip(self.config.kde_mean_hybrid_gamma, 0.0, 1.0))
            rec[active_mask] = (1.0 - gamma) * weighted_mean[active_mask] + gamma * kde_mode[active_mask]
        else:
            rec = weighted_mean.copy()
        if self.config.use_physics and np.any(active_mask):
            safe_center = self.learned_safe_center(test_record, train_records)
            prior_weight = float(np.clip(self.config.learned_prior_weight, 0.0, 1.0))
            rec[active_mask] = (1.0 - prior_weight) * rec[active_mask] + prior_weight * safe_center[active_mask]
        else:
            safe_center = weighted_mean.copy()
        rec[frozen_mask] = process_policy["mode_params"][frozen_mask]
        rec = np.clip(rec, 0.0, 1.0)
        ood = bool(float(sims["distance"].min()) > self.config.reject_distance)
        return rec, {
            "ood_flag": ood,
            "similar_boards": sims[["board_id", "distance", "weight"]].to_dict("records"),
            "process_policy": {
                "frozen_mask": process_policy["frozen_mask"].astype(int).tolist(),
                "mode_params": process_policy["mode_params"].tolist(),
                "mode_share": process_policy["mode_share"].tolist(),
                "std": process_policy["std"].tolist(),
            },
            "weighted_mean": weighted_mean.tolist(),
            "weighted_kde_mode": kde_mode.tolist(),
            "learned_safe_center": safe_center.tolist(),
        }

    def predict_candidate_quality(self, test_record, candidate, train_records: Sequence, cache=None) -> dict:
        sims = self.similar_boards(test_record, train_records, cache)
        if sims.empty:
            return {"volume_error": np.nan, "offset_error": np.nan, "shape_error": np.nan, "ng_risk": 1.0, "score": 0.0}
        rows = []
        for _, row in sims.iterrows():
            source_board = row["board_id"]
            source_trials = [r for r in train_records if r.board_id == source_board]
            if not source_trials:
                continue
            param_d = np.array([np.linalg.norm(candidate.params - r.params) for r in source_trials])
            trial_weights = np.exp(-param_d / (self.config.prediction_bandwidth + 1e-9))
            trial_weights = trial_weights / (trial_weights.sum() + 1e-9)
            q = {
                "volume_error": sum(w * r.quality.volume_error for w, r in zip(trial_weights, source_trials)),
                "offset_error": sum(w * r.quality.offset_error for w, r in zip(trial_weights, source_trials)),
                "shape_error": sum(w * r.quality.shape_error for w, r in zip(trial_weights, source_trials)),
                "ng_risk": sum(w * r.quality.ng_rate for w, r in zip(trial_weights, source_trials)),
                "score": sum(w * r.quality.score for w, r in zip(trial_weights, source_trials)),
                "board_weight": float(row["weight"]),
            }
            rows.append(q)
        if not rows:
            return {"volume_error": np.nan, "offset_error": np.nan, "shape_error": np.nan, "ng_risk": 1.0, "score": 0.0}
        out = {}
        for key in ["volume_error", "offset_error", "shape_error", "ng_risk", "score"]:
            out[key] = float(sum(r[key] * r["board_weight"] for r in rows))
        return out

    def rank_observed_candidates_protocol_a(self, test_record, candidates: Sequence, train_records: Sequence, cache=None) -> pd.DataFrame:
        """Rank true executed candidates while hiding their observed quality during ranking."""
        cont_rec, reason = self.recommend_continuous(test_record, train_records, cache)
        scales = self.quality_scales(train_records)
        rows = []
        for rank_idx, cand in enumerate(candidates):
            pred = self.predict_candidate_quality(test_record, cand, train_records, cache)
            pred_objective = self.normalized_predicted_objective(pred, scales)
            phys = self.physics_penalty(test_record, cand.params)
            dist_to_otma = float(np.linalg.norm(cand.params - cont_rec))
            uncertainty = float(cand.stability + dist_to_otma) if self.config.use_uncertainty else 0.0
            ranking_score = (
                pred_objective
                + 0.5 * uncertainty
                + 2.0 * phys
            )
            rows.append(
                {
                    "experiment_id": cand.experiment_id,
                    "board_id": cand.board_id,
                    "p_norm": cand.params[0],
                    "v_norm": cand.params[1],
                    "press": cand.press_raw,
                    "velocity": cand.velocity_raw,
                    "pred_volume_error": pred["volume_error"],
                    "pred_offset_error": pred["offset_error"],
                    "pred_shape_error": pred["shape_error"],
                    "pred_ng_risk": pred["ng_risk"],
                    "pred_score": pred["score"],
                    "pred_objective": pred_objective,
                    "objective_scale_source": "training_board_zscore",
                    "uncertainty": uncertainty,
                    "physics_penalty": phys,
                    "distance_to_continuous_otma": dist_to_otma,
                    "ranking_score": ranking_score,
                    "ood_flag": reason["ood_flag"],
                    "similar_boards": reason["similar_boards"],
                    "record": cand,
                }
            )
        df = pd.DataFrame(rows).sort_values("ranking_score", ascending=True).reset_index(drop=True)
        df["candidate_rank"] = np.arange(1, len(df) + 1)
        return df
