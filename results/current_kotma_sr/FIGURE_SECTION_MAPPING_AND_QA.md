# KOTMA-SR figure-to-manuscript mapping and QA audit

## Naming recommendation

Recommended manuscript name: **KOTMA-SR**, short for **Knowledge-guided Optimal Transport Memory Alignment with Sparse-tail Reasoning**.

Do not use plain **KOTMA** as the main method name unless all ablations are renamed, because KOTMA is better treated as the method family. In this result package, the main method is KOTMA-SR and the OT-only ablation is KOTMA-SR (unconstrained).

## Figure QA summary

- Backend: Python / matplotlib, consistent with the selected plotting backend.
- Exports: every figure has PNG, SVG, PDF, TIFF and source-data CSV.
- Programmatic QA: 18/18 pass in `figure_qa_audit.csv`.
- Visual style: restrained red-blue-neutral palette, sans-serif publication fonts, lowercase panel labels, source-data-backed quantitative panels.
- Remaining layout note: several complex composite figures trigger Matplotlib `tight_layout` warnings, but all exports and source data were produced successfully. Before journal submission, open the final PDF/SVG versions and check text overlap at the actual printed width.

## Main figures

| Figure | Manuscript placement | Purpose |
|---|---|---|
| Fig1_Graphical_Abstract | Opening figure after Introduction, also anchors Sections 3.1-3.4 | One-picture story: first-article pressure recommendation, current-database-only evidence, KOTMA-SR effect over CBR, and claim boundary. |
| Fig2_Knowledge_Architecture | 4.1 Layered knowledge architecture | Shows the layered knowledge architecture from historical case memory to structural reasoning and recommendation output. |
| Fig3_Process_Knowledge | 3.1 First-article pressure recommendation task; 3.2 Historical case memory; 4.5 Trust-aware recommendation card | Establishes task objects, board-side independence, executable pressure range, velocity policy, and recommendation-card fields. |
| Fig4_Structural_Memory | 4.2 Process-aware structural memory | Shows how descriptors and process structure form a retrievable memory rather than a black-box regressor. |
| Fig5_Sparse_Tail_Gate | 4.3 Descriptor CBR as the auditable default; 4.4 Sparse-tail bounded reasoning | Explains when structural correction is allowed and why CBR remains the auditable default under common support. |
| Fig6_Validation_System | 5 Experimental Setup | Shows the validation protocol: physical-board grouped nested LOBO, A/B handling, baselines, bootstrap inference, and robustness checks. |
| Fig7_Primary_Results | 6.1 Overall recommendation performance | Main quantitative comparison: KOTMA-SR versus CBR and major baselines on retrospective pressure recovery. |
| Fig8_Trust_Calibration | 6.3 Trustworthiness analysis | Connects confidence, manual review, accepted coverage, and accepted-window recovery. |
| Fig9_Evidence_Matrix | 6.4 Robustness and engineering-readiness evidence | Reviewer-facing matrix for claim boundaries, readiness status, and prohibited overclaims. |

## Supplementary figures

| Figure | Manuscript placement | Purpose |
|---|---|---|
| FigS1_Grouped_Benchmark | 6.1 supplementary benchmark evidence | Strong-baseline benchmark including tree models, linear models, OT variants and exploratory comparators. |
| FigS2_Protocol_Sensitivity | 5 Experimental Setup; 6.4 robustness | Shows sensitivity to validation protocol choices. |
| FigS3_Sparse_Tail_Cases | 6.2 Structural-memory and sparse-tail analysis | Case-level evidence for sparse-tail improvement and failure modes. |
| FigS4_Gate_Sensitivity | 6.2; 6.4 | Gate-threshold sensitivity for the sparse-tail correction. |
| FigS5_Robustness | 6.4 | Robustness diagnostics under resampling and perturbation. |
| FigS6_Conditional_Calibration | 6.3 | Conditional trust and review-trigger behavior. |
| FigS7_Velocity_Policy | 3.4 Executability and review constraints; 6.4 | Documents the empirical velocity policy and why pressure is the main recommendation variable. |
| FigS8_Exploratory_GNN | 6.4 supplementary only | Exploratory GNN baseline; should not be framed as the primary methodological contribution. |
| FigS9_Interval_Comparators | 6.3; 6.4 | Interval comparator evidence and uncertainty-aware trustworthiness. |

## Coverage against the proposed paper frame

- Section 3 is adequately supported by Fig1 and Fig3, but should also include a notation/task table.
- Section 4.1-4.5 are well covered by Fig2-Fig5.
- Section 4.6 still needs **Algorithm 1** and a compact complexity table. This is better as a manuscript algorithm/table than as another figure.
- Section 5 is covered by Fig6 and FigS2.
- Sections 6.1-6.4 are covered by Fig7-Fig9 and FigS1-FigS9.

## Reviewer-facing conclusion

The figure system is sufficient for a JCR Q1 submission package under a bounded retrospective claim. For a KBS-level submission, the visual narrative is now coherent, but the manuscript must avoid universal superiority claims because the cluster-bootstrap intervals versus CatBoost and Ridge still cross zero.
