"""Geometry primitives retained from the project implementation."""
from __future__ import annotations
import numpy as np
from sklearn.cluster import MiniBatchKMeans

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

class GeometryEngine:
    def __init__(self, base_k=80):
        from types import SimpleNamespace
        self.config = SimpleNamespace(base_k=base_k)
        self.feat_weights = {"pos": .1, "area": .4, "ar": 1., "aspect": .5, "height": .5}

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
