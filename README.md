# KOTMA-SR

KOTMA-SR is a case-based decision-support framework for first-article SMT solder-paste printing pressure recommendation under sparse historical production records.

The repository contains the code, current retrospective result package, figure source data, editable figure assets, manuscript drafts, and citation-management files used for the KOTMA-SR study.

## Repository layout

```text
OTMAcodingV1/                      Python implementation and tests
results/current_kotma_sr/           Current KOTMA-SR result package and figures
manuscript/                         Manuscript drafts, review audits, and references
requirements.txt                    Python runtime dependencies
```

## Data boundary

The raw SMT production database is not included because it contains enterprise process records and PCB geometry information. The result package includes exported summaries, figure source data, audits, and manuscript-ready figures generated from the current internal database.

## Reproducing the pipeline

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the experiment pipeline with an authorized local database:

```bash
python -m OTMAcodingV1.run_experiments --db path/to/authorized.db --output results/current_kotma_sr --paper-profile kbs --device auto --fgw-device cpu --run-exploratory-gnn
```

The code records package versions and exports benchmark summaries, calibration summaries, robustness summaries, figure source data, and claim-readiness audits.

## Manuscript materials

The `manuscript/` folder contains the current manuscript draft, review-audit notes, and BibTeX references. The manuscript frames KOTMA-SR as retrospective engineer-supervised decision support, not as autonomous SMT process optimization or external deployment validation.

