# AEI support audit

This report checks whether the result package includes the engineering-informatics support material requested for AEI-style review.

## Added support tables

- `dataset_scope_summary.csv`: 1 row(s).
- `method_rule_table.csv`: 8 row(s).
- `example_recommendation_card.csv`: 1 row(s).
- `protocol_mapping_audit.csv`: 6 row(s).

## Primary claim boundary

- Primary MAE: 0.2647.
- Accepted coverage: 0.824.
- Accepted within +/-0.4: 0.821.
- The package supports a retrospective knowledge-intensive engineering decision-support claim.
- It does not support autonomous process control, counterfactual quality optimization, or external deployment validation.

## AEI readiness note

The code now exports data-scope, method-rule, recommendation-card, and protocol-mapping evidence. These outputs are intended to make the methodology reproducible and to prevent confusion between primary nested validation, mechanism ablation, and diagnostic suites.