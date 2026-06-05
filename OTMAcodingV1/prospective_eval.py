"""Prospective and engineer-review data-collection protocols."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROSPECTIVE_COLUMNS = [
    "board_id",
    "physical_board_id",
    "collected_at",
    "recommended_at",
    "recommended_pressure",
    "recommended_velocity",
    "interval_80_low",
    "interval_80_high",
    "manual_review",
    "review_reason",
    "engineer_override_pressure",
    "verified_usable_pressure",
    "first_article_pass",
    "verification_rounds",
    "time_to_usable_minutes",
    "notes",
]

ENGINEER_REVIEW_COLUMNS = [
    "reviewer_id",
    "board_id",
    "card_version",
    "understands_reason",
    "trusts_interval",
    "accepts_recommendation",
    "review_time_seconds",
    "usefulness_score",
    "comment",
]


def write_collection_templates(output_dir: str | Path) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prospective = output_dir / "prospective_validation_template.csv"
    engineer = output_dir / "engineer_review_template.csv"
    pd.DataFrame(columns=PROSPECTIVE_COLUMNS).to_csv(prospective, index=False)
    pd.DataFrame(columns=ENGINEER_REVIEW_COLUMNS).to_csv(engineer, index=False)
    return {"prospective_template": prospective, "engineer_review_template": engineer}


def evaluate_prospective_csv(path: str | Path, output_dir: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = sorted(set(PROSPECTIVE_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Prospective CSV is missing columns: {missing}")
    collected = pd.to_datetime(frame["collected_at"], errors="raise")
    recommended = pd.to_datetime(frame["recommended_at"], errors="raise")
    if (recommended > collected).any():
        raise ValueError("recommended_at must not be later than collected_at.")
    verified = pd.to_numeric(frame["verified_usable_pressure"], errors="coerce")
    recommended_pressure = pd.to_numeric(frame["recommended_pressure"], errors="coerce")
    frame["pressure_abs_error_raw"] = (recommended_pressure - verified).abs()
    frame["interval_80_covered"] = (
        (verified >= pd.to_numeric(frame["interval_80_low"], errors="coerce"))
        & (verified <= pd.to_numeric(frame["interval_80_high"], errors="coerce"))
    )
    summary = pd.DataFrame(
        [
            {
                "n_new_sides": len(frame),
                "first_article_pass_rate": pd.to_numeric(frame["first_article_pass"], errors="coerce").mean(),
                "mean_verification_rounds": pd.to_numeric(frame["verification_rounds"], errors="coerce").mean(),
                "mean_time_to_usable_minutes": pd.to_numeric(frame["time_to_usable_minutes"], errors="coerce").mean(),
                "engineer_override_rate": frame["engineer_override_pressure"].notna().mean(),
                "pressure_mae_raw": frame["pressure_abs_error_raw"].mean(),
                "interval_80_coverage": frame["interval_80_covered"].mean(),
            }
        ]
    )
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_dir / "prospective_validation_cases.csv", index=False)
    summary.to_csv(output_dir / "prospective_validation_summary.csv", index=False)
    return summary


def evaluate_engineer_review_csv(path: str | Path, output_dir: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = sorted(set(ENGINEER_REVIEW_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Engineer-review CSV is missing columns: {missing}")
    summary = pd.DataFrame(
        [
            {
                "n_reviews": len(frame),
                "understands_reason_rate": pd.to_numeric(frame["understands_reason"], errors="coerce").mean(),
                "trusts_interval_rate": pd.to_numeric(frame["trusts_interval"], errors="coerce").mean(),
                "accepts_recommendation_rate": pd.to_numeric(frame["accepts_recommendation"], errors="coerce").mean(),
                "mean_review_time_seconds": pd.to_numeric(frame["review_time_seconds"], errors="coerce").mean(),
                "mean_usefulness_score": pd.to_numeric(frame["usefulness_score"], errors="coerce").mean(),
            }
        ]
    )
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_dir / "engineer_review_cases.csv", index=False)
    summary.to_csv(output_dir / "engineer_review_summary.csv", index=False)
    return summary

