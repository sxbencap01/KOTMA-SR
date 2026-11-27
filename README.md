# KOTMA-SR: Decision-Stage Attribution and Leakage-Controlled Case-Based Squeegee Pressure Recommendation

Official core code, anonymized derived results, and 8-board synthetic end-to-end smoke test for the manuscript:

> **Decision-Stage Attribution and Leakage-Controlled Case-Based Squeegee Pressure Recommendation from Historical Solder-Paste Printing Records**  
> Xin Su, Yichen Liu (*Engineering Applications of Artificial Intelligence*, Manuscript `EAAI-26-17496`)

---

## 1. Quick Verification (No Proprietary Data Required)

Run the one-command end-to-end smoke test on the bundled **8-board (`12`-side) synthetic pad-level dataset**:

```bash
pip install -r requirements.txt
python smoke_test.py
```

`smoke_test.py` executes the exact core pipeline end to end:
1. Single-board unique-pad deduplication (`code/prepare.py`)
2. 12-D descriptor extraction, $M \le 80$ `MiniBatchKMeans` super-node coarsening, and `POT` entropic FGW matching (`code/geometry.py`)
3. Physical-board grouped nested leave-one-board-out (LOBO) cross-validation with the rare-setting frequency gate ($s_i < 3$), bounded adjustment cap, `0.1 kgf` grid projection, and Layer 2 empirical residual calibration (`code/evaluate.py`)
4. Matched tabular ML baselines (`CatBoost`, `ExtraTrees`, `Weighted kNN`, `code/benchmark.py`)
5. New-board CLI recommendation card generation (`code/recommend.py`)
6. Pre-print CAD vs. observed SPI equivalence and outer-fold replay (`audit/compare_preprint.py`)

---

## 2. Repository Structure (Core Release Only)

```text
KOTMA-SR/
├── smoke_test.py                       # One-command 8-board synthetic end-to-end verification
├── config.json                         # Confirmed primary t = 0.15 mm specification (defaults to synthetic demo DB)
├── config_t012_sensitivity.json        # Stencil thickness t = 0.12 mm sensitivity specification
├── requirements.txt                    # Python dependencies (numpy, pandas, scipy, scikit-learn, POT, catboost)
├── code/                               # Core algorithmic & leakage-controlled evaluation modules
│   ├── common.py                       # Config, SHA-256, and deterministic single-thread defaults
│   ├── prepare.py                      # Read-only SQLite audit & single-board unique-pad deduplication
│   ├── primitives.py                   # 12-D board descriptors, GeometryEngine (M<=80), similarity weights
│   ├── geometry.py                     # POT entropic FGW computation & convergence verification
│   ├── evaluate.py                     # Physical-board grouped nested LOBO CV, gating, Layer 2 intervals
│   ├── benchmark.py                    # CatBoost, ExtraTrees, Weighted kNN baselines (identical folds)
│   ├── independent_controls.py         # Matched decision-stage attribution controls
│   ├── learning.py                     # Sample-efficiency sub-library tuning helper
│   └── recommend.py                    # Research CLI recommendation card generator
├── audit/
│   ├── compare_preprint.py             # Pre-print CAD vs. SPI equivalence & frozen-fold decision replay
│   └── preprint_manifest.example.json  # Evidence manifest template
├── data/
│   ├── anonymized_two_board_samples.csv # Two strictly anonymized board-level derived examples (Table S10)
│   └── synthetic_demo_8boards/         # 8-board (12-side) synthetic SQLite DB, CSV, & pre-print CAD export
├── results_t015_primary/               # Anonymized derived evaluation tables (t = 0.15 mm primary benchmark)
├── results_t012_sensitivity/           # Anonymized derived sensitivity summary (t = 0.12 mm)
└── figures/                            # Publication-ready PNG previews (Figures 1–11 & S1)
```

---

## 3. Summary of Verified Primary Results (`t = 0.15 mm`, 21 Physical Boards / 34 PCB Sides)

All results are computed under strict **physical-board grouped nested LOBO cross-validation** after deduplicating `1,734,749` multi-run SPI rows (`1,066` board runs) into `54,661` unique single-board pads. Run-to-run variance auditing across all `54,564` multi-run `(side, PadID)` pairs confirms **exact `0.000000` variation** in `SizeX`, `SizeY`, `PosX`, `PosY`, and `Rotation` on `100.0%` (`33/33`) of single-revision sides (static nominal Gerber geometry), whereas post-print measured deposit columns (`ABSArea`, `PerArea`) vary on `100.0%` of pads.

| Method | Primary MAE (`34` sides, kgf) | Board-Equal MAE (`21` boards, kgf) | Qualified Cohort MAE (`23` sides / `15` boards, kgf) | Sensitivity `t = 0.12 mm` Primary MAE (kgf) |
| :--- | :---: | :---: | :---: | :---: |
| **CatBoost** (unconstrained tabular upper bound) | **0.2588** | **0.2643** | **0.3391** | **0.2588** |
| ExtraTrees | 0.2912 | 0.2786 | 0.3522 | 0.2971 |
| Median (constant LOO baseline) | 0.3059 | 0.3238 | 0.5565 | 0.3059 |
| Ridge | 0.3118 | 0.3238 | 0.3826 | 0.3088 |
| **Full (KOTMA-SR)** | **0.3265** | **0.3190** | **0.4261** | **0.3265** |
| Gated CatBoost (same rare-setting gate) | 0.3265 | 0.3190 | 0.4261 | — |
| LOO Mean (constant mean baseline) | 0.3294 | 0.3286 | 0.4217 | — |
| Gated descriptor (matched attribution control) | 0.3294 | 0.3238 | 0.4304 | 0.3265 |
| Gated Ridge (same rare-setting gate) | 0.3294 | 0.3214 | 0.4261 | — |
| Shuffled cost (20 seeds, mean ± SD; $p = 0.0952$) | 0.3316 ± 0.0030 | — | — | — |
| Gated median (matched attribution control) | 0.3324 | 0.3262 | 0.4261 | 0.3324 |
| Gated Weighted kNN (same rare-setting gate) | 0.3324 | 0.3262 | 0.4348 | — |
| **CBR** (nearest-neighbor anchor) | 0.3529 | 0.3571 | 0.4783 | 0.3529 |

- **Primary paired gain (`CBR - Full`)**: `+0.0265 kgf` (`-7.5%`), 95% physical-board cluster CI `[0.0000, 0.0625]`, net positive on `3/3` active physical boards (`B07`, `B18`, `B19`).
- **Qualified cohort paired gain (`CBR - Full`)**: `+0.0522 kgf` (`-10.9%`), 95% physical-board cluster CI **`[0.0083, 0.1100]`** (strictly excluding zero), net positive on `4/4` active physical boards (exact sign-flip $p = 0.125$).
- **Decision-stage attribution**: FGW modifies continuous candidates on `33/34` sides (`mean 0.0743 kgf`), yet the rare-setting frequency gate ($s_i < 3$), bounded cap, and `0.1 kgf` grid compress executable differences to `1/34` side (`S33`). Relaxing the gate threshold to $s_i < 6$ lowers `Full` primary MAE to `0.2765 kgf`.

---

## 4. Data Privacy & Industrial Confidentiality

In compliance with industrial non-disclosure agreements, raw proprietary customer PCB pad layouts, enterprise part identifiers, and the source SQLite database (`test.db`) are **strictly excluded** from this repository. Only core algorithmic code, anonymized derived summary tables, two strictly anonymized board-level derived examples (`data/anonymized_two_board_samples.csv`), and the self-contained 8-board synthetic demonstration dataset (`data/synthetic_demo_8boards/`) are published.
