## 2. Related work

### 2.1 SMT printing process recommendation

Research on solder-paste printing has traditionally focused on experimental characterization, process-window analysis, and parameter optimization. Printing pressure, squeegee speed, stencil geometry, aperture ratio, and paste characteristics are commonly treated as controllable factors that affect deposit geometry and downstream quality. Recent work has extended this line of research from static parameter analysis to data-supported optimization. Lee et al. combined neural-network surrogates with particle-swarm optimization to improve SMT process quality and productivity while reducing the number of physical experiments [1]. Zhang et al. formulated a human-on-the-loop deep-reinforcement-learning approach for SMT control, showing how iterative feedback can support adaptive parameter adjustment [2]. Related manufacturing research has also used human-in-the-loop Bayesian optimization to reduce experimental burden in complex process optimization [3].

These studies advance process modeling and closed-loop adjustment, but their assumptions differ from the first-article problem considered here. Surrogate optimization and reinforcement learning are most useful when target-process experiments, inspection outcomes, or online feedback are available. In high-mix and high-reliability production, an unseen PCB may instead require an executable initial setting before target-board outcomes have accumulated. The practical question is therefore not how to search without restriction for a globally optimal pressure, but how to reuse validated engineering experience while exposing the limits of that reuse. This motivates an industrial decision-support architecture centered on historical cases, executable constraints, and engineer review.

### 2.2 Case-based reasoning for manufacturing knowledge reuse

Case-based reasoning (CBR) organizes historical problem-solution pairs as reusable knowledge. For a new task, similar cases are retrieved, prior solutions are reused or adapted, and validated experience can be retained for future decisions [31]. This logic is attractive in manufacturing because process knowledge is often distributed across historical records, engineering rules, and context-dependent judgments. Recent studies have combined case retrieval with knowledge-graph embeddings for manufacturing inspection [4], developed dynamic machining-process knowledge bases that integrate ontology, production rules, querying, CBR, and rule-based reasoning [5], and proposed knowledge-model updating mechanisms for digital-twin manufacturing environments [6]. These studies illustrate a broader move from isolated predictive models toward traceable knowledge-guided decision support.

For first-article SMT recommendation, descriptor-level CBR is useful because an engineer can inspect which historical PCBs support a proposed setting. However, tabular descriptors inevitably compress information. Two PCBs may have similar board dimensions, pad counts, or aperture statistics while differing in local pad density and spatial organization. The weakness is not that descriptor-based retrieval lacks value, but that it may treat structurally different boards as similar when the historical case base is sparse. Accordingly, descriptor-level CBR is retained as an auditable default, while structural evidence is introduced only when tabular similarity is insufficient.

### 2.3 Structural similarity and optimal transport

A PCB pad field cannot be fully represented by an ordinary fixed-length vector. Different boards contain variable numbers of pads, heterogeneous local geometries, and no natural one-to-one pad correspondence. Optimal transport (OT) provides a principled family of tools for comparing heterogeneous objects. Wasserstein formulations compare feature distributions, Gromov-Wasserstein (GW) formulations compare intra-object relationships [32], and fused Gromov-Wasserstein (FGW) formulations jointly account for attributes and structure [33]. Recent research has improved the efficiency and applicability of these ideas for graph-structured data. Nguyen and Tsuda proposed linearFGW to approximate graph similarity more efficiently [11]. Ma et al. used FGW to construct graph mixups while accelerating optimization [12]. Tang et al. transformed graph-edit-distance computation into an FGW-alignment problem [13]. Piening and Beinert proposed a sliced FGW formulation that lowers computational burden while retaining useful invariance properties [14]. Outside manufacturing, recent studies have also used GW alignment for structure-preserving feature selection [15] and graph OT for hyperspectral representation learning [16]. These cross-domain examples are cited as technical evidence for structure-aware comparison, not as direct evidence for PCB process transfer.

The present study does not claim a new OT distance. Instead, FGW-based matching is used as complementary evidence within a conservative CBR architecture. This distinction matters in manufacturing: similar pad-field geometry may support knowledge transfer, but it does not establish identical material behavior, equipment conditions, or process outcomes. Super-node coarsening is therefore used to control matching cost for dense pad fields, while the structural module qualifies bounded adaptation rather than replacing traceable historical cases.

### 2.4 Trustworthy industrial decision support

In high-reliability manufacturing, a recommendation system is incomplete if it outputs only a point estimate. Engineers also need to know which historical cases support a recommendation, whether the proposed value lies within executable limits, whether the input is weakly supported by prior experience, and when manual review is required. Recent manufacturing research increasingly frames AI as a supervised and human-centric capability rather than an unconditional replacement for engineering judgment. Surveys and applications have examined trustworthy AI for human-centric manufacturing [7], integrated safety and quality assurance [8], broader manufacturing-AI opportunities and limitations [9], conversational access to real-time manufacturing data [10], human-in-the-loop assembly learning [20], human-cyber collaborative scheduling under uncertainty [21], and human-supervised or knowledge-enhanced manufacturing decisions [23-27,30].

Uncertainty information should also change system behavior. Conformal prediction is relevant because it produces sets or intervals that expose uncertainty rather than forcing a single confident output [34]. Cresswell et al. showed that conformal prediction sets can improve human decision making [17]. Zhang et al. examined their utility in AI-advised image labeling [18], while De Toni et al. studied prediction sets designed for human-AI complementarity [19]. In an industrial setting, class-conditional conformal prediction has been used to support transparent uncertainty quantification and rejection under open-set fault conditions [22]. These studies are adjacent methodological references rather than direct validations of the SMT workflow.

Prior work has advanced SMT optimization, manufacturing knowledge reuse, structural matching, and trustworthy decision support largely as separate lines of research. Their intersection remains less developed for cold-start first-article SMT pressure recommendation under sparse historical coverage. The gap is industrial as well as algorithmic: the system must reuse validated experience, compare variable-size PCB structures, remain executable on production equipment, and expose uncertainty and review conditions to engineers. This motivates KOTMA-SR, a bounded case-based decision-support framework that preserves CBR as the auditable default, introduces FGW-based structural evidence selectively, and produces traceable recommendation cards rather than autonomous control actions.

## 3. Problem formulation and data scope

The industrial problem addressed in this study is first-article recommendation of solder-paste printing pressure for a newly introduced PCB side in high-reliability SMT production. In such production, an engineer needs an executable initial setting before repeated target-board trial printing has accumulated sufficient inspection feedback. The task is therefore different from closed-loop process optimization, in which repeated target-process measurements can be used to search for an optimum. It is also different from solder-joint quality prediction, because the present database records one historically executed process setting for each PCB side rather than a counterfactual response surface over alternative pressure-speed combinations. This distinction is important for industrial decision support: the proposed system recommends a historically plausible first setting for engineer-supervised verification; it does not claim autonomous process control or defect-rate optimization. The problem setting and executable manufacturing assumptions are summarized in Fig. 3.

Each case in the historical memory is represented as a PCB-side problem paired with a validated printing-pressure setting and associated process metadata. A PCB side is treated as the recommendation unit because the two sides of a physical board may differ in pad layout, component distribution, and production requirements. However, the two sides are not treated as independent physical products during validation. When a physical board has both A and B sides, both sides are held out together in the outer evaluation fold. This design prevents a model from learning one side of a board and then appearing to generalize to the other side through shared board-level identity or geometry. The evaluation unit is therefore the PCB side, while the leakage-control unit is the physical board.

Let the historical case base be denoted by \(\mathcal{D}=\{(B_i, x_i, G_i, p_i, v_i)\}_{i=1}^{n}\), where \(B_i\) is the physical-board identifier, \(x_i\) is a fixed-length descriptor vector, \(G_i\) is a structural representation of the pad field, \(p_i\) is the historically executed printing pressure, and \(v_i\) is the executed squeegee velocity. For a target PCB side \(j\), the system observes \(x_j\) and \(G_j\), but not the target outcome under alternative parameter values. It outputs a pressure recommendation \(\hat{p}_j\), an empirical velocity suggestion \(\hat{v}_j\), uncertainty intervals, traceable neighboring cases, and review triggers. The primary endpoint is the absolute recovery error \(|\hat{p}_j-p_j|\), where \(p_j\) is the historically executed first-article pressure for the held-out side. This endpoint should be interpreted as retrospective recovery of engineering practice, not proof that the recovered pressure is globally optimal. Table 1 defines the notation and claim boundary used throughout the method and evaluation.

**Table 1. Problem notation and claim boundary.**

| Symbol or term | Meaning in this study | Claim boundary |
|---|---|---|
| PCB side | One side of a physical PCB used as the recommendation object | A/B sides can differ and are evaluated as side-level recommendations |
| Physical board | Physical PCB identifier used as the leakage-control unit | All sides of a held-out physical board are excluded from training and tuning |
| \(x_i\) | Fixed-length board and pad-field descriptor vector | Used for auditable descriptor CBR retrieval |
| \(G_i\) | Structural pad-field representation after super-node coarsening | Used as complementary structural evidence |
| \(p_i\) | Historically executed first-article printing pressure | Treated as the retrospective recovery target |
| \(v_i\) | Historically executed squeegee velocity | Used to define an empirical velocity suggestion, not a learned optimization target |
| \(\hat{p}_j\) | Recommended pressure for held-out target side \(j\) | Rounded to the executable pressure grid before evaluation |
| Primary endpoint | \(|\hat{p}_j-p_j|\) and its mean across held-out sides | Measures retrospective recovery, not counterfactual quality improvement |
| Review trigger | Rule that flags weak evidence or uncertain recommendation | Supports human-in-the-loop review rather than autonomous release |

The executable action space follows the observed engineering setting range in the current database. Pressure recommendations are restricted to the feasible pressure interval and rounded to a 0.1 grid before evaluation. This choice reflects industrial use: a recommendation that cannot be directly set on the equipment is less valuable than a slightly less flexible but executable value. Velocity is handled as an empirical policy because the available records show that it is largely anchored by historical shop-floor practice, with engineer override retained for exceptional cases. Consequently, pressure is the active recommendation target, while velocity is reported as contextual process guidance. The velocity evidence is reported in Fig. S7.

The current database contains 34 independent PCB-side records from 21 physical boards. The database does not contain a reliable acquisition timestamp, production-site field, or prospective deployment log that would support a temporal split or external validation. The study therefore adopts a current-database-only retrospective design and states this boundary explicitly. This limitation is not a reason to use random side-level splitting; rather, it motivates a grouped validation protocol and a conservative decision-support claim. Similar caution is recommended in human-centric manufacturing AI, where system outputs must remain interpretable, reviewable, and aligned with operational constraints rather than presented as unconditional automation [7-10,20,23].

## 4. Safe-KOTMA/KOTMA-SR method

KOTMA-SR is short for Knowledge-guided Optimal Transport Memory Alignment with Sparse-tail Reasoning. It is designed as a knowledge-reuse framework for sparse industrial histories. Its central principle is conservative adaptation: descriptor-based CBR remains the auditable default, while structural evidence is used only when the local historical support for the descriptor-nearest recommendation is weak. This design follows the CBR view that historical cases constitute reusable problem-solution knowledge [31], but extends it for variable-size PCB geometry and engineering review. In contrast to black-box regression, the system must show which historical boards support a recommendation, why a correction was or was not applied, and when the decision should be escalated for human review. The overall architecture is shown in Fig. 2.

### 4.1 Case memory and descriptor-level retrieval

The first memory layer is a descriptor case memory. For each PCB side, the system constructs a fixed-length descriptor vector from board-level and pad-field summary information, including pad count, board dimensions, pad-area statistics, aperture-ratio statistics, aspect-ratio statistics, and spatial spans. Descriptors are standardized within each training fold to avoid test-fold information leakage. Given a target PCB side, the system retrieves similar historical cases according to descriptor distance. The nearest descriptor case supplies the CBR safeguard recommendation, while the top-ranked neighborhood supplies traceable evidence and local support statistics.

Descriptor-level retrieval is deliberately retained even though it compresses the pad field. In an industrial recommendation workflow, a method that can identify a small set of similar historical boards is easier to audit than a purely parametric model. The limitation is that descriptor similarity may ignore local geometry and layout organization. Therefore, descriptor CBR is treated as the default evidence channel, not the only evidence channel.

### 4.2 Structural memory by super-node coarsening and FGW matching

The second memory layer represents each PCB side as a structural pad-field object. Direct pad-to-pad matching is computationally expensive and unstable because different PCB sides have different numbers of pads and no natural pad index correspondence. The method therefore coarsens each pad field into super-nodes using position, pad-size, and local-density information. The resulting graph-like object preserves coarse spatial structure while reducing the matching cost. This structural-memory construction is illustrated in Fig. 4.

Structural similarity is computed with a fused Gromov-Wasserstein matching signal. GW compares relational structure between objects, while FGW combines node attributes with internal relational geometry [32,33]. This is suitable for PCB-side comparison because process transfer may depend on both local pad attributes and global layout organization. Recent work has shown that FGW and related graph OT formulations can be adapted for graph similarity, graph mixup, graph-edit-distance approximation, and efficient sliced variants [11-14]. In this study, however, FGW is not proposed as a new distance. It is used as a complementary structural evidence source inside a bounded industrial reasoning architecture.

### 4.3 Sparse-tail support audit and bounded structural correction

The key decision rule is the sparse-tail support audit. After descriptor retrieval, the system examines whether the nearest descriptor-supported pressure lies in a locally well-supported pressure region. If the descriptor neighborhood provides sufficient support, the recommendation remains the descriptor CBR pressure. If the nearest pressure lies in a sparse historical tail, the system allows a bounded correction informed by structural neighbors. The correction is capped by a training-fold-selected maximum adjustment and then rounded to the executable pressure grid. The gate logic and its case-level consequences are shown in Fig. 5 and Fig. S3.

This rule is intentionally asymmetric. Structural evidence is not allowed to override CBR everywhere, because unconstrained structural matching can be unreliable in small historical databases. Instead, the method asks a narrower question: when descriptor CBR is likely to rely on weak local evidence, does the structural memory provide enough additional evidence to make a small, bounded adjustment? This selective design is consistent with trustworthy industrial decision support, where model behavior should change under uncertainty rather than forcing a single confident output [7,17-19,22].

### 4.4 Recommendation card, uncertainty intervals, and review triggers

For each target PCB side, KOTMA-SR produces a recommendation card rather than only a point estimate. The card includes the recommended pressure, the empirical velocity suggestion, the descriptor CBR pressure, any structural correction, the retrieved neighbors and their weights, uncertainty intervals, runtime, and review reasons. Review triggers are activated when evidence is weak, the target appears outside the training-fold descriptor coverage, the interval is wide, or the sparse-tail rule indicates that the recommendation depends on limited local support.

The uncertainty intervals are empirical intervals calibrated only from training-fold residuals inside the nested validation protocol. They are not presented as certified safety bounds. Their function is operational: they help engineers distinguish routine recommendations from cases requiring extra inspection. This aligns with conformal and prediction-set research showing that uncertainty sets can improve human-AI decision making when they are displayed as decision aids rather than hidden model diagnostics [17-19,34].

### 4.5 Algorithmic summary and leakage controls

For each outer fold, all preprocessing, descriptor scaling, support thresholds, calibration residuals, and hyperparameter choices are fit using only the training physical boards. For a held-out target side, KOTMA-SR retrieves descriptor neighbors, computes or looks up structural similarities to training cases, audits local pressure support, either keeps the CBR safeguard or applies a bounded structural correction, rounds the final pressure to the executable grid, and generates the recommendation card. No held-out side, its paired physical-board side, or its residual enters tuning, scaling, or interval calibration. The procedure is summarized in Algorithm 1.

**Algorithm 1. KOTMA-SR recommendation for one outer validation fold.**

```text
Input:
  Training physical-board cases D_train
  Held-out target PCB side q
  Fold-local hyperparameter grid H

Output:
  Recommended pressure p_hat(q)
  Empirical velocity suggestion v_hat(q)
  Recommendation card C(q)

1. Fit descriptor scaler using D_train only.
2. Select hyperparameters h* by inner grouped validation on D_train.
3. Build descriptor memory from scaled descriptors in D_train.
4. Build structural memory by super-node coarsening for D_train.
5. Retrieve descriptor neighbors of q and compute descriptor CBR pressure.
6. Audit local pressure support around the descriptor-nearest pressure.
7. If support is sufficient:
       keep descriptor CBR pressure as p_hat(q).
   Else:
       compute structural-neighbor evidence using FGW memory;
       apply a bounded sparse-tail correction;
       round the corrected pressure to the executable 0.1 grid.
8. Estimate fold-local empirical intervals from training residuals.
9. Set review triggers from support, coverage, interval width, and OOD flags.
10. Return p_hat(q), v_hat(q), retrieved-neighbor evidence, intervals, and review reasons.
```

The method is evaluated as a deployable decision-support procedure rather than as an oracle fitted on all records. The median held-out runtime of KOTMA-SR in the complete run was 63.8 ms per PCB side, which is compatible with interactive engineering review rather than offline-only analysis.

## 5. Experimental design

The experimental design follows the industrial scope defined above. All experiments use the current historical database and evaluate retrospective pressure recovery for 34 PCB sides from 21 physical boards. The primary protocol is physical-board grouped nested leave-one-board-out validation. In each outer fold, one physical board is held out; if both A and B sides are present, both are excluded from the training data. Hyperparameters are selected in an inner grouped validation loop over the remaining boards. The final model for that fold is then refit on the outer-training boards and evaluated on the held-out side or sides. This protocol is stricter than random side-level splitting and is intended to test whether the case memory can support unseen physical boards. The validation system is summarized in Fig. 6, and protocol sensitivity is reported in Fig. S2.

The primary metric is pressure mean absolute error in raw pressure units. Two engineering-window recovery rates are also reported: the fraction of sides within +/-0.2 and within +/-0.4 of the historically executed pressure. These window metrics are secondary because a method can achieve a high +/-0.4 rate by predicting a common pressure while still having larger average error. Median absolute error, accepted coverage, accepted within-window recovery, and median runtime are reported as additional diagnostics. Paired comparisons use side-level paired statistics and physical-board cluster-bootstrap intervals, with the latter treated as the primary inference because physical boards are the independence unit. Bootstrap intervals are widely used for robust uncertainty estimation when analytic sampling distributions are undesirable [35].

The baseline suite is designed to separate several explanations for performance. First, CBR baselines include Top-1 CBR, local median CBR, weighted kNN-CBR, and local mode CBR. Second, tabular machine-learning baselines include Ridge, Elastic Net, RBF-SVR, Random Forest, ExtraTrees, CatBoost, XGBoost, LightGBM, and Gaussian Process regression. These baselines test whether the proposed method is merely recovering a conventional descriptor-to-pressure regression relation. Third, structural baselines include Wasserstein-only, GW-only, FGW-only, and descriptor-plus-FGW retrieval. These baselines test whether unconstrained structural matching is sufficient. Fourth, naive historical controls include training median, training mode, nearest pad-count only, and random historical pressure. Finally, an exploratory graph neural network baseline is included as a small-sample diagnostic rather than as a primary comparator, because end-to-end graph learning is not expected to be stable with 34 side-level observations. Tree boosting and ensemble baselines are included because they are common high-performing tabular baselines in industrial prediction studies [36-39].

Several additional analyses test the industrial decision-support behavior. Ablations compare descriptor CBR, FGW-only retrieval, descriptor-plus-FGW retrieval, and the sparse-tail correction mechanism. Mechanism stratification separates common-support cases from sparse-tail cases. Calibration analyses evaluate empirical interval coverage at nominal 80% and 90% levels overall and by review status. Robustness analyses perturb pad missingness, position noise, size noise, shape availability, and super-node counts. Sample-efficiency analyses evaluate performance under reduced numbers of training physical boards. These analyses are included to communicate not only an aggregate score, but also when the system works, when it should defer, and which assumptions matter for industrial use.

The implementation was run in manuscript mode with fixed random seed 2026. The environment used Python 3.9.21 with NumPy 1.26.4, pandas 2.2.3, SciPy 1.13.1, scikit-learn 1.6.1, and POT 0.9.6.post1. All figures were exported with source-data CSV files to support reproducibility and auditability. Table 2 summarizes the evaluation protocol and evidence package.

**Table 2. Experimental protocol and evidence package.**

| Component | Setting in this study | Purpose |
|---|---|---|
| Database | 34 PCB sides from 21 physical boards | Current historical SMT first-article records |
| Primary split | Physical-board grouped nested LOBO | Avoids A/B-side leakage during tuning and evaluation |
| Primary endpoint | Pressure MAE | Retrospective recovery of executed pressure |
| Secondary endpoints | Within +/-0.2 and +/-0.4 recovery; median error | Engineering-window diagnostics |
| Trust endpoints | Accepted coverage; accepted within +/-0.4; interval coverage | Measures selective recommendation behavior |
| Baselines | CBR, tabular ML, structural OT, naive historical controls, exploratory GNN | Separates CBR, regression, structural, and trivial explanations |
| Inference | Physical-board cluster bootstrap; side-level Wilcoxon diagnostic | Accounts for grouped physical-board dependence |
| Robustness | Pad, position, size, shape, and super-node perturbations | Tests sensitivity of industrial inputs |
| Reproducibility | Fixed seed, recorded package versions, source-data CSV for each figure | Supports auditability |

## 6. Results

### 6.1 Primary retrospective pressure recovery

Under physical-board grouped nested validation, KOTMA-SR achieved the lowest primary MAE among the main methods evaluated in the primary protocol. Its pressure MAE was 0.2647, compared with 0.3235 for descriptor CBR, 0.3148 for an unconstrained KOTMA-SR variant, 0.3059 for the training median, and 0.4235 for the training mode. Relative to CBR, this corresponds to an 18.2% reduction in MAE. The median absolute error also decreased from 0.4000 for CBR to 0.1000 for KOTMA-SR. Engineering-window recovery improved from 41.2% to 55.9% within +/-0.2 and from 73.5% to 79.4% within +/-0.4. These results are summarized in Fig. 7 and Table 3.

The paired evidence supports a bounded improvement over CBR. The mean MAE advantage of KOTMA-SR over CBR was 0.0588, with a physical-board cluster-bootstrap confidence interval of [0.0161, 0.1118] and a bootstrap probability of 0.9988 that KOTMA-SR was better. The side-level Wilcoxon test was borderline (p = 0.0526), which is expected in part because pressure recommendations are rounded to a discrete 0.1 grid and many sides tie exactly. Therefore, the cluster-bootstrap interval is used as the primary inference, while the Wilcoxon test is reported as a supplementary paired diagnostic.

Strong tabular baselines were competitive. CatBoost, Ridge, and ExtraTrees each obtained an MAE of approximately 0.2912, while Random Forest obtained 0.2941. KOTMA-SR had the best MAE point estimate, but the evidence does not support statistically significant superiority over all strong baselines. Some secondary window metrics also favored simple baselines; for example, Ridge achieved a +/-0.4 recovery rate of 82.4%, and the training median and training mode reached 88.2% within +/-0.4 despite worse MAE. These results indicate that KOTMA-SR should be interpreted as a selective, traceable recommendation strategy with favorable MAE, not as a universally dominant predictor on every metric. The full grouped benchmark is provided in Fig. S1.

**Table 3. Primary grouped retrospective pressure-recovery results.**

| Method | MAE | Median absolute error | Within +/-0.2 | Within +/-0.4 | Accepted coverage | Accepted within +/-0.4 |
|---|---:|---:|---:|---:|---:|---:|
| KOTMA-SR | 0.2647 | 0.1000 | 55.9% | 79.4% | 82.4% | 82.1% |
| Descriptor CBR | 0.3235 | 0.4000 | 41.2% | 73.5% | NA | NA |
| KOTMA-SR unconstrained | 0.3148 | 0.2141 | 47.1% | 67.6% | NA | NA |
| Training median | 0.3059 | 0.4000 | 38.2% | 88.2% | NA | NA |
| Training mode | 0.4235 | 0.4000 | 8.8% | 88.2% | NA | NA |

### 6.2 Mechanism: bounded sparse-tail correction

The ablation results show that the method's benefit does not come from using structural matching indiscriminately. Descriptor CBR achieved an ablation MAE of 0.2882, FGW-only retrieval achieved 0.3262, and descriptor-plus-FGW retrieval achieved 0.2917. The sparse-tail correction variant achieved the best ablation MAE, 0.2382, while preserving a +/-0.4 recovery rate of 79.4%. This pattern supports the design choice made in Section 4: structural evidence is useful when it is used as a bounded corrective signal, but unconstrained structural retrieval alone is not reliable enough for this small industrial database. Fig. 5 shows the sparse-tail decision gate, while Fig. 9 summarizes the ablation evidence within the broader evidence matrix.

The mechanism-stratified results make this interpretation more precise. In the common-support stratum, which contained 27 sides from 18 physical boards, KOTMA-SR and CBR had essentially identical MAE, both approximately 0.2667. In the sparse-tail stratum, which contained 7 sides from 6 physical boards, CBR MAE was 0.5429, while KOTMA-SR MAE was 0.2571. The mean gain over CBR in this stratum was 0.2857. Thus, the system improves mainly where descriptor retrieval is locally weak, while preserving the CBR safeguard when the historical neighborhood is well supported. Case-level sparse-tail behavior is reported in Fig. S3, and gate-threshold sensitivity is reported in Fig. S4.

**Table 4. Mechanism and ablation summary.**

| Analysis | Group or method | n sides | MAE | Within +/-0.4 | Interpretation |
|---|---|---:|---:|---:|---|
| Ablation | Descriptor CBR | 34 | 0.2882 | 76.5% | Auditable default |
| Ablation | FGW only | 34 | 0.3262 | 70.6% | Structural matching alone is insufficient |
| Ablation | Descriptor + FGW | 34 | 0.2917 | 73.5% | Naive fusion does not explain the gain |
| Ablation | Sparse-tail correction | 34 | 0.2382 | 79.4% | Best mechanism-level variant |
| Stratum | Common support | 27 | 0.2667 | NA | KOTMA-SR preserves CBR behavior |
| Stratum | Sparse tail | 7 | 0.2571 | NA | Main source of gain over CBR |

This result is important for the industrial interpretation of the method. A purely structural model would be difficult to justify when historical evidence is sparse and the production consequence of a poor recommendation may be costly. Conversely, a pure CBR model may fail when the nearest descriptor case lies in a weakly supported pressure tail. KOTMA-SR resolves this tension by making the structural module conditional and bounded. The method therefore behaves less like a black-box optimizer and more like an engineering assistant that changes its reasoning mode when the local case evidence is weak.

### 6.3 Trustworthiness, interval calibration, and selective review

KOTMA-SR accepted 82.4% of the held-out sides for direct recommendation and flagged the remainder for manual review. Among accepted sides, the within +/-0.4 recovery rate was 82.1%. These values indicate that selective recommendation is usable in the current database, but they are preliminary engineering-readiness evidence rather than deployment validation. A very conservative industrial threshold of 85% accepted within-window recovery was not reached, so the result is best interpreted as supporting engineer-supervised decision aid rather than unsupervised release. Fig. 8 visualizes the selective-recommendation and trust-calibration behavior.

The empirical intervals were reasonably calibrated at the 80% level and modestly under-covered at the 90% level. Overall, the nominal 80% interval achieved 79.4% empirical coverage with a mean width of 0.9435, while the nominal 90% interval achieved 85.3% empirical coverage with a mean width of 1.5488. Conditional calibration showed that accepted cases were better covered than manual-review cases: accepted sides achieved 82.1% coverage at the nominal 80% level and 89.3% at the nominal 90% level, whereas manual-review sides achieved 66.7% at both levels. This pattern supports the review trigger as a meaningful indicator of weaker evidence, although the manual-review subgroup is small. Conditional calibration is reported in Fig. S6.

Interval comparison with Ridge and Top-1 CBR suggests that KOTMA-SR provides competitive uncertainty summaries rather than uniquely superior calibration. At nominal 80% coverage, all three methods achieved 79.4% empirical coverage, while KOTMA-SR had a mean interval width of 0.9624, Ridge 1.1012, and Top-1 CBR 1.1424. At nominal 90% coverage, all three achieved 85.3% empirical coverage, with KOTMA-SR width 1.5594, Ridge 1.4935, and CBR 1.5112. The value of KOTMA-SR intervals is therefore not only numerical width; it is their integration with traceable case evidence and explicit review conditions. Interval comparators are shown in Fig. S9.

**Table 5. Trust and uncertainty summary.**

| Quantity | Value | Interpretation |
|---|---:|---|
| Accepted coverage | 82.4% | Fraction of held-out sides recommended without manual-review flag |
| Accepted within +/-0.4 | 82.1% | Engineering-window recovery among accepted sides |
| Overall 80% interval coverage | 79.4% | Close to nominal in current database |
| Overall 90% interval coverage | 85.3% | Modest under-coverage |
| Accepted-side 80% interval coverage | 82.1% | Accepted cases are better calibrated than review cases |
| Accepted-side 90% interval coverage | 89.3% | Close to nominal for accepted cases |
| Manual-review-side 80% interval coverage | 66.7% | Small subgroup; indicates weaker evidence |
| Manual-review-side 90% interval coverage | 66.7% | Small subgroup; supports cautious review trigger |

### 6.4 Robustness, sample efficiency, and supplementary evidence

Robustness tests showed that recommendations were stable under several simulated input perturbations. Pad missingness at 1%, 5%, and 10% produced mean recommendation shifts of 0.0000, 0.0029, and 0.0118, respectively, with a maximum shift of 0.4 at the highest level. Position noise and size noise produced no mean pressure shift in the tested settings. Varying the number of super-nodes from 40 to 100 did not change pressure recommendations, although it caused small changes in review flags at the lower super-node counts. The main sensitivity was complete shape-feature removal: when all shape information was removed, the mean recommendation shift increased to 0.1853 and the review-flag change rate reached 20.6%. This is a limitation and a useful diagnostic. The method is robust to moderate perturbations but depends on retaining meaningful pad-shape information. Robustness evidence is summarized in Fig. 9 and detailed in Fig. S5.

Sample-efficiency analysis showed that performance improved as more physical boards were available in the historical case base. With 5 training physical boards, KOTMA-SR had MAE 0.3569, compared with 0.3824 for Top-1 CBR. With 10 boards, the corresponding values were 0.3216 and 0.4118; with 15 boards, 0.2853 and 0.3333; and with 20 boards, 0.2647 and 0.3235. These results suggest that the benefit of selective structural correction becomes more useful as the case memory grows, but they also show that very small histories remain challenging.

Negative controls help rule out trivial explanations. KOTMA-SR obtained an MAE of 0.2382 in the negative-control suite, compared with 0.3471 for random historical pressure, 0.3059 for nearest pad-count only, and 0.3059 for the training median. The training median had the highest +/-0.4 rate, again confirming that window recovery alone is not a sufficient endpoint. An exploratory GNN baseline was unstable under the small sample size, with seed-level MAE ranging from 0.5382 to 0.7382 and +/-0.4 recovery between 41.2% and 50.0%. This finding should not be generalized to larger SMT datasets; it only indicates that end-to-end graph learning is not competitive in the present small-data setting. The exploratory GNN baseline is shown in Fig. S8.

Taken together, the results support a conservative industrial claim. KOTMA-SR improves retrospective first-article pressure recovery over descriptor CBR in the current database, obtains the best MAE point estimate among the evaluated methods, and provides recommendation cards with traceable evidence, empirical intervals, and review triggers. At the same time, the evidence remains retrospective, single-database, and pressure-recovery based. The appropriate conclusion is that KOTMA-SR is a promising knowledge-based decision-support framework for sparse high-reliability SMT histories, pending prospective engineer-supervised validation and external-site evaluation.

## Figure captions for the main manuscript

**Fig. 2. KOTMA-SR knowledge architecture for first-article SMT printing recommendation.** The architecture links historical PCB-side cases, descriptor memory, structural pad-field memory, sparse-tail reasoning, and an engineer-facing recommendation card. Structural evidence is not used as an unconstrained predictor; it is filtered through support auditing, bounded correction, and review-trigger logic. Source data: `Fig2_Knowledge_Architecture_SourceData.csv`.

**Fig. 3. Industrial problem formulation and executable process knowledge.** The figure defines the PCB-side recommendation object, physical-board grouping for leakage control, executable pressure range, empirical velocity policy, and recommendation-card outputs. Pressure is the active recommendation variable, while velocity is reported as an empirical process anchor with engineer override. Source data: `Fig3_Process_Knowledge_SourceData.csv`.

**Fig. 4. Structural memory construction for variable-size PCB pad fields.** Pad-level geometry is coarsened into super-nodes so that variable-size PCB sides can be compared through structural memory. FGW provides complementary structure-aware evidence for case retrieval, but it is not treated as a stand-alone optimizer. Source data: `Fig4_Structural_Memory_SourceData.csv`.

**Fig. 5. Sparse-tail support audit and bounded structural correction.** Descriptor CBR is used as the default recommendation. A structural correction is permitted only when the descriptor-supported pressure lies in a fold-local sparse tail, and the correction is bounded and rounded to the executable grid. Source data: `Fig5_Sparse_Tail_Gate_SourceData.csv`.

**Fig. 6. Physical-board grouped nested validation system.** The validation pipeline holds out physical boards, performs inner grouped tuning and calibration only on training boards, evaluates held-out PCB sides, and reports benchmark, mechanism, trust, and robustness evidence. This design avoids A/B-side leakage and supports the current-database-only retrospective claim. Source data: `Fig6_Validation_System_SourceData.csv`.

**Fig. 7. Primary retrospective pressure-recovery performance.** KOTMA-SR achieved a pressure MAE of 0.2647 versus 0.3235 for descriptor CBR, improving within +/-0.2 and within +/-0.4 recovery over CBR. The paired physical-board cluster-bootstrap interval for the MAE advantage over CBR was [0.0161, 0.1118]. Source data: `Fig7_Primary_Results_SourceData.csv`.

**Fig. 8. Trust calibration and selective recommendation behavior.** KOTMA-SR accepted 82.4% of held-out sides for direct recommendation and achieved 82.1% within +/-0.4 among accepted sides. Empirical interval coverage was 79.4% for nominal 80% intervals and 85.3% for nominal 90% intervals, indicating useful but not perfect uncertainty calibration. Source data: `Fig8_Trust_Calibration_SourceData.csv`.

**Fig. 9. Evidence matrix for claim boundaries and engineering readiness.** The matrix summarizes ablation, sparse-tail mechanism, robustness, sample-efficiency, negative-control, and claim-audit evidence. It supports a bounded retrospective decision-support claim and distinguishes supported findings from unsupported extensions such as autonomous quality optimization and universal superiority over all strong baselines. Source data: `Fig9_Evidence_Matrix_SourceData.csv`.

## Supplementary figure captions

