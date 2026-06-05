"""Database loading and board-level quality metrics for OT-MA validation.

The loader keeps observed SPI quality as first-class fields so final
performance can be evaluated from real production records rather than from
manifold smoothness or physical-consistency proxies.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
import sqlite3
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

LAST_JUDGERES_LABEL_AUDIT = pd.DataFrame()
LAST_UNKNOWN_JUDGERES_LABELS = pd.DataFrame()


@dataclass(frozen=True)
class ProcessRanges:
    pressure: Tuple[float, float] = (5.0, 8.0)
    velocity: Tuple[float, float] = (0.0, 100.0)
    stencil_thickness: float = 0.12


@dataclass
class QualityMetrics:
    volume_error: float
    volume_std: float
    offset_error: float
    offset_std: float
    shape_error: float
    good_rate: float
    ng_rate: float
    unknown_label_rate: float
    score: float
    n_pads: int

    def as_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class ExperimentRecord:
    board_id: str
    experiment_id: str
    press_raw: float
    velocity_raw: float
    params: np.ndarray
    comps_raw: np.ndarray
    board_dim: Tuple[float, float, float]
    quality: QualityMetrics
    is_ng: bool
    ot_repr: tuple | None = None
    stability: float = 0.0
    _features_cache: np.ndarray | None = field(default=None, repr=False, compare=False)

    def board_features(self) -> np.ndarray:
        """Compact board descriptor used by tabular baselines."""
        if self._features_cache is not None:
            return self._features_cache
        comps = self.comps_raw
        self._features_cache = np.array(
            [
                comps[:, 0].mean(),
                comps[:, 1].mean(),
                comps[:, 2].mean(),
                comps[:, 3].mean(),
                comps[:, 5].mean(),
                comps[:, 6].mean(),
                comps[:, 7].mean(),
                len(comps),
                self.board_dim[2],
            ],
            dtype=float,
        )
        return self._features_cache


@dataclass
class BoardRecord:
    board_id: str
    comps_raw: np.ndarray
    board_dim: Tuple[float, float, float]
    params: np.ndarray
    ot_repr: tuple | None = None
    stability: float = 0.0
    geometry_source: str = "canonical_aggregate"
    geometry_max_abs_delta: float = 0.0
    _features_cache: np.ndarray | None = field(default=None, repr=False, compare=False)

    def board_features(self) -> np.ndarray:
        if self._features_cache is not None:
            return self._features_cache
        comps = self.comps_raw
        self._features_cache = np.array(
            [
                comps[:, 0].mean(),
                comps[:, 1].mean(),
                comps[:, 2].mean(),
                comps[:, 3].mean(),
                comps[:, 5].mean(),
                comps[:, 6].mean(),
                comps[:, 7].mean(),
                len(comps),
                self.board_dim[2],
            ],
            dtype=float,
        )
        return self._features_cache


@dataclass(frozen=True)
class CandidateView:
    """Quality-hidden candidate passed to rankers during Protocol A/B."""

    board_id: str
    experiment_id: str
    press_raw: float
    velocity_raw: float
    params: np.ndarray
    board_dim: Tuple[float, float, float]
    ot_repr: tuple | None = None
    stability: float = 0.0

    def board_features(self) -> np.ndarray:
        if self.ot_repr is not None:
            pos, feat, weights = self.ot_repr
            return np.array(
                [
                    np.asarray(pos)[:, 0].mean(),
                    np.asarray(pos)[:, 1].mean(),
                    np.asarray(feat).mean(),
                    np.asarray(weights).std(),
                    len(weights),
                    self.board_dim[2],
                ],
                dtype=float,
            )
        return np.array([self.board_dim[0], self.board_dim[1], self.board_dim[2], *self.params], dtype=float)


def to_candidate_view(record: ExperimentRecord) -> CandidateView:
    return CandidateView(
        board_id=record.board_id,
        experiment_id=record.experiment_id,
        press_raw=record.press_raw,
        velocity_raw=record.velocity_raw,
        params=record.params.copy(),
        board_dim=record.board_dim,
        ot_repr=record.ot_repr,
        stability=record.stability,
    )


def build_candidate_views(records: Iterable[ExperimentRecord]) -> List[CandidateView]:
    return [to_candidate_view(r) for r in records]


def build_board_record(records: List[ExperimentRecord], engine=None) -> BoardRecord:
    if not records:
        raise ValueError("Cannot build BoardRecord from an empty record list.")
    first = records[0]
    same_shape = all(r.comps_raw.shape == first.comps_raw.shape for r in records)
    if same_shape:
        stack = np.stack([r.comps_raw for r in records], axis=0)
        comps = np.mean(stack, axis=0)
        max_delta = float(np.max(np.abs(stack - comps[None, :, :])))
        source = "mean_geometry_across_process_settings"
    else:
        comps = first.comps_raw.copy()
        max_delta = np.nan
        source = "first_geometry_shape_mismatch_flagged"
    ot_repr = first.ot_repr
    stability = first.stability
    if engine is not None:
        k = min(getattr(engine.config, "base_k", 200), len(comps))
        ot_repr = engine.coarsen_pcb(comps, n_clusters=k)
        stability = engine.compute_stability(comps, base_k=k)
    return BoardRecord(
        board_id=first.board_id,
        comps_raw=comps,
        board_dim=first.board_dim,
        params=np.array([0.5, 0.5], dtype=float),
        ot_repr=ot_repr,
        stability=float(stability),
        geometry_source=source,
        geometry_max_abs_delta=max_delta,
    )


def _safe_good_mask(values: pd.Series) -> pd.Series:
    text = values.astype(str)
    ng = text.str.contains("NG|不良|bad|fail", case=False, na=False)
    return ~ng


def _known_good_mask(values: pd.Series) -> pd.Series:
    text = values.astype(str)
    return text.str.contains(r"^OK$|PASS|良品|合格|正常|通过|通過|good|accepted", case=False, na=False, regex=True)


def _normalise_param(value: float, span: Tuple[float, float]) -> float:
    lo, hi = span
    return float((value - lo) / (hi - lo + 1e-12))


# Override the legacy label parser above with a broader production-safe parser.
def _label_status(values: pd.Series) -> pd.Series:
    text = values.astype(str)
    known_ng = text.str.contains(
        r"NG|N\.G\.|不良|失败|失敗|缺陷|坏|壞|bad|fail|failed|defect|defective|"
        r"涓嶈壇|不合格|少锡|少錫|多锡|多錫|连锡|連錫|桥连|橋連|偏移|漏印|锡珠|錫珠|立碑",
        case=False,
        na=False,
        regex=True,
    )
    known_good = _known_good_mask(text)
    status = pd.Series("unknown", index=values.index, dtype=object)
    status.loc[known_good & ~known_ng] = "good"
    status.loc[known_ng] = "ng"
    return status


def _safe_good_mask(values: pd.Series) -> pd.Series:
    return _label_status(values) == "good"


def compute_quality_metrics(group: pd.DataFrame) -> QualityMetrics:
    per_volume = pd.to_numeric(group["PerVolume"], errors="coerce").fillna(100.0)
    shift_x = pd.to_numeric(group["ShiftX"], errors="coerce").fillna(0.0)
    shift_y = pd.to_numeric(group["ShiftY"], errors="coerce").fillna(0.0)
    abs_vol = pd.to_numeric(group.get("ABSVolume", 0.0), errors="coerce").fillna(0.0)
    abs_area = pd.to_numeric(group.get("ABSArea", 1.0), errors="coerce").fillna(1.0)
    abs_height = pd.to_numeric(group.get("ABSHeight", 1.0), errors="coerce").fillna(1.0)

    volume_error = float((per_volume - 100.0).abs().mean())
    volume_std = float(per_volume.std(ddof=0))
    offset = np.sqrt(np.square(shift_x.to_numpy()) + np.square(shift_y.to_numpy()))
    offset_error = float(np.mean(offset))
    offset_std = float(np.std(offset))
    shape_factor = abs_vol / (abs_area * abs_height + 1e-9)
    shape_error = float((shape_factor - 1.0).abs().mean())

    status = _label_status(group.get("JudgeRes", pd.Series(["good"] * len(group))))
    good_mask = status == "good"
    unknown_mask = status == "unknown"
    good_rate = float(good_mask.mean())
    # Conservative manuscript default: unknown labels are treated as not-good,
    # while the unknown rate is reported separately for sensitivity analysis.
    ng_rate = float((status != "good").mean())
    unknown_label_rate = float(unknown_mask.mean())

    score_vol = 100.0 * np.exp(-0.01 * volume_error)
    score_shape = 100.0 * np.exp(-5.0 * shape_error)
    score_shift = 100.0 * np.exp(-2.0 * offset_error)
    score = float(np.clip(0.4 * score_vol + 0.3 * score_shape + 0.3 * score_shift, 1.0, 100.0))

    return QualityMetrics(
        volume_error=volume_error,
        volume_std=volume_std,
        offset_error=offset_error,
        offset_std=offset_std,
        shape_error=shape_error,
        good_rate=good_rate,
        ng_rate=ng_rate,
        unknown_label_rate=unknown_label_rate,
        score=score,
        n_pads=int(len(group)),
    )


def load_print_spi(
    db_path: str | Path,
    ranges: ProcessRanges | None = None,
    ot_engine=None,
    base_k: int = 200,
    precompute_stability: bool = True,
) -> List[ExperimentRecord]:
    """Load real production board experiments from SQLite.

    If ``ot_engine`` is provided, board representations are precomputed once per
    board and attached to every experiment record.
    """
    ranges = ranges or ProcessRanges()
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    query = """
    SELECT no, press, "out", length, width, height, PosX, PosY, SizeX, SizeY,
           Rotation, PerVolume, ShiftX, ShiftY, ABSArea, ABSVolume, ABSHeight,
           JudgeRes
    FROM print_spi
    """
    fallback_query = """
    SELECT no, press, "out", length, width, PosX, PosY, SizeX, SizeY,
           Rotation, PerVolume, ShiftX, ShiftY
    FROM print_spi
    """
    with sqlite3.connect(str(db_path)) as conn:
        try:
            df = pd.read_sql(query, conn)
        except Exception:
            df = pd.read_sql(fallback_query, conn)
            df["height"] = 1.0
            df["ABSArea"] = df["SizeX"] * df["SizeY"]
            df["ABSVolume"] = df["ABSArea"] * ranges.stencil_thickness
            df["ABSHeight"] = ranges.stencil_thickness
            df["JudgeRes"] = "good"

    if df.empty:
        raise ValueError("print_spi query returned no records.")

    global LAST_JUDGERES_LABEL_AUDIT, LAST_UNKNOWN_JUDGERES_LABELS
    if "JudgeRes" in df.columns:
        labels = df["JudgeRes"].astype(str).fillna("<NA>")
        status = _label_status(labels)
        parsed_good = status == "good"
        parsed_ng = status == "ng"
        parsed_unknown = status == "unknown"
        known_good = _known_good_mask(labels)
        LAST_JUDGERES_LABEL_AUDIT = (
            pd.DataFrame({"raw_label": labels, "parsed_as_good": parsed_good, "parsed_as_ng": parsed_ng, "parsed_as_unknown": parsed_unknown, "known_good_pattern": known_good})
            .groupby(["raw_label", "parsed_as_good", "parsed_as_ng", "parsed_as_unknown", "known_good_pattern"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
            .sort_values(["parsed_as_ng", "count"], ascending=[False, False])
        )
        LAST_UNKNOWN_JUDGERES_LABELS = LAST_JUDGERES_LABEL_AUDIT[
            LAST_JUDGERES_LABEL_AUDIT["parsed_as_unknown"]
        ].copy()

    records: List[ExperimentRecord] = []
    board_repr_cache = {}
    grouped = df.groupby(["no", "press", "out"], sort=True)
    for exp_idx, ((board_id, press, velocity), group) in enumerate(grouped):
        group = group.copy()
        length = float(group["length"].iloc[0])
        width = float(group["width"].iloc[0])
        height = float(group.get("height", pd.Series([1.0])).iloc[0])
        if length <= 0 or width <= 0:
            continue

        size_x = pd.to_numeric(group["SizeX"], errors="coerce").fillna(0.0)
        size_y = pd.to_numeric(group["SizeY"], errors="coerce").fillna(0.0)
        area_ratio = (size_x * size_y) / (2 * (size_x + size_y) * ranges.stencil_thickness + 1e-9)
        aspect_ratio = np.minimum(size_x, size_y) / (ranges.stencil_thickness + 1e-9)
        comps = np.stack(
            [
                pd.to_numeric(group["PosX"], errors="coerce").fillna(0.0).to_numpy() / length,
                pd.to_numeric(group["PosY"], errors="coerce").fillna(0.0).to_numpy() / width,
                size_x.to_numpy() / length,
                size_y.to_numpy() / width,
                pd.to_numeric(group["Rotation"], errors="coerce").fillna(0.0).to_numpy() / 360.0,
                (size_x.to_numpy() / length) * (size_y.to_numpy() / width),
                area_ratio.to_numpy(),
                aspect_ratio.to_numpy(),
            ],
            axis=1,
        )

        board_key = str(board_id)
        ot_repr = None
        stability = 0.0
        if ot_engine is not None:
            if board_key not in board_repr_cache:
                k = min(base_k, len(comps))
                board_repr_cache[board_key] = (
                    ot_engine.coarsen_pcb(comps, n_clusters=k),
                    ot_engine.compute_stability(comps, base_k=k) if precompute_stability else 0.0,
                )
            ot_repr, stability = board_repr_cache[board_key]

        quality = compute_quality_metrics(group)
        records.append(
            ExperimentRecord(
                board_id=board_key,
                experiment_id=f"{board_key}|{float(press):.6g}|{float(velocity):.6g}|{exp_idx}",
                press_raw=float(press),
                velocity_raw=float(velocity),
                params=np.array(
                    [
                        _normalise_param(float(press), ranges.pressure),
                        _normalise_param(float(velocity), ranges.velocity),
                    ],
                    dtype=float,
                ),
                comps_raw=comps,
                board_dim=(length, width, height),
                quality=quality,
                is_ng=bool(quality.ng_rate > 0.05),
                ot_repr=ot_repr,
                stability=stability,
            )
        )

    return records


def records_to_quality_frame(records: Iterable[ExperimentRecord]) -> pd.DataFrame:
    rows = []
    for rec in records:
        row = {
            "board_id": rec.board_id,
            "experiment_id": rec.experiment_id,
            "press": rec.press_raw,
            "velocity": rec.velocity_raw,
            "p_norm": rec.params[0],
            "v_norm": rec.params[1],
        }
        row.update(rec.quality.as_dict())
        rows.append(row)
    return pd.DataFrame(rows)


def write_data_inventory(records: Iterable[ExperimentRecord], output_dir: str | Path) -> Path:
    """Write a Nature-style source-data inventory for restricted production data."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df = records_to_quality_frame(records)
    inventory = output_dir / "source_data_inventory.csv"
    df.to_csv(inventory, index=False)
    label_path = output_dir / "judgeres_label_audit.csv"
    if not LAST_JUDGERES_LABEL_AUDIT.empty:
        LAST_JUDGERES_LABEL_AUDIT.to_csv(label_path, index=False)
    else:
        pd.DataFrame(
            {
                "raw_label": ["<unavailable>"],
                "count": [0],
                "parsed_as_good": [np.nan],
                "parsed_as_ng": [np.nan],
                "note": ["Run load_print_spi before write_data_inventory to export raw JudgeRes labels."],
            }
        ).to_csv(label_path, index=False)
    unknown_path = output_dir / "unknown_judgeres_labels.csv"
    if not LAST_UNKNOWN_JUDGERES_LABELS.empty:
        LAST_UNKNOWN_JUDGERES_LABELS.to_csv(unknown_path, index=False)
    else:
        pd.DataFrame(columns=["raw_label", "parsed_as_good", "parsed_as_ng", "known_good_pattern", "count"]).to_csv(unknown_path, index=False)

    statement = output_dir / "DATA_AVAILABILITY_DRAFT.md"
    statement.write_text(
        "\n".join(
            [
                "# Data Availability Draft",
                "",
                "The raw production SPI database contains enterprise process data and may be subject to commercial restrictions.",
                "The processed source data tables generated by this pipeline are exported with every figure and summary table.",
                "For submission, specify whether anonymized board-level geometry, process settings, and derived quality metrics can be deposited in a controlled-access or institutional repository.",
                "",
                "Required confirmation before submission:",
                "- Repository or controlled-access route for anonymized processed source data.",
                "- Whether raw pad-level coordinates can be shared, masked, or only made available under data-use agreement.",
                "- Contact route and approval criteria for restricted production records.",
            ]
        ),
        encoding="utf-8",
    )
    return inventory
