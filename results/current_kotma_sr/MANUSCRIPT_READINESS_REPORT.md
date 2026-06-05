# KOTMA-SR manuscript readiness report

## Scope

Retrospective recovery of historically executed first-article printing pressure settings for independent PCB sides. This is not counterfactual quality optimization or autonomous process control.

## Primary evidence

- Independent PCB sides: 34; physical boards: 21.
- Primary protocol: physical-board grouped nested LOBO; A/B sides are evaluated independently but held out together.
- Pressure MAE: KOTMA-SR 0.2647 versus CBR 0.3235.
- Best non-KOTMA-SR grouped benchmark: CatBoost with MAE 0.2912.
- Relative MAE reduction: 18.2%.
- Within +/-0.2: KOTMA-SR 55.9% versus CBR 41.2%.
- Within +/-0.4: KOTMA-SR 79.4% versus CBR 73.5%.
- Side-level paired Wilcoxon p: 0.05257. Physical-board cluster-bootstrap CI for mean MAE advantage: [0.0161, 0.1118].

## Selective reasoning

- Descriptor CBR safeguard: 27 PCB sides.
- Bounded structural tail correction: 7 PCB sides.
- Accepted coverage: 82.4%.
- Accepted within +/-0.4: 82.1%.

## Reviewer boundary

- [pass] physical_board_grouped_nested_lobo: Outer folds hold out both A/B sides of each physical board; held-out boards are excluded from tuning, scaling and calibration. Action: Use manuscript claims only for a complete non-smoke run.
- [candidate] strong_baseline_benchmark: KOTMA-SR MAE=0.2647; best non-KOTMA-SR baseline=CatBoost MAE=0.2912; paired advantage=0.02647. Action: Claim broad superiority only when the grouped benchmark supports it; otherwise present the method as a trustworthy selective strategy with explicit trade-offs.
- [risk] engineering_usability: accepted coverage=0.824; accepted within +/-0.4=0.821. Action: Claim trustworthy selective recommendation only if accepted coverage and usability remain adequate.
- [candidate] bounded_structural_correction: descriptor CBR MAE=0.2882; bounded sparse-tail correction MAE=0.2382. Action: Describe FGW as a bounded sparse-tail correction unless paired analysis supports a stronger claim.
- [pass] paired_cbr_evidence: mean MAE advantage=0.05882; side-level Wilcoxon p=0.05257; physical-board cluster-bootstrap CI=[0.01613, 0.1118]. Action: Use the physical-board cluster-bootstrap interval as primary inference and report the side-level Wilcoxon test as a supplementary diagnostic.
- [prohibited] universal_metric_dominance: Methods with higher within +/-0.4 recovery than KOTMA-SR: ['Training median', 'Training mode']. Action: Do not claim superiority on every metric; state the primary MAE endpoint and trade-offs explicitly.
- [limitation] current_database_only_scope: All experiments are intentionally restricted to the current local historical database. The available database has no usable acquisition timestamp, batch-time or site field for a defensible temporal or external split. Action: State the single-database retrospective scope explicitly. Do not fabricate temporal ordering or present prospective/external validation as completed evidence.
- [future_work] future_deployment_validation: Engineer-supervised prospective verification and external-site validation require data outside the declared current-database-only experiment scope. Action: Describe these as future deployment-validation directions, not as missing experiments within the present retrospective study.
- [prohibited] quality_optimization_claim: Each board has one historically executed setting; counterfactual quality is unavailable. Action: Use recommendation, recovery and manual-review language only.

## Figure QA

- Publication figures passed export and source-data QA: 18/18.
- Each figure is exported as PNG, SVG, PDF, TIFF, and a source-data CSV.
