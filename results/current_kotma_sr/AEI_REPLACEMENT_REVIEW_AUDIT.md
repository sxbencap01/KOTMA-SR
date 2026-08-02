# AEI replacement review audit

## Scope

This audit reviews the code and generated-result replacement performed for the AEI-oriented manuscript revision. The replacement intentionally adds reproducibility and engineering-interpretation outputs without changing the KOTMA-SR recommendation logic, hyperparameter search space, validation protocol, or primary claim boundary.

## Code changes reviewed

- Added dataset-scope, method-rule, example recommendation-card, protocol-mapping, and AEI support-report exports to `OTMAcodingV1/run_experiments.py`.
- Kept descriptor retrieval, super-node coarsening, FGW matching, sparse-tail support audit, bounded correction, empirical interval calibration, and review-trigger logic unchanged.
- The new outputs are generated from existing `records`, `artifacts`, and validation traces.

## Generated outputs reviewed

- `shared/dataset_scope_summary.csv` reports 34 PCB sides from 21 physical boards, A/B-side counts, feasible action ranges, pressure/velocity distribution, pad-count distribution, and board-size summaries.
- `shared/method_rule_table.csv` provides eight reproducibility rows covering descriptor memory, retrieval, super-node structural memory, FGW, sparse-tail gate, bounded correction, empirical intervals, and review triggers.
- `shared/example_recommendation_card.csv` exports a held-out recommendation-card example with pressure, velocity, CBR pressure, structural pressure, action, top neighbors, intervals, confidence, and review reasons.
- `shared/protocol_mapping_audit.csv` separates the primary grouped nested validation from mechanism ablation, negative controls, interval diagnostics, robustness, and sample-efficiency analyses.
- `AEI_SUPPORT_AUDIT.md` records the AEI-facing support summary and claim boundary.

## Reviewer-style conclusion

The replacement correctly addresses the code/result side of the previously identified AEI shortcomings. It strengthens method reproducibility and prevents confusion between Table 3 primary nested results and Table 4 mechanism-ablation results. The primary numerical claim remains unchanged: KOTMA-SR MAE is 0.2647 versus descriptor CBR MAE 0.3235 under physical-board grouped nested validation. The added outputs support a retrospective knowledge-intensive engineering decision-support claim, not autonomous process control, counterfactual quality optimization, or external deployment validation.

Remaining manuscript-side work still required: update the article text to cite these new tables, replace the residual "For Computers in Industry" sentence with AEI wording, improve the AI-use declaration, and complete the reference-format cleanup.
