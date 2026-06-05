# KOTMA-SR figure interpretation and reviewer report

This report interprets Fig1-Fig9 and FigS1-FigS9 from a manuscript-review perspective. It follows a figure-first logic: what the figure shows, how it should be read, what conclusion it supports, and what claim boundary a KBS/JCR-Q1 reviewer would expect.

## Overall reviewer judgement

The figure set is coherent for a bounded retrospective decision-support paper. The main visual argument is: KOTMA-SR keeps descriptor CBR as an auditable default, activates bounded structural correction mainly in sparse-tail cases, and improves retrospective first-article pressure recovery over Top-1 CBR under physical-board grouped validation.

The strongest defensible claim is:

KOTMA-SR achieves the best retrospective MAE point estimate in the current database and significantly improves over Top-1 CBR under physical-board cluster-bootstrap inference.

The claim that should not be made is:

KOTMA-SR is statistically superior to every strong baseline or has already proven autonomous SMT quality optimization. The intervals versus CatBoost and Ridge still cross zero, and the database has no external site or temporal deployment field.

## Main figures

### Fig1 Graphical Abstract

**How to read it:** This is the opening visual story. Read it from left to right: sparse historical PCB-side cases, a new PCB side with hidden SPI response, dual memory retrieval through descriptor and structural memory, a selection gate, and a traceable recommendation card. The bottom metric cards summarize the central result: KOTMA-SR lowers MAE from 0.3235 to 0.2647 relative to CBR, with improved within-window recovery.

**Paper conclusion:** The paper addresses a small-data first-article recommendation task rather than generic process optimization. The innovation is not only FGW or CBR, but a review-aware, executable strategy that combines case memory, structural memory, sparse-tail reasoning, and a recommendation card.

**Reviewer interpretation:** This figure is strong as a KBS-style opening figure because it connects industrial constraint, method mechanism, and measured effect in one place. The phrase "not autonomous quality optimization" is important and should remain, because it protects the paper from overclaiming.

### Fig2 Knowledge Architecture

**How to read it:** Fig2 decomposes KOTMA-SR into layers: input knowledge, representation, memory alignment, selective reasoning, output and trust. The key is that structural memory is not used as an unconstrained predictor. It is filtered through process constraints and trust logic.

**Paper conclusion:** KOTMA-SR is a layered knowledge architecture, not a single black-box model. The architecture explains why the method is suitable for high-mix, small-sample SMT: it reuses human-auditable case memory and only adds structural evidence where support is weak.

**Reviewer interpretation:** This figure supports the methodological novelty. Reviewers will expect Section 4.1 to define each layer formally and Section 4.6 to add pseudocode and complexity. The figure alone is enough visually, but the text must make the data-flow and leakage controls precise.

### Fig3 Process Knowledge

**How to read it:** Fig3 explains the industrial process assumptions. Pressure is the active recommendation variable with an executable grid of 5.0-8.0 in 0.1 steps. Velocity is mostly an empirical anchor around 0.8, with engineer override supported. A/B sides are treated as independent recommendation objects, while physical board grouping is used in validation to avoid optimistic leakage.

**Paper conclusion:** The problem is well scoped: recommend a usable pressure for rapid first-article verification. The method does not pretend to discover a full pressure-speed quality landscape from one historical setting per board side.

**Reviewer interpretation:** This figure is important because it turns domain constraints into formal modelling constraints. A reviewer will likely accept the velocity treatment if the manuscript states that speed is nearly constant historically and that pressure is the controlled output.

### Fig4 Structural Memory

**How to read it:** Fig4 shows why graph/structure matters. PCB geometry is abstracted into structural memory; FGW alignment then supplies a structural similarity signal. The figure should be read as conditional evidence, not a replacement for CBR.

**Paper conclusion:** Structural memory provides information beyond descriptor-only recall, especially when the descriptor-nearest pressure lies in a weakly supported local tail.

**Reviewer interpretation:** This figure carries the "why OT/FGW?" argument. It needs to be paired with ablation evidence in Fig9 and sparse-tail evidence in Fig5/FigS3. Without those figures, Fig4 would look conceptual; with them, it becomes mechanistic.

### Fig5 Sparse Tail Gate

**How to read it:** The top row shows the decision rule: descriptor CBR first, support audit second, then either CBR default or bounded correction. The lower panels show that most sides stay on CBR default, while a smaller sparse-tail subset receives bounded correction.

**Paper conclusion:** KOTMA-SR improves mainly by intervening in sparse-tail situations, not by overriding CBR everywhere. This is the core mechanism claim. The stratum summary supports it: common-support MAE is essentially equal to CBR, while sparse-tail MAE improves from 0.5429 to 0.2571.

