"""Generate one traceable retrospective recommendation card."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .data_loader import load_print_spi
    from .otma_engine import OTMAConfig, OTMAEngine
    from .trusted_recommender import TrustedConfig, TrustedRecommender
    from .v1_evaluation import calibrate_profile
except ImportError:
    from data_loader import load_print_spi
    from otma_engine import OTMAConfig, OTMAEngine
    from trusted_recommender import TrustedConfig, TrustedRecommender
    from v1_evaluation import calibrate_profile


def parse_args():
    parser = argparse.ArgumentParser(description="Write a traceable first-article recommendation card.")
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--db", default=str(root / "test.db"))
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--output", default="recommendation_card.json")
    parser.add_argument("--base-k", type=int, default=80)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--fgw-device", choices=["auto", "cpu", "cuda"], default="cpu")
    parser.add_argument("--velocity-override", type=float, default=None, help="Optional engineer-approved velocity override.")
    return parser.parse_args()


def main():
    args = parse_args()
    engine = OTMAEngine(OTMAConfig(base_k=args.base_k, require_pot=True, compute_device=args.device, fgw_device=args.fgw_device))
    records = load_print_spi(args.db, ot_engine=engine, base_k=args.base_k, precompute_stability=False)
    cases = {}
    for record in records:
        cases.setdefault(record.board_id, record)
    board_id = str(args.board_id)
    if board_id not in cases:
        raise KeyError(f"Board not found in the retrospective database: {board_id}")
    train = [record for key, record in cases.items() if key != board_id]
    config = TrustedConfig(
        top_k=8,
        descriptor_weight=0.5,
        prior_weight=0.0,
        use_fgw=True,
        use_prior=False,
        sparse_tail_shrink=True,
    )
    calibration = calibrate_profile(engine, train, config)
    trace = TrustedRecommender(engine, config).recommend(cases[board_id], train, calibration)
    if args.velocity_override is not None:
        if not 0.0 <= args.velocity_override <= 100.0:
            raise ValueError("--velocity-override must be within [0, 100].")
        trace.recommended_velocity_raw = float(args.velocity_override)
        trace.recommended_velocity_norm = float(args.velocity_override / 100.0)
        trace.fired_rules.append("engineer_velocity_override")
    Path(args.output).write_text(json.dumps(trace.as_dict(), indent=2), encoding="utf-8")
    print(Path(args.output).resolve())


if __name__ == "__main__":
    main()

