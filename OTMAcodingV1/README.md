# KOTMA-SR

Leakage-safe retrospective evaluation for trustworthy first-article solder-paste
printing pressure recommendation under sparse production histories.

KOTMA-SR keeps descriptor CBR as an auditable safeguard. FGW graph reasoning is
used only as a bounded correction when the nearest historical pressure lies in
a fold-local sparsely supported tail. Executable pressure recommendations are
rounded to a 0.1 grid. Velocity remains a training-fold empirical policy.

## Claim boundary

This package evaluates recovery of historically executed pressure settings. It
does not prove quality optimization, defect reduction, autonomous control, or a
globally optimal process setting.

The manuscript-ready claim is deliberately narrower: KOTMA-SR improves the
primary pressure-recovery MAE endpoint against descriptor CBR while exposing
intervals, review triggers, and engineering trade-offs. Do not claim superiority
on every secondary metric. Independent temporal or external-site validation and
an engineer-supervised first-article verification study remain required before a
strong deployment claim.

## Manuscript profiles

- `kbs`: knowledge representation, traceable case reasoning, confidence
  calibration, selective review, explanation fidelity, and robustness.
- `jms`: high-mix low-volume aerospace SMT workflow, recommendation cards,
  engineering usability, human review, latency, and deployment boundaries.
- `both`: generate both manuscript figure packages from the same validation run.

## Existing environment

```powershell
$PY = 'D:\ProgramData\Anaconda3\envs\pytorch\python.exe'
& $PY -c "import numpy, pandas, scipy, sklearn, matplotlib, seaborn, ot, torch; print('environment-ok')"
```

## Smoke run

```powershell
& $PY -m OTMAcodingV1.run_experiments `
  --db .\test.db `
  --output .\OTMA_V1_Smoke `
  --paper-profile both `
  --device auto `
  --fgw-device cpu `
  --smoke
```

Smoke outputs validate the pipeline only. They must not be reported as manuscript
results.

## Complete manuscript run

```powershell
& $PY -m OTMAcodingV1.run_experiments `
  --db .\test.db `
  --output .\OTMA_V1_Results `
  --paper-profile both `
  --device auto `
  --fgw-device cpu `
  --strict-nested-lobo
```

The run writes:

- `shared/primary_endpoint_statistics.csv` and paired board-level statistics.
- `shared/sample_efficiency_results.csv`, negative controls, ablations,
  perturbation robustness, interval calibration, and selective-risk curves.
- `claim_readiness_audit.csv`, which marks claims that are supported, risky,
  prohibited, or still require prospective validation.
- Nine red-blue manuscript figures in PNG, SVG, PDF, and 600-DPI TIFF formats,
  each with a source-data CSV and an export manifest.

The figure sequence is: opening graphical abstract, knowledge architecture,
process-knowledge policy, structural memory, sparse-tail safeguard, validation
system, primary results, trust calibration, and evidence matrix.

## Recommendation card

```powershell
& $PY -m OTMAcodingV1.recommend `
  --db .\test.db `
  --board-id BOARD_ID `
  --device auto `
  --fgw-device cpu `
  --output .\recommendation_card.json
```

Use `--velocity-override VALUE` only for an engineer-approved deviation from
the empirical velocity policy.

`--device auto` uses CUDA only for sufficiently large batched descriptor
operations. Small arrays remain on CPU because host-device transfer overhead
would dominate. Keep
`--fgw-device cpu` for the current small graph pairs: measured POT FGW latency is
substantially lower on CPU because CUDA launch and iterative-transfer overhead
dominates these small matrices.

## Tests

```powershell
& $PY -m unittest discover -s .\OTMAcodingV1\tests -v
```