**Reviewer interpretation:** This is one of the most important method figures. It converts a possible reviewer criticism, "FGW may overfit small data", into a strength: FGW is bounded and conditionally activated. The manuscript should report the gate thresholds and correction cap explicitly.

### Fig6 Validation System

**How to read it:** Fig6 explains the evidence pipeline: current historical database, physical-board grouped nested LOBO, inner tuning, calibration, held-out evaluation, benchmark suite, mechanism suite, trust suite and robustness suite.

**Paper conclusion:** The evaluation is designed to reduce leakage. A/B sides are independent for recommendation, but the outer validation holds out physical boards together. This supports the retrospective claim more strongly than random side-level splits would.

**Reviewer interpretation:** This is the methodological defense figure. It should be cited before the results. It also clarifies that temporal or external validation is not claimed, because the current database lacks timestamp/site fields.

### Fig7 Primary Results

**How to read it:** Panel a ranks the primary methods by MAE. KOTMA-SR has the lowest MAE among the displayed methods. Panel b compares engineering-window recovery. Panel c shows paired difference versus CBR. Panel d gives reviewer-facing statistics including mean gain, Wilcoxon p, bootstrap probability and win/tie/loss.

**Paper conclusion:** KOTMA-SR improves retrospective pressure recovery over CBR: MAE 0.2647 versus 0.3235, with cluster-bootstrap advantage [0.0161, 0.1118]. It also improves within +/-0.2 and +/-0.4 over CBR.

**Reviewer interpretation:** This is the main result figure. The correct claim is "significantly better than CBR under clustered bootstrap." Do not say "statistically better than all strong baselines"; FigS1 shows why that would be too strong.

### Fig8 Trust Calibration

**How to read it:** Fig8 links confidence thresholds, accepted coverage, interval calibration and review triggers. The important reading is selective recommendation: the method can recommend directly for most cases but flags uncertain cases for review.

**Paper conclusion:** KOTMA-SR is designed as trust-aware engineering decision support. Accepted coverage is 82.4%, and accepted within +/-0.4 is 82.1%. Interval calibration is close but not perfect: 80% nominal gives 79.4% empirical, while 90% nominal gives 85.3%.

**Reviewer interpretation:** This figure is a strength for KBS because it addresses trustworthy AI and human-in-the-loop deployment. The limitation is that accepted within-window recovery is not yet above a very conservative 85% engineering threshold.

### Fig9 Evidence Matrix

**How to read it:** Fig9 is a compact reviewer-facing evidence matrix. It summarizes ablation, perturbation, sample-efficiency and negative-control evidence. Its purpose is not to introduce a new result, but to show that the claims are stress-tested.

**Paper conclusion:** The evidence supports a bounded retrospective recommendation claim and identifies prohibited overclaims. KOTMA-SR should be positioned as a selective, review-aware pressure recommendation method.

**Reviewer interpretation:** This figure helps with reviewer trust because it shows the authors know where the method fails or remains unproven. It should be used in Section 6.4 to close the Results section.

## Supplementary figures

### FigS1 Grouped Benchmark

**How to read it:** FigS1 expands the benchmark comparison beyond the main methods. It includes CatBoost, Ridge, ExtraTrees, Random Forest, SVR, Elastic Net, XGBoost, LightGBM, GP, OT variants, CBR variants and exploratory comparators.

**Paper conclusion:** KOTMA-SR has the best MAE point estimate among the benchmark suite. However, paired clustered intervals versus CatBoost and Ridge cross zero, so broad statistical superiority over all strong baselines is not established.

**Reviewer interpretation:** This is mandatory supplementary evidence for a KBS-level submission. It prevents the paper from looking like it only compared against weak baselines.

### FigS2 Protocol Sensitivity

**How to read it:** FigS2 compares results under different validation protocols or sensitivity settings. It should be read as a leakage and protocol robustness check, not as a second primary endpoint.

**Paper conclusion:** The central performance pattern is not an artifact of one convenient split. The physical-board grouped nested LOBO remains the primary protocol because it is the most conservative for the current database.

**Reviewer interpretation:** This figure helps answer whether the evaluation is cherry-picked. The manuscript should clearly state which protocol is primary and why.

### FigS3 Sparse Tail Cases

**How to read it:** FigS3 lists or visualizes case-level sparse-tail behavior. It separates common-support cases from sparse-tail cases and shows where bounded correction changes the recommendation.

**Paper conclusion:** The improvement is concentrated where historical local pressure support is weak. This supports the sparse-tail reasoning mechanism and explains why a globally unconstrained structural model is not used.

**Reviewer interpretation:** This is the case-level backup for Fig5. It helps reviewers see the method is not just tuned for aggregate MAE.

