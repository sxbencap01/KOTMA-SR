"""Shared configuration, deterministic single-thread defaults, and path helpers."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import os
import sys

ROOT = Path(os.environ.get("KOTMA_ROOT", Path(__file__).resolve().parents[1]))
CONFIG_PATH = Path(os.environ.get("KOTMA_CONFIG", ROOT / "config.json"))
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
DB = Path(os.environ.get("KOTMA_DB", (ROOT / CONFIG["database"]).resolve()))
if not 0 < float(CONFIG["stencil_thickness_assumed"]) < float("inf"):
    raise ValueError("The assumed stencil thickness must be finite and positive.")
OUT = Path(os.environ.get("KOTMA_OUT", ROOT / "results"))
OUT.mkdir(parents=True, exist_ok=True)
sys.dont_write_bytecode = True
for name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ[name] = "1"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(name: str, obj: dict) -> None:
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
