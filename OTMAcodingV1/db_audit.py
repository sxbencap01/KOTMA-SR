"""Read-only SQLite audits for manuscript traceability."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import closing
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


OUTCOME_ONLY_FIELDS = {
    "judgeres",
    "defecttype",
    "perarea",
    "pervolume",
    "shiftx",
    "shifty",
    "absarea",
    "absvolume",
    "absheight",
}
IDENTIFIER_ONLY_FIELDS = {"index", "id", "pcbid", "padid"}
CONTEXT_CANDIDATE_FIELDS = {"partnumber", "density", "shapeid", "jobname", "speed"}


@dataclass(frozen=True)
class DatabaseAudit:
    schema: pd.DataFrame
    coverage: pd.DataFrame
    joins: pd.DataFrame
    board_consistency: pd.DataFrame
    eligibility: pd.DataFrame


def _write_audit(audit: DatabaseAudit, output_dir: str | Path | None) -> DatabaseAudit:
    if output_dir is None:
        return audit
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit.schema.to_csv(out / "database_schema_audit.csv", index=False)
    audit.coverage.to_csv(out / "field_coverage_audit.csv", index=False)
    audit.joins.to_csv(out / "join_coverage_audit.csv", index=False)
    audit.board_consistency.to_csv(out / "board_level_consistency_audit.csv", index=False)
    audit.eligibility.to_csv(out / "feature_eligibility_audit.csv", index=False)
    return audit


def audit_database_fast(db_path: str | Path, output_dir: str | Path | None = None) -> DatabaseAudit:
    """Fast manuscript audit: all schemas plus one-pass coverage for print_spi."""
    db_path = Path(db_path)
    schema_rows: list[dict] = []
    coverage_rows: list[dict] = []
    with closing(sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)) as conn:
        tables = _table_names(conn)
        print_columns: list[str] = []
        for table in tables:
            info = conn.execute(f"PRAGMA table_info({_quoted(table)})").fetchall()
            for row in info:
                column = str(row[1])
                schema_rows.append(
                    {
                        "table": table,
                        "column": column,
                        "sqlite_type": str(row[2]),
                        "not_null_declared": int(row[3]),
                        "primary_key": int(row[5]),
                        "role": _column_role(column),
                    }
                )
                if table == "print_spi":
                    print_columns.append(column)
        if print_columns:
            parts = ["COUNT(*) AS __rows"]
            for column in print_columns:
                parts.append(f"COUNT({_quoted(column)}) AS {_quoted('__nonnull__' + column)}")
            cursor = conn.execute(f"SELECT {', '.join(parts)} FROM print_spi")
            values = cursor.fetchone()
            value_map = dict(zip([item[0] for item in cursor.description], values))
            n_rows = int(value_map["__rows"])
            for column in print_columns:
                non_null = int(value_map["__nonnull__" + column])
                coverage_rows.append(
                    {
                        "table": "print_spi",
                        "column": column,
                        "rows": n_rows,
                        "non_null_rows": non_null,
                        "coverage": float(non_null / n_rows) if n_rows else np.nan,
                        "distinct_values": np.nan,
                        "distinct_status": "deferred_full_audit",
                        "role": _column_role(column),
                    }
                )
    schema = pd.DataFrame(schema_rows)
    coverage = pd.DataFrame(coverage_rows)
    eligibility = coverage.copy()
    if not eligibility.empty:
        eligibility["eligible_as_model_input"] = (
            eligibility["role"].isin(["pre_print_candidate", "context_candidate"])
            & (eligibility["coverage"].fillna(0.0) >= 0.90)
        ).astype(int)
        eligibility["decision"] = np.where(
            eligibility["role"].eq("outcome_only"),
            "descriptive_only",
            np.where(
                eligibility["role"].eq("identifier_only"),
                "join_or_aggregate_only",
                np.where(eligibility["eligible_as_model_input"].eq(1), "candidate_after_semantic_review", "exclude_low_coverage"),
            ),
        )
    return _write_audit(
        DatabaseAudit(schema, coverage, pd.DataFrame(), pd.DataFrame(), eligibility),
        output_dir,
    )


def _table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return [str(row[0]) for row in rows if not str(row[0]).startswith("sqlite_")]


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _column_role(column: str) -> str:
    key = column.lower()
    if key in OUTCOME_ONLY_FIELDS:
        return "outcome_only"
    if key in IDENTIFIER_ONLY_FIELDS:
        return "identifier_only"
    if key in CONTEXT_CANDIDATE_FIELDS:
        return "context_candidate"
    return "pre_print_candidate"


def audit_database(db_path: str | Path, output_dir: str | Path | None = None) -> DatabaseAudit:
    """Audit all SQLite tables without modifying the enterprise database."""
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    schema_rows: list[dict] = []
    coverage_rows: list[dict] = []
    consistency_rows: list[dict] = []
    join_rows: list[dict] = []
    with closing(sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)) as conn:
        tables = _table_names(conn)
        columns_by_table: dict[str, set[str]] = {}
        for table in tables:
            info = conn.execute(f"PRAGMA table_info({_quoted(table)})").fetchall()
            columns = [str(row[1]) for row in info]
            columns_by_table[table] = set(columns)
            n_rows = int(conn.execute(f"SELECT COUNT(*) FROM {_quoted(table)}").fetchone()[0])
            aggregate_parts = ["COUNT(*) AS __rows"]
            for row in info:
                column = str(row[1])
                qcol = _quoted(column)
                aggregate_parts.append(f"COUNT({qcol}) AS {_quoted('__nonnull__' + column)}")
                if n_rows <= 250000 or column.lower() in CONTEXT_CANDIDATE_FIELDS | IDENTIFIER_ONLY_FIELDS | {"no", "press", "out"}:
                    aggregate_parts.append(f"COUNT(DISTINCT {qcol}) AS {_quoted('__distinct__' + column)}")
            aggregate_sql = f"SELECT {', '.join(aggregate_parts)} FROM {_quoted(table)}"
            cursor = conn.execute(aggregate_sql)
            aggregates = cursor.fetchone()
            aggregate_names = [item[0] for item in cursor.description]
            aggregate_map = dict(zip(aggregate_names, aggregates))
            for row in info:
                column = str(row[1])
                schema_rows.append(
                    {
                        "table": table,
                        "column": column,
                        "sqlite_type": str(row[2]),
                        "not_null_declared": int(row[3]),
                        "primary_key": int(row[5]),
                        "role": _column_role(column),
                    }
                )
                non_null = int(aggregate_map["__nonnull__" + column])
                distinct_value = aggregate_map.get("__distinct__" + column)
                distinct = int(distinct_value) if distinct_value is not None else np.nan
                coverage_rows.append(
                    {
                        "table": table,
                        "column": column,
                        "rows": n_rows,
                        "non_null_rows": non_null,
                        "coverage": float(non_null / n_rows) if n_rows else np.nan,
                        "distinct_values": distinct,
                        "distinct_status": "computed" if np.isfinite(distinct) else "skipped_large_table",
                        "role": _column_role(column),
                    }
                )

        if "print_spi" in columns_by_table and "no" in columns_by_table["print_spi"]:
            cols = columns_by_table["print_spi"]
            for column in sorted(cols):
                if column.lower() not in CONTEXT_CANDIDATE_FIELDS:
                    continue
                qcol = _quoted(column)
                frame = pd.read_sql_query(
                    f"""
                    SELECT no AS board_id,
                           COUNT(*) AS n_rows,
                           COUNT({qcol}) AS non_null_rows,
                           COUNT(DISTINCT {qcol}) AS distinct_values
                    FROM print_spi
                    GROUP BY no
                    """,
                    conn,
                )
                for _, row in frame.iterrows():
                    consistency_rows.append(
                        {
                            "table": "print_spi",
                            "column": column,
                            "board_id": str(row["board_id"]),
                            "n_rows": int(row["n_rows"]),
                            "non_null_rows": int(row["non_null_rows"]),
                            "distinct_values": int(row["distinct_values"]),
                            "board_constant": int(row["distinct_values"] <= 1),
                        }
                    )

        base = columns_by_table.get("print_spi", set())
        for table, columns in columns_by_table.items():
            if table == "print_spi":
                continue
            candidate_pairs = []
            if "no" in base and "no" in columns:
                candidate_pairs.append(("no", "no"))
            if "PCBID" in base and "PCBID" in columns:
                candidate_pairs.append(("PCBID", "PCBID"))
            if "no" in base and "no_id" in columns:
                candidate_pairs.append(("no", "no_id"))
            for left, right in candidate_pairs:
                matched = int(
                    conn.execute(
                        f"""
                        SELECT COUNT(DISTINCT p.{_quoted(left)})
                        FROM print_spi p
                        INNER JOIN {_quoted(table)} t
                          ON CAST(p.{_quoted(left)} AS TEXT) = CAST(t.{_quoted(right)} AS TEXT)
                        """
                    ).fetchone()[0]
                )
                total = int(
                    conn.execute(
                        f"SELECT COUNT(DISTINCT {_quoted(left)}) FROM print_spi WHERE {_quoted(left)} IS NOT NULL"
                    ).fetchone()[0]
                )
                join_rows.append(
                    {
                        "left_table": "print_spi",
                        "left_key": left,
                        "right_table": table,
                        "right_key": right,
                        "matched_left_keys": matched,
                        "total_left_keys": total,
                        "join_coverage": float(matched / total) if total else np.nan,
                    }
                )

    schema = pd.DataFrame(schema_rows)
    coverage = pd.DataFrame(coverage_rows)
    joins = pd.DataFrame(join_rows)
    consistency = pd.DataFrame(consistency_rows)
    eligibility = coverage.copy()
    if not eligibility.empty:
        eligibility["eligible_as_model_input"] = (
            eligibility["role"].isin(["pre_print_candidate", "context_candidate"])
            & (eligibility["coverage"].fillna(0.0) >= 0.90)
        ).astype(int)
        eligibility["decision"] = np.where(
            eligibility["role"].eq("outcome_only"),
            "descriptive_only",
            np.where(
                eligibility["role"].eq("identifier_only"),
                "join_or_aggregate_only",
                np.where(eligibility["eligible_as_model_input"].eq(1), "candidate_after_semantic_review", "exclude_low_coverage"),
            ),
        )
    audit = DatabaseAudit(schema, coverage, joins, consistency, eligibility)
    return _write_audit(audit, output_dir)
