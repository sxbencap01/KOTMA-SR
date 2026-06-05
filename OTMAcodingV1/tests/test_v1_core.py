from __future__ import annotations

from pathlib import Path
from contextlib import closing
import gc
import sqlite3
import tempfile
import time
import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

from OTMAcodingV1.baseline_suite import executable_pressure
from OTMAcodingV1.db_audit import audit_database
from OTMAcodingV1.prospective_eval import PROSPECTIVE_COLUMNS, evaluate_prospective_csv
from OTMAcodingV1.trusted_recommender import CalibrationProfile, TrustedConfig, TrustedRecommender, stable_similarity_weights
from OTMAcodingV1.validation_protocols import assert_no_physical_board_leakage, make_folds, physical_board_id


def _record(board_id: str, pressure_norm: float, shift: float = 0.0):
    comps = np.array(
        [
            [0.1 + shift, 0.1, 0.01, 0.02, 0.0, 0.001, 1.0, 2.0],
            [0.5 + shift, 0.5, 0.02, 0.01, 0.0, 0.001, 1.2, 1.5],
            [0.8 + shift, 0.7, 0.01, 0.01, 0.0, 0.001, 0.9, 1.0],
        ],
        dtype=float,
    )
    return SimpleNamespace(
        board_id=board_id,
        params=np.array([pressure_norm, 0.008], dtype=float),
        press_raw=5.0 + 3.0 * pressure_norm,
        velocity_raw=0.8,
        comps_raw=comps,
        board_dim=(100.0, 80.0, 1.6),
        ot_repr=(comps[:, :2], comps[:, 2:], np.full(len(comps), 1.0 / len(comps))),
    )


class _FakeEngine:
    def compute_fgw_distance(self, left, right):
        return float(np.linalg.norm(np.mean(left[0], axis=0) - np.mean(right[0], axis=0)))


class StableWeightsTests(unittest.TestCase):
    def test_large_distances_are_normalized(self):
        weights = stable_similarity_weights(np.array([100000.0, 120000.0, 180000.0]))
        self.assertTrue(np.all(np.isfinite(weights)))
        self.assertAlmostEqual(float(weights.sum()), 1.0)
        self.assertGreater(weights[0], weights[1])


class AuditTests(unittest.TestCase):
    def test_database_audit_marks_outcomes_descriptive_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "audit.db"
            with closing(sqlite3.connect(db)) as conn:
                conn.execute("CREATE TABLE print_spi (no TEXT, press REAL, JudgeRes TEXT, partNumber REAL)")
                conn.execute("INSERT INTO print_spi VALUES ('A', 6.0, 'OK', 1)")
                conn.commit()
            audit = audit_database(db)
            row = audit.eligibility[(audit.eligibility["table"] == "print_spi") & (audit.eligibility["column"] == "JudgeRes")].iloc[0]
            self.assertEqual(row["decision"], "descriptive_only")
            gc.collect()
            time.sleep(0.05)


class TrustedReasonerTests(unittest.TestCase):
    def test_trace_recomputes_pressure_fusion(self):
        train = [_record("A", 0.3), _record("B", 0.5, 0.02), _record("C", 0.7, 0.04)]
        held = _record("T", 0.6, 0.03)
        config = TrustedConfig(top_k=3, descriptor_weight=1.0, prior_weight=0.4, use_fgw=False, use_prior=True)
        trace = TrustedRecommender(_FakeEngine(), config).recommend(held, train, CalibrationProfile())
        fused = trace.retrieval_contribution * trace.retrieval_pressure_raw + trace.prior_contribution * trace.prior_pressure_raw
        self.assertAlmostEqual(trace.recommended_pressure_raw, fused, places=7)
        self.assertEqual(trace.board_id, "T")

    def test_low_neighbor_support_requests_review(self):
        train = [_record("A", 0.4)]
        held = _record("T", 0.6, 0.03)
        config = TrustedConfig(top_k=1, descriptor_weight=1.0, prior_weight=0.0, use_fgw=False, use_prior=False)
        trace = TrustedRecommender(_FakeEngine(), config).recommend(held, train, CalibrationProfile())
        self.assertTrue(trace.manual_review)
        self.assertIn("low_neighbor_support", trace.review_reasons)

    def test_sparse_tail_shrink_preserves_supported_cbr(self):
        train = [_record("A", 0.5), _record("B", 0.5, 0.02), _record("C", 0.5, 0.04), _record("D", 0.8, 0.08)]
        held = _record("T", 0.6, 0.01)
        config = TrustedConfig(
            top_k=3,
            descriptor_weight=1.0,
            prior_weight=0.0,
            use_fgw=False,
            use_prior=False,
            sparse_tail_shrink=True,
        )
        trace = TrustedRecommender(_FakeEngine(), config).recommend(held, train, CalibrationProfile())
        self.assertEqual(trace.safety_action, "descriptor_cbr_safeguard")
        self.assertAlmostEqual(trace.recommended_pressure_raw, trace.descriptor_cbr_pressure_raw)

    def test_sparse_tail_shrink_bounds_sparse_tail_adjustment(self):
        train = [_record("A", 0.25), _record("B", 0.5, 0.02), _record("C", 0.5, 0.04), _record("D", 0.5, 0.08)]
        held = _record("T", 0.6, 0.001)
        config = TrustedConfig(
            top_k=4,
            descriptor_weight=1.0,
            prior_weight=0.0,
            use_fgw=False,
            use_prior=False,
            sparse_tail_shrink=True,
            max_tail_adjustment_raw=0.2,
        )
        trace = TrustedRecommender(_FakeEngine(), config).recommend(held, train, CalibrationProfile())
        self.assertEqual(trace.safety_action, "bounded_structural_tail_correction")
        self.assertLessEqual(abs(trace.recommended_pressure_raw - trace.descriptor_cbr_pressure_raw), 0.2 + 1e-9)


class GroupedProtocolTests(unittest.TestCase):
    def test_ab_sides_are_held_out_together(self):
        records = [_record("PCB-001-A", 0.3), _record("PCB-001-B", 0.4), _record("PCB-002-A", 0.5)]
        folds = make_folds(records, "pcb_group_lobo")
        assert_no_physical_board_leakage(folds)
        first = next(fold for fold in folds if fold.fold_id == "PCB-001")
        self.assertEqual({record.board_id for record in first.test_cases}, {"PCB-001-A", "PCB-001-B"})

    def test_prefix_is_anonymous(self):
        self.assertEqual(physical_board_id("AD5.948.01145-A"), "AD5.948.01145")
        self.assertEqual(physical_board_id("ANYTHING.ELSE.01145-B"), "ANYTHING.ELSE.01145")

    def test_executable_pressure_uses_point_one_grid(self):
        self.assertAlmostEqual(executable_pressure(5.14), 5.1)
        self.assertAlmostEqual(executable_pressure(7.96), 8.0)
        self.assertAlmostEqual(executable_pressure(4.8), 5.0)


class ProspectiveProtocolTests(unittest.TestCase):
    def test_future_recommendation_timestamp_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prospective.csv"
            row = {column: "" for column in PROSPECTIVE_COLUMNS}
            row.update(
                {
                    "board_id": "PCB-001-A",
                    "physical_board_id": "PCB-001",
                    "recommended_at": "2026-06-03",
                    "collected_at": "2026-06-02",
                }
            )
            pd.DataFrame([row]).to_csv(path, index=False)
            with self.assertRaises(ValueError):
                evaluate_prospective_csv(path, tmp)


if __name__ == "__main__":
    unittest.main()