### FigS4 Gate Sensitivity

**How to read it:** FigS4 varies gate parameters such as minimum supported pressure cases and maximum tail adjustment. It shows how MAE, within-window recovery, review rate and correction rate respond.

**Paper conclusion:** The selected gate is a trade-off between correction strength and engineering review burden. Larger correction caps can improve some errors but risk less conservative behavior.

**Reviewer interpretation:** This figure is important for reproducibility. It shows the gate is not arbitrary. A reviewer may still ask for exact hyperparameter-selection rules, so Section 5 should specify that the gate is tuned only inside training folds.

### FigS5 Robustness

**How to read it:** FigS5 tests perturbations such as pad missingness, position noise, size noise, shape missingness and super-node count changes. The source data records recommendation shifts and review-flag changes.

**Paper conclusion:** Recommendations are stable under realistic descriptor perturbations in the current retrospective setting.

**Reviewer interpretation:** This supports engineering readiness, but it is still simulation-based robustness, not field deployment validation.

### FigS6 Conditional Calibration

**How to read it:** FigS6 compares nominal and empirical interval coverage overall and by strata such as common support and sparse tail. For example, overall 80% nominal coverage is 79.4%; 90% nominal is 85.3%.

**Paper conclusion:** The uncertainty intervals are useful and close to nominal at 80%, but the 90% interval undercovers modestly. This supports transparent recommendation cards but not perfect uncertainty quantification.

**Reviewer interpretation:** This is a sophisticated trustworthiness figure. It should be reported candidly because it strengthens credibility.

### FigS7 Velocity Policy

**How to read it:** FigS7 compares observed velocity with a fixed 0.8 policy and fold-mode policy. Most historical records use 0.8, with a few deviations. Engineer override is supported.

**Paper conclusion:** Velocity is not learned as a flexible target because the database shows it is an empirical process anchor. The active recommendation task is pressure.

**Reviewer interpretation:** This figure prevents confusion about why the paper does not optimize speed. It should be cited in the problem formulation and executability constraints.

### FigS8 Exploratory GNN

**How to read it:** FigS8 reports exploratory small-n GNN results across seeds. The GNN MAE is much worse than KOTMA-SR in this database, with seed-level MAE around 0.54-0.74.

**Paper conclusion:** End-to-end graph learning is not reliable under the current sample size. This supports the choice of structured memory and bounded reasoning rather than a deep graph model as the main approach.

**Reviewer interpretation:** This is useful only as supplementary exploratory evidence. It should not be overemphasized as a definitive rejection of GNNs in larger datasets.

### FigS9 Interval Comparators

**How to read it:** FigS9 compares uncertainty intervals across KOTMA-SR, Ridge and Top-1 CBR. KOTMA-SR has 80% empirical coverage of 79.4% with mean interval width about 0.96, while CBR and Ridge have similar coverage with wider or comparable intervals.

**Paper conclusion:** KOTMA-SR produces uncertainty estimates that are competitive with baseline comparators while preserving a traceable recommendation process.

**Reviewer interpretation:** This figure supports the trust-aware claim, but it should be framed as interval comparison, not a guarantee of calibrated deployment performance.

## Cross-figure synthesis

The complete figure set supports four manuscript-level conclusions.

First, the task is carefully bounded: first-article pressure recommendation for rapid verification, not counterfactual quality optimization.

Second, the main methodological novelty is selective sparse-tail reasoning over a process-aware memory. The method improves where CBR is weak while retaining CBR when support is adequate.

Third, the primary quantitative result is credible within the current database: KOTMA-SR improves over CBR in grouped retrospective validation.

Fourth, the paper must remain honest about limits. The evidence is sufficient for a competitive JCR-Q1 submission package, but KBS-level claims must avoid universal strong-baseline superiority, prospective deployment success, or external-site generalization.

## Recommended manuscript placement

- Opening/Introduction: Fig1.
- Problem Formulation: Fig3, FigS7.
- Method: Fig2, Fig4, Fig5.
- Experimental Setup: Fig6, FigS2.
- Results 6.1: Fig7, FigS1.
- Results 6.2: Fig5, FigS3, FigS4.
- Results 6.3: Fig8, FigS6, FigS9.
- Results 6.4: Fig9, FigS5, FigS8.

## Editorial recommendation

From an academic-paper-reviewer perspective, the visual evidence package is suitable for a bounded retrospective KBS-style submission after manuscript writing is tightened. The remaining weakness is not figure quality; it is the statistical scope of the current database. The manuscript should make the CBR comparison central, report strong-baseline results transparently, and frame prospective validation as future deployment evidence rather than completed proof.
