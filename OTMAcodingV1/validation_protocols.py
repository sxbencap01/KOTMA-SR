"""Leakage-safe validation folds for anonymous PCB-side identifiers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Iterable, Sequence

import pandas as pd


_SIDE_SUFFIX = re.compile(r"-(A|B)$", flags=re.IGNORECASE)


def physical_board_id(board_id: str) -> str:
    """Return the physical PCB id while treating every other id segment as anonymous."""
    return _SIDE_SUFFIX.sub("", str(board_id))


def unique_side_cases(records: Iterable) -> list:
    cases = {}
    for record in records:
        cases.setdefault(str(record.board_id), record)
    return [cases[key] for key in sorted(cases)]


def group_id(record, protocol: str) -> str:
    board_id = str(record.board_id)
    if protocol == "side_lobo":
        return board_id
    if protocol == "pcb_group_lobo":
        return physical_board_id(board_id)
    raise ValueError(f"Unknown validation protocol: {protocol}")


@dataclass(frozen=True)
class ValidationFold:
    protocol: str
    fold_id: str
    train_cases: tuple
    test_cases: tuple

    def as_rows(self) -> list[dict]:
        rows = []
        for role, cases in [("train", self.train_cases), ("test", self.test_cases)]:
            for case in cases:
                rows.append(
                    {
                        "protocol": self.protocol,
                        "fold_id": self.fold_id,
                        "role": role,
                        "board_id": str(case.board_id),
                        "physical_board_id": physical_board_id(str(case.board_id)),
                    }
                )
        return rows


def make_folds(records: Sequence, protocol: str = "pcb_group_lobo", max_folds: int | None = None) -> list[ValidationFold]:
    cases = unique_side_cases(records)
    grouped: dict[str, list] = {}
    for case in cases:
        grouped.setdefault(group_id(case, protocol), []).append(case)
    fold_ids = sorted(grouped)
    if max_folds is not None:
        fold_ids = fold_ids[:max_folds]
    folds = []
    for fold_id in fold_ids:
        test_ids = {str(case.board_id) for case in grouped[fold_id]}
        folds.append(
            ValidationFold(
                protocol=protocol,
                fold_id=fold_id,
                train_cases=tuple(case for case in cases if str(case.board_id) not in test_ids),
                test_cases=tuple(grouped[fold_id]),
            )
        )
    return folds


def inner_folds(train_cases: Sequence, protocol: str) -> list[ValidationFold]:
    return make_folds(train_cases, protocol=protocol)


def write_fold_manifest(folds: Sequence[ValidationFold], output_path) -> pd.DataFrame:
    rows = []
    for fold in folds:
        rows.extend(fold.as_rows())
    frame = pd.DataFrame(rows)
    frame.to_csv(output_path, index=False)
    return frame


def assert_no_physical_board_leakage(folds: Sequence[ValidationFold]) -> None:
    for fold in folds:
        train = {physical_board_id(str(case.board_id)) for case in fold.train_cases}
        test = {physical_board_id(str(case.board_id)) for case in fold.test_cases}
        overlap = train & test
        if overlap:
            raise AssertionError(f"Physical-board leakage in fold {fold.fold_id}: {sorted(overlap)}")


def anonymous_board_number_map(records: Sequence) -> dict[str, int]:
    """Stable display-only mapping; never use the numeric aliases as model features."""
    ids = sorted({physical_board_id(str(record.board_id)) for record in records})
    return {board_id: index + 1 for index, board_id in enumerate(ids)}