**Fig. S1. Grouped benchmark comparison.** Extended grouped benchmark including CBR variants, tabular machine-learning baselines, structural OT variants, and exploratory comparators. KOTMA-SR has the best MAE point estimate, while paired intervals versus strong baselines such as CatBoost and Ridge do not support universal superiority.

**Fig. S2. Protocol sensitivity analysis.** Sensitivity of the observed performance pattern to validation-protocol choices. Physical-board grouped nested LOBO remains the primary protocol because it is the most conservative leakage-control setting for the current database.

**Fig. S3. Sparse-tail case evidence.** Case-level behavior of the sparse-tail gate, showing where bounded structural correction changes the descriptor CBR recommendation and where the method preserves the CBR safeguard.

**Fig. S4. Gate-threshold sensitivity.** Sensitivity of MAE, within-window recovery, correction rate, and review burden to sparse-tail support and correction-cap settings. Gate parameters are selected inside the training folds.

**Fig. S5. Robustness under input perturbations.** Recommendation shifts and review-flag changes under pad missingness, position noise, size noise, shape removal, and super-node-count changes. Shape-feature removal is the main sensitivity.

**Fig. S6. Conditional interval calibration.** Empirical interval coverage by common-support and sparse-tail strata, OOD status, review status, and pressure groups. Small strata are flagged as insufficient when appropriate.

**Fig. S7. Velocity policy.** Comparison of observed velocity with fixed and fold-mode empirical policies. The figure supports the treatment of velocity as a process anchor rather than as the main learned target.

**Fig. S8. Exploratory graph neural network baseline.** Seed-level GNN results under the current small database. The baseline is unstable and worse than KOTMA-SR, but this result is not generalized to larger SMT datasets.

**Fig. S9. Interval comparator analysis.** Comparison of interval coverage and width for KOTMA-SR, Ridge, and Top-1 CBR. KOTMA-SR intervals are competitive and integrated with traceable recommendation evidence, but they are not claimed to be uniquely calibrated.

## References cited in Sections 2-6

[1] C.-H. Lee, K.-X. Lin, and C.-W. Chou, "Surrogate-based optimization framework for enhancing SMT process quality and productivity in electronics manufacturing services," *The International Journal of Advanced Manufacturing Technology*, vol. 136, pp. 5103-5122, 2025. doi:10.1007/s00170-025-15032-w.

[2] Q. Zhang, P. Li, Y.-B. Zhao, and Y. Kang, "Human-on-the-Loop Control in Surface Mount Technology via Deep Reinforcement Learning," *IET Control Theory & Applications*, vol. 19, no. 1, e70028, 2025. doi:10.1049/cth2.70028.

[3] J. P. Sousa, A. Sousa, F. Brueckner, L. P. Reis, and A. Reis, "Human-in-the-loop Multi-objective Bayesian Optimization for Directed Energy Deposition with in-situ monitoring," *Robotics and Computer-Integrated Manufacturing*, vol. 92, 102892, 2025. doi:10.1016/j.rcim.2024.102892.

[4] S. Wang, P. Zou, X. Gong, M. Song, J. Peng, and R. J. Jiao, "Visual analytics and intelligent reasoning for smart manufacturing defect detection and judgement: A meta-learning approach with knowledge graph embedding case-based reasoning," *Journal of Industrial Information Integration*, vol. 37, 100536, 2024. doi:10.1016/j.jii.2023.100536.

[5] L. Guo, T. Hu, L. Dong, and S. Ma, "Ontology and production rules-based dynamic knowledge base construction methodology for machining process," *Journal of Manufacturing Systems*, vol. 77, pp. 1027-1044, 2024. doi:10.1016/j.jmsy.2024.11.006.

[6] S. Liu et al., "A dynamic updating method of digital twin knowledge model based on fused memorizing-forgetting model," *Advanced Engineering Informatics*, vol. 57, 102115, 2023. doi:10.1016/j.aei.2023.102115.

[7] D. Li et al., "Trustworthy AI for human-centric smart manufacturing: A survey," *Journal of Manufacturing Systems*, vol. 78, pp. 308-327, 2025. doi:10.1016/j.jmsy.2024.11.020.

[8] Y. Zhong et al., "Human-centric integrated safety and quality assurance in collaborative robotic manufacturing systems," *CIRP Annals*, vol. 73, no. 1, pp. 345-348, 2024. doi:10.1016/j.cirp.2024.04.008.

[9] R. X. Gao et al., "Artificial Intelligence in manufacturing: State of the art, perspectives, and future directions," *CIRP Annals*, vol. 73, no. 2, pp. 723-749, 2024. doi:10.1016/j.cirp.2024.04.101.

[10] J. Jeon et al., "ChatCNC: Conversational machine monitoring via large language model and real-time data retrieval augmented generation," *Journal of Manufacturing Systems*, vol. 79, pp. 504-514, 2025. doi:10.1016/j.jmsy.2025.01.018.

[11] D. H. Nguyen and K. Tsuda, "On a linear fused Gromov-Wasserstein distance for graph structured data," *Pattern Recognition*, vol. 138, 109351, 2023. doi:10.1016/j.patcog.2023.109351.

[12] X. Ma, X. Chu, Y. Wang, Y. Lin, J. Zhao, L. Ma, and W. Zhu, "Fused Gromov-Wasserstein Graph Mixup for Graph-level Classifications," in *Advances in Neural Information Processing Systems 36*, 2023.

[13] J. Tang, X. Zhao, L. Kong, X. Zhou, and J. Li, "Fused Gromov-Wasserstein Alignment for Graph Edit Distance Computation and Beyond," *Proceedings of the VLDB Endowment*, vol. 18, no. 10, pp. 3641-3654, 2025. doi:10.14778/3748191.3748221.

[14] M. Piening and R. Beinert, "A Novel Sliced Fused Gromov-Wasserstein Distance," in *Proceedings of the AAAI Conference on Artificial Intelligence*, vol. 40, no. 29, pp. 24828-24836, 2026. doi:10.1609/aaai.v40i29.39669.

[15] C. Cao, Y. Zhang, Y. Ai, and Q. Zhang, "Unsupervised feature selection via unifying distribution alignment and structure preservation," *Information Fusion*, vol. 126, 103544, 2026. doi:10.1016/j.inffus.2025.103544.

[16] H. Feng, Y. Sun, X. Hu, Z. Li, C. Chen, B. Wang, and Y. Wang, "Flexible exploration: A hyperspectral image classification framework based on dynamic scale and graph optimal transport," *Information Fusion*, vol. 128, 103962, 2026. doi:10.1016/j.inffus.2025.103962.

[17] J. C. Cresswell, Y. Sui, B. Kumar, and N. Vouitsis, "Conformal Prediction Sets Improve Human Decision Making," in *Proceedings of the 41st International Conference on Machine Learning*, PMLR 235, pp. 9439-9457, 2024.

[18] D. Zhang, A. Chatzimparmpas, N. Kamali, and J. Hullman, "Evaluating the Utility of Conformal Prediction Sets for AI-Advised Image Labeling," in *Proceedings of the 2024 CHI Conference on Human Factors in Computing Systems*, 2024. doi:10.1145/3613904.3642446.

[19] G. De Toni, N. Okati, S. Thejaswi, E. Straitouri, and M. Gomez-Rodriguez, "Towards Human-AI Complementarity with Prediction Sets," in *Advances in Neural Information Processing Systems 37*, 2024.

[20] Q. Zhao et al., "HAIL: Human-in-the-loop Assembly Imitation Learning System," *Journal of Manufacturing Systems*, vol. 86, pp. 991-1006, 2026. doi:10.1016/j.jmsy.2026.04.020.

[21] K. Hu, X. Yao, F. Qiao, W. Shen, H. Wu, and W. Yang, "Digital twin-integrated bandit learning for LRM-driven multi-agent resilient production scheduling," *Journal of Manufacturing Systems*, vol. 86, pp. 50-66, 2026. doi:10.1016/j.jmsy.2026.02.021.

[22] A. Heddoub, L. Homri, and A. Siadat, "Class-conditional conformal prediction with discriminant-analysis backbones for reliable open-set fault diagnosis in safety-critical industrial systems," *Journal of Process Control*, vol. 161, 103701, 2026. doi:10.1016/j.jprocont.2026.103701.

[23] M. S. Bajestani, D. Mun, and D. B. Kim, "Human-in-the-loop and large language models in smart manufacturing: Current applications, challenges, and perspectives," *Journal of Manufacturing Systems*, vol. 86, pp. 913-941, 2026. doi:10.1016/j.jmsy.2026.04.027.

[24] L. Zhou et al., "Towards trustworthy AI in Industry 5.0: Ante-hoc interpretability with deep learning," *Computers & Industrial Engineering*, vol. 213, 111805, 2026. doi:10.1016/j.cie.2026.111805.

[25] S. Liu, J. Xie, X. Wang, and X. Qiao, "You are my eyes: Integrating human intelligence and LLMs in AR-assisted motion planning for industrial mobile robots," *Robotics and Computer-Integrated Manufacturing*, vol. 98, 103174, 2026. doi:10.1016/j.rcim.2025.103174.

[26] C. Chen et al., "Leveraging large language models for smart manufacturing: Reviews, enablers, challenges, and opportunities," *Journal of Manufacturing Systems*, vol. 85, pp. 593-612, 2026. doi:10.1016/j.jmsy.2026.02.008.

[27] J. Leng et al., "AIGC-empowered smart manufacturing: Prospects and challenges," *Robotics and Computer-Integrated Manufacturing*, vol. 97, 103076, 2026. doi:10.1016/j.rcim.2025.103076.

[28] T. Ouyang, Y. Seo, and I. Echizen, "Textual out-of-distribution (OOD) detection for LLM quality assurance," *Knowledge-Based Systems*, vol. 310, 112975, 2025. doi:10.1016/j.knosys.2025.112975.

[29] Y. Hu et al., "Out-of-distribution monocular depth estimation with local invariant regression," *Knowledge-Based Systems*, vol. 319, 113518, 2025. doi:10.1016/j.knosys.2025.113518.

[30] C. A. Steed and N. Kim, "Deep active-learning based model-synchronization of digital manufacturing stations using human-in-the-loop simulation," *Journal of Manufacturing Systems*, vol. 70, pp. 436-450, 2023. doi:10.1016/j.jmsy.2023.08.012.

[31] A. Aamodt and E. Plaza, "Case-based reasoning: Foundational issues, methodological variations, and system approaches," *AI Communications*, vol. 7, no. 1, pp. 39-59, 1994.

[32] G. Peyre, M. Cuturi, and J. Solomon, "Gromov-Wasserstein averaging of kernel and distance matrices," in *Proceedings of the 33rd International Conference on Machine Learning*, PMLR 48, pp. 2664-2672, 2016.

[33] T. Vayer, L. Chapel, R. Flamary, R. Tavenard, and N. Courty, "Fused Gromov-Wasserstein distance for structured objects," *Algorithms*, vol. 13, no. 9, 212, 2020. doi:10.3390/a13090212.

[34] G. Shafer and V. Vovk, "A tutorial on conformal prediction," *Journal of Machine Learning Research*, vol. 9, pp. 371-421, 2008.

[35] B. Efron and R. J. Tibshirani, *An Introduction to the Bootstrap*. New York: Chapman & Hall/CRC, 1993.

[36] T. Chen and C. Guestrin, "XGBoost: A scalable tree boosting system," in *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, pp. 785-794, 2016.

[37] G. Ke et al., "LightGBM: A highly efficient gradient boosting decision tree," in *Advances in Neural Information Processing Systems 30*, 2017.

[38] L. Breiman, "Random forests," *Machine Learning*, vol. 45, pp. 5-32, 2001.

[39] L. Prokhorenkova et al., "CatBoost: Unbiased boosting with categorical features," in *Advances in Neural Information Processing Systems 31*, 2018.

