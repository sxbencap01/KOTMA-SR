Structure-Aware Case-Based First-Article Pressure Setting for Solder-Paste Printing under Sparse Process Histories

Xin Su1,2,*, Yichen Liu 1


## 1 The School of Automotive Engineering, Chengdu Aeronautic Polytechnic University, Chengdu 610100, China


## 2 School of Computer Science and Software Engineering, Southwest Petroleum University, Chengdu 610500, China

E-mail addresses: Xin Su(2300018@cap.edu.cn)


## Abstract: First-article pressure setting in solder-paste printing is a practical manufacturing-process problem in high-mix and small-batch surface-mount technology (SMT) production. For a newly introduced printed circuit board (PCB) side, engineers must select an executable initial pressure before target-board inspection feedback has accumulated, while repeated trial printing is undesirable in high-reliability production. This study proposes KOTMA-SR, a knowledge-guided process-recommendation method for first-article solder-paste printing pressure setting under sparse process histories. The method retains descriptor-based case-based reasoning (CBR) as an auditable process-knowledge reuse path, constructs structural memory from variable-size PCB pad fields through super-node coarsening and fused Gromov-Wasserstein (FGW) matching, and activates bounded structural correction only when descriptor-level pressure support is weak. The output is an engineer-facing recommendation card containing the recommended pressure, empirical velocity anchor, retrieved process cases, empirical uncertainty intervals, and review triggers. The method is evaluated on an anonymized industrial aerospace SMT database containing 34 PCB sides from 21 physical boards using physical-board grouped nested leave-one-board-out validation. KOTMA-SR reduced pressure mean absolute error (MAE) from 0.3235 for descriptor CBR to 0.2647, corresponding to an 18.2% reduction, with a physical-board cluster-bootstrap MAE-advantage interval of [0.0161, 0.1118]. It accepted 82.4% of held-out sides for direct recommendation and achieved 82.1% within ?0.4 among accepted sides. The results support a bounded retrospective process-recommendation claim for engineer-supervised first-article preparation. They do not establish autonomous process control, defect reduction, solder-deposit quality optimization, or external deployment readiness.

## Keywords: Solder-paste printing; first-article pressure setting; manufacturing-process knowledge reuse; case-based reasoning; structural pad-field matching; process recommendation.


## 1. Introduction

Solder-paste printing is one of the most influential early operations in SMT assembly because it determines the initial solder deposit formed on PCB pads and constrains the quality window of placement and reflow. Printing pressure affects the contact condition among the squeegee, stencil, solder paste, and PCB surface. Insufficient pressure may lead to incomplete aperture filling or unstable paste transfer, whereas excessive pressure may cause paste smearing, stencil wear, or unnecessary process disturbance. Therefore, first-article pressure setting is not only a numerical parameter-selection task but also a practical process-preparation decision. This interpretation is consistent with assembly and acceptability standards that treat stencil printing, soldered assembly quality, and process verification as linked manufacturing concerns [42,43]. In high-reliability and high-mix production, including aerospace electronics production, the process engineer must select an executable initial setting for a new PCB side while avoiding unnecessary trial printing, material consumption, and uncontrolled process excursions. Many historical production databases record one validated engineering setting for each PCB side rather than a complete response surface over alternative pressure-speed combinations.

The process nature of the problem is also reflected in practical SMT guidance. Stencil design, soldering-process setup, land-pattern requirements, and package-specific assembly implementation all influence whether a recommended setting is meaningful on the shop floor [47,48]. Electronics assembly handbooks further emphasize that soldering practice is constrained by equipment capability, board design, materials, and inspection requirements rather than by a single isolated parameter [49,50]. KOTMA-SR is therefore positioned as a first-article process-preparation aid, not as a replacement for standard inspection, certification, or release decisions.

Recent SMT studies have advanced surrogate optimization and human-supervised control. Neural-network surrogates combined with metaheuristic search can reduce the number of physical experiments for SMT process improvement [1], while human-on-the-loop deep reinforcement learning can adapt process control when iterative feedback is available [2]. These methods are valuable in mass-production SMT PCB processes, where a sufficiently large number of process trials and inspection results may support repeated parameter iteration and optimization. However, aerospace and other high-reliability PCB manufacturing often exhibits multi-product, small-batch, mixed-line production characteristics, where extensive trial printing for each newly introduced PCB side is undesirable or impractical. In this setting, the practical goal is not to search for a globally optimal parameter combination through repeated experiments, but to rapidly obtain a feasible first-article process setting for engineering verification. The problem considered in this paper is narrower but common in industrial practice: before feedback from the target PCB side is available, how can the system recommend a plausible first-article pressure by reusing prior engineering experience and showing the limits of that evidence.

Historical cases provide a natural foundation for such a decision-support system. Case-based reasoning (CBR) retrieves similar past problems and reuses their validated solutions [3], which matches the way engineers often reason about new PCB introductions. However, descriptor-level similarity alone may be insufficient for PCB comparison. Two PCB sides can have similar pad counts, board dimensions, and aperture statistics while differing in spatial pad organization and local density. Conversely, a purely structural model may be difficult to audit and may overreact in sparse histories. This creates an industrial design tension: the recommendation system should use structural evidence when it helps, but should not discard traceable case evidence.

For first-article process setting, recommendation evidence must be inspectable. A useful system should expose the supporting historical cases, indicate whether the target PCB side is weakly covered by prior experience, quantify empirical uncertainty, and identify cases that require engineer review. This view is consistent with recent human-centric manufacturing studies that emphasize supervised process support rather than unconditional automation [4,5]. It is also consistent with prediction-set and conformal-prediction research showing that uncertainty information can improve human decisions when it is presented as an actionable aid [6,7].

This paper proposes KOTMA-SR, a knowledge-guided process-recommendation method with sparse-tail reasoning. The method keeps descriptor CBR as the auditable default, builds structural memory from PCB pad fields using super-node coarsening and fused Gromov-Wasserstein (FGW) matching [8,9], and activates bounded structural correction only when descriptor retrieval falls into a weakly supported pressure tail. Each output is packaged as a recommendation card containing the proposed pressure, empirical velocity guidance, neighbors, weights, intervals, and review reasons. Figure 1 contrasts this support-audited reasoning strategy with conventional descriptor CBR under sparse process histories.

Figure 1 Conceptual contrast between descriptor-only CBR and KOTMA-SR for first-article solder-paste printing pressure setting under sparse process histories.

Conventional descriptor CBR reuses pressure from the nearest descriptor-similar historical case, which is auditable but may miss pad-field structure and weakly supported sparse-tail cases. KOTMA-SR retains descriptor CBR as a safeguard, adds FGW-based structural memory, and activates bounded correction only when descriptor support is weak. The output combines pressure, empirical uncertainty, and review status. The reported values summarize retrospective pressure-recovery evidence and do not imply autonomous solder-deposit quality optimization or external deployment validation.

The contributions are threefold. First, at the problem level, the paper formulates high-reliability first-article solder-paste printing pressure setting as sparse historical case reuse under bounded evidence rather than as conventional closed-loop optimization. Second, at the method level, it proposes KOTMA-SR as a manufacturing-process knowledge reuse workflow that combines descriptor CBR, structure-aware pad-field matching, sparse-tail support auditing, bounded correction, empirical intervals, and review-aware outputs. Third, at the validation level, it evaluates the framework with physical-board grouped nested leave-one-board-out validation and reports benchmark, ablation, calibration, robustness, sample-efficiency, negative-control evidence. The results support a bounded process-recommendation claim within the current historical database and identify the additional evidence still needed for prospective deployment.


## 2. Related work

This review is organized around four aspects relevant to first-article solder-paste printing pressure setting: process modelling, historical process-case reuse, structure-aware PCB comparison, and engineer-supervised recommendation. The purpose is not to review optimal transport or artificial intelligence exhaustively, but to clarify why sparse SMT process histories require a conservative process-recommendation method.

## 2.1 Solder-paste printing process modelling and parameter setting

Research on solder-paste printing has moved from empirical trial adjustment toward data-supported process recommendation and optimization. Recent studies typically model printing pressure, squeegee speed, stencil geometry, aperture

characteristics, and paste-related factors as controllable variables associated with deposit quality or process productivity. This view is compatible with industry guidance in which stencil design and assembly acceptability are treated as process-control issues rather than purely geometric design issues [42,43]. For example, Lee et al. developed a neural-network surrogate coupled with particle-swarm optimization to improve SMT process quality and productivity with fewer physical trials. Zhang et al. further formulated SMT process control as a human-on-the-loop deep-reinforcement-learning problem, illustrating how inspection feedback can support adaptive parameter adjustment [2]. Similar feedback-efficient optimization ideas have also been reported in adjacent manufacturing processes, where human-in-the-loop Bayesian optimization is used to reduce the number of costly process experiments [10].

However, most optimization-oriented studies assume that target-board experiments, inspection feedback, or online measurements are available during model updating or parameter search. This assumption is not always compatible with first-article SMT printing for high-mix, high-reliability products, where production is typically multi-product, small-batch, and mixed-line. In these settings, a large number of historical process records exist, but they are rarely leveraged to rapidly generate a feasible initial parameter set for new PCB sides. Practical SMT references also emphasize that process setup is constrained by soldering practice, board design, component packages, and certification-oriented assembly rules [51,52]. The practical objective is therefore not unconstrained global optimization, but cold-start recommendation: transferring validated settings from historical PCBs, judging structural relevance of retrieved cases, and indicating when human engineer review is required. This gap motivates a case-centered, constraint-aware recommendation framework tailored for SMT printing.

## 2.2 Historical process-case reuse in manufacturing

Case-based reasoning (CBR) organizes historical problem-solution pairs as reusable knowledge. For a new task, similar cases are retrieved, prior solutions are reused or adapted, and validated experience can be retained for future decisions [3]. This logic is attractive in manufacturing because process knowledge is often distributed across historical records, engineering rules, and context-dependent judgments. Recent studies have combined case retrieval with knowledge-graph embeddings for manufacturing inspection [11], developed dynamic machining-process knowledge bases that integrate ontology, production rules, querying, CBR, and rule-based reasoning [12] , and proposed knowledge-model updating mechanisms for digital-twin manufacturing environments [13]. These studies illustrate a broader move from isolated predictive models toward traceable knowledge-guided decision support.

Despite the accumulation of extensive historical manufacturing records, such records are often underutilized for systematic process recommendation, especially when new products must be introduced under sparse target-specific evidence. Descriptor-level CBR is useful in first-article SMT because engineers can inspect which historical PCBs support a proposed setting. However, tabular descriptors inevitably compress information: two PCBs may have similar board dimensions, pad counts, or aperture statistics while differing in local pad density and spatial organization. The limitation is not that descriptor-based retrieval lacks value, but that when the historical case base is sparse, structurally different boards may be erroneously treated as similar.

## 2.3 Structure-aware comparison of variable-size PCB pad fields

A PCB pad field cannot be fully represented by an ordinary fixed-length vector. Different boards contain variable numbers of pads, heterogeneous local geometries, and no natural one-to-one pad correspondence. Optimal transport (OT) provides a principled family of tools for comparing heterogeneous objects. Wasserstein formulations compare feature distributions, Gromov-Wasserstein (GW) formulations compare intra-object relationships [8], and fused Gromov-Wasserstein (FGW) formulations jointly account for attributes and structure [9]. Recent research has improved the efficiency and applicability of these ideas for graph-structured data. Nguyen and Tsuda proposed linear FGW to approximate graph similarity more efficiently [14]. Ma et al. used FGW to construct graph mixups while accelerating optimization [15]. Tang et al. transformed graph-edit-distance computation into an FGW-alignment problem [16]. Piening and Beinert proposed a sliced FGW formulation that lowers computational burden while retaining useful invariance properties [17]. Outside manufacturing, recent studies have also used GW alignment for structure-preserving feature selection [18] and graph OT for hyperspectral representation learning [19]. These cross-domain examples are cited as technical evidence for structure-aware comparison, not as direct evidence for PCB process transfer.

## 2.4 Engineer-supervised first-article process recommendation

In high-reliability manufacturing, a recommendation system is incomplete if it outputs only a point estimate. Engineers also need to know which historical cases support a recommendation, whether the proposed value lies within executable limits, whether the input is weakly supported by prior experience, and when manual review is required. Recent manufacturing research increasingly frames intelligent methods as supervised and human-centric process aids rather than replacements for engineering judgment. Surveys and applications have examined human-centric and review-aware manufacturing methods [20], integrated safety and quality assurance [21], broader manufacturing intelligence opportunities and limitations [22], conversational access to real-time manufacturing data [23], human-in-the-loop assembly learning [4], human-cyber collaborative scheduling under uncertainty [24], and human-supervised or knowledge-enhanced manufacturing decisions [5,25-28].

Uncertainty information should also change system behavior. Conformal prediction is relevant because it produces sets or intervals that expose uncertainty rather than forcing a single confident output [29]. Recent tutorials and distribution-free prediction methods provide useful methodological background for empirical intervals and prediction sets [37,38]. Cresswell et al. showed that conformal prediction sets can improve human decision making [6]. Zhang et al. examined their utility in machine-assisted image labeling [7], while De Toni et al. studied prediction sets designed for human decision support [30]. In an industrial setting, class-conditional conformal prediction has been used to support transparent uncertainty quantification and rejection under open-set fault conditions [31]. Related jackknife-style predictive inference and OOD-detection work also motivates reporting uncertainty and review triggers rather than only point predictions [39,40]. These studies are adjacent methodological references rather than direct validations of the SMT workflow.

Prior work has advanced SMT optimization, manufacturing knowledge reuse, structural matching, and engineer-supervised recommendation largely as separate lines of research. Their intersection remains less developed for cold-start first-article SMT pressure recommendation under sparse historical coverage.

Compared with optimization-driven SMT studies, KOTMA-SR contributes a manufacturing-process recommendation workflow that leverages accumulated historical records, combines case-based reasoning, structure-aware pad-field evidence, bounded reasoning, and uncertainty-aware human review, aligning with first-article process preparation rather than autonomous process optimization.


## 3. Problem formulation and data scope

The industrial problem addressed in this study is first-article recommendation of solder-paste printing pressure for a newly introduced PCB side in high-reliability SMT production. In such production, an engineer needs an executable initial setting before repeated target-board trial printing has accumulated sufficient inspection feedback. The task is therefore different from closed-loop process optimization, in which repeated target-process measurements can be used to search for an optimum. It is also different from solder-joint quality prediction, because the present database records one historically executed process setting for each PCB side rather than a counterfactual response surface over alternative pressure-speed combinations. This distinction is important for industrial decision support: the proposed system recommends a historically plausible first setting for engineer-supervised verification; it does not claim autonomous process control or defect-rate optimization. The problem setting and executable manufacturing assumptions are summarized in Figure 2. Although SPI measurements and defect outcomes are essential for process validation after first-article printing, they are not available before the initial pressure recommendation is made for a newly introduced PCB side. Therefore, the problem studied here is the pre-inspection recommendation of an executable first-article pressure, rather than post-inspection solder-deposit quality optimization. The historical executed pressure is used as the retrospective reference because it represents the pressure accepted by engineers for production preparation in the available records.

Figure 2 Industrial problem formulation and executable process knowledge.

The figure defines the PCB-side recommendation object, physical-board grouping for leakage control, executable pressure range, empirical velocity policy, and recommendation-card outputs. Pressure is the active recommendation variable, while velocity is reported as an empirical process anchor with engineer override.

Each case in the historical memory is represented as a PCB-side problem paired with a validated printing-pressure setting and associated process metadata. A PCB side is treated as the recommendation unit because the two sides of a physical board may differ in pad layout, component distribution, and production requirements. However, the two sides are not treated as independent physical products during validation. When a physical board has both A and B sides, both sides are held out together in the outer evaluation fold. This design prevents a model from learning one side of a board and then appearing to generalize to the other side through shared board-level identity or geometry. Thus, the evaluation unit is the PCB side, while the leakage-control unit is the physical board.

Let the historical case base be denoted by

\[
\mathcal{D}=\{(b_i, x_i, G_i, p_i, v_i)\}_{i=1}^{N}.
\]

Here, \(b_i\) is the physical-board identifier, \(x_i\) is the fixed-length descriptor vector, \(G_i\) is the super-node structural representation of the pad field, \(p_i\) is the historically executed first-article printing pressure, and \(v_i\) is the executed squeegee velocity. For a target PCB side \(q\), the system observes \(x_q\) and \(G_q\), but not the target outcome under alternative parameter values. It outputs a pressure recommendation \(\hat{p}_q\), an empirical velocity suggestion \(\hat{v}_q\), uncertainty intervals, traceable neighboring cases, and review triggers. The primary endpoint is the absolute recovery error \(|\hat{p}_q-p_q|\), where \(p_q\) is the historically executed first-article pressure for the held-out side. This endpoint is interpreted as retrospective recovery of engineering practice, not proof that the recovered pressure is globally optimal. Table 1 defines the notation and claim boundary used throughout the method and evaluation.

Table 1 Problem notation and claim boundary.

The executable action space follows the observed engineering setting range in the current database. Pressure recommendations are restricted to the feasible pressure interval and rounded to a 0.1 grid before evaluation. This choice reflects industrial executability: a recommendation that cannot be directly set on the equipment is less useful than a slightly less flexible but immediately executable value. Velocity is handled as an empirical policy because the available records show that it is largely anchored by historical shop-floor practice, with engineer override retained for exceptional cases. Consequently, pressure is the active recommendation target, while velocity is reported as contextual process guidance. The velocity evidence is reported in Figure 3.

Figure 3 Velocity policy.

The figure compares the observed velocity settings with fixed and fold-mode empirical policies. The result supports treating velocity as a process anchor and contextual recommendation field rather than as the main learned target.

The current database contains 34 independent PCB-side records from 21 physical boards, as summarized in Table 2. The database does not contain a reliable acquisition timestamp, production-site field, or prospective deployment log that would support a temporal split or external validation. The study therefore adopts a current-database-only retrospective design and states this boundary explicitly. This limitation does not justify random side-level splitting; instead, it motivates physical-board grouped validation and a conservative decision-support claim. Similar caution is recommended in human-centric manufacturing intelligence, where system outputs must remain interpretable, reviewable, and aligned with operational constraints rather than presented as unconditional automation [4,5,20].

Table 2 Dataset scope of the current historical SMT database.


## 4. KOTMA-SR process-recommendation method

KOTMA-SR is a knowledge-guided process-recommendation method designed for sparse SMT process histories. Its central principle is conservative adaptation: descriptor-based CBR remains the auditable default, while structural evidence is used only when the local historical support for the descriptor-nearest recommendation is weak. This design follows the CBR view that historical cases constitute reusable problem-solution knowledge [3], but extends it for variable-size PCB geometry and engineering review. Rather than treating structural matching as an unconstrained predictor, KOTMA-SR uses it as conditional evidence within a support-audited and bounded process-recommendation workflow. In contrast to black-box regression, the system must show which historical boards support a recommendation, why a correction was or was not applied, and when the decision should be escalated for human review. The layered architecture of the process-recommendation method is shown in Figure 4.

Figure 4 Layered KOTMA-SR architecture for first-article solder-paste printing pressure recommendation.

PCB geometry, process-policy constraints, and historical PCB-side cases are converted into descriptor memory and structural pad-field memory. Descriptor CBR provides the auditable default, whereas FGW-informed structural evidence is activated only for bounded correction under weak local support. The review gate adds empirical intervals, evidence status, and review triggers before returning an engineer-facing recommendation card. Fold-dependent scaling, tuning, support auditing, and interval calibration use training physical boards only.

To support reproducibility, the method is summarized through core methodological rules and fold-local parameter settings rather than through globally fitted parameters. All descriptor scaling, retrieval thresholds, correction caps, and empirical intervals are selected or calibrated within the training boards of each validation fold. The main rules are summarized in Table 3.

Table 3 Core methodological rules and fold-local parameter settings of KOTMA-SR.

Table 3 records the reproducible decision rules used by KOTMA-SR, including descriptor construction, fold-local scaling, descriptor-neighborhood retrieval, super-node construction, FGW matching, sparse-tail gating, bounded correction, interval calibration, and review-trigger logic.

## 4.1 Descriptor case memory and process-neighbor retrieval

The first memory layer is a descriptor case memory. For each PCB side, the system constructs a fixed-length descriptor vector from board-level and pad-field summary information, including pad count, board dimensions, pad-area statistics, aperture-ratio statistics, aspect-ratio statistics, and spatial spans. These descriptors summarize the board scale, pad-field density, aperture-related printing characteristics, pad-shape distribution, and spatial coverage of the PCB side. Descriptors are standardized within each training fold to avoid test-fold information leakage. Specifically, the descriptor scaler is fitted only on the outer-training physical boards and then applied to the held-out target side. Given a target PCB side, the system retrieves similar historical cases according to descriptor distance. The nearest descriptor case supplies the CBR safeguard recommendation, while the top-ranked neighborhood supplies traceable evidence and local support statistics. Here, the nearest case defines the auditable default pressure, whereas the retrieved neighborhood provides supporting evidence for support auditing and review decisions.

Descriptor-level retrieval is deliberately retained even though it compresses the pad field. In an industrial recommendation workflow, a method that can identify a small set of similar historical boards is easier to audit than a purely parametric model. The retrieved cases allow engineers to inspect whether the recommendation is supported by recognizable prior PCB introductions rather than by an opaque regression surface. The limitation is that descriptor similarity may ignore local geometry and layout organization. Therefore, descriptor CBR is treated as the default evidence channel, not the only evidence channel. When descriptor-level evidence is weak or potentially misleading, structural pad-field memory is introduced as complementary evidence rather than as a replacement for traceable case retrieval.

## 4.2 Structural pad-field memory and process interpretation

The second memory layer represents each PCB side as a structural pad-field object. Direct pad-to-pad matching is computationally expensive and unstable because different PCB sides have different numbers of pads and no natural pad index correspondence. This issue is important for SMT recommendation because local pad density, pad-size distribution, aperture-related features, and spatial organization may affect how historical printing-pressure experience transfers across PCB sides. The method therefore coarsens each pad field into super-nodes using position, pad-size, and local-density information. The super-node representation is a structural summary of the original pad field rather than a replacement of PCB geometry: it preserves coarse spatial organization while reducing matching cost and improving comparison stability. This structural-memory construction is illustrated in Figure 5. For manufacturing-process readers, the process interpretation is as important as the matching formulation. Pad count and board span reflect the spatial extent of printing and potential squeegee-contact loading. Local pad density may affect local paste-transfer stability. Pad area, aperture ratio, and aspect ratio reflect release difficulty and deposit sensitivity. A global descriptor may miss local dense regions or spatial organization; structural evidence therefore helps judge whether a pressure successfully used on one PCB side is transferable to another. The method does not model solder-paste rheology or stencil release physics directly. It uses structural similarity as process-relevance evidence for historical case reuse.

Figure 5 Structural memory construction for variable-size PCB pad fields.

Raw pad-level geometry is summarized into physics-aware super-nodes, preserving coarse spatial organization while reducing matching cost. FGW matching compares query and historical PCB-side structures by jointly considering node attributes and intra-object geometry. The resulting structural similarity is used as complementary evidence for sparse-tail reasoning, not as a stand-alone optimizer.

Structural similarity is then computed using a fused Gromov-Wasserstein matching signal. GW compares relational structure between objects, whereas FGW combines node attributes with internal relational geometry [8,9]. This formulation is suitable for PCB-side comparison because process transfer may depend on both local pad attributes and global layout organization, while different PCB sides have variable numbers of pads and no natural one-to-one pad correspondence. Computational OT research provides the numerical background for regularized transport and efficient implementation [45,46]. Recent work has shown that FGW and related graph OT formulations can support graph similarity, graph mixup, graph-edit-distance approximation, and efficient sliced variants [16,17]. OT has also been used for domain adaptation, which is conceptually related to transferring information across heterogeneous objects, although the present study uses OT only for structural case evidence rather than supervised domain adaptation [54]. In this study, FGW is not proposed as a new distance or used as an unconstrained pressure predictor. It is used as complementary structural evidence inside a bounded industrial reasoning architecture, where structural matching can inform sparse-tail correction but cannot replace descriptor CBR as the auditable default.

## 4.3 Sparse-tail support audit and bounded process correction

The key decision rule in KOTMA-SR is the sparse-tail support audit. After descriptor retrieval, the system examines whether the descriptor-CBR pressure is sufficiently supported by nearby historical cases within the current training fold. This audit is fold-local: only the outer-training physical boards are used to estimate pressure support, and no held-out target information enters the support decision. If the descriptor neighborhood provides sufficient support, the recommendation remains the descriptor-CBR pressure. If the descriptor-CBR pressure has fewer than the minimum supported pressure cases or falls outside the fold-local supported pressure range, it is treated as a sparse-tail recommendation. In that case, the system allows a bounded correction informed by structural neighbors.

The correction rule is deliberately conservative. The final pressure starts from the descriptor-CBR pressure. When the sparse-tail gate is triggered, the structural estimate is allowed to adjust the CBR pressure only within a fold-selected correction cap. The corrected value is then rounded to the executable 0.1 pressure grid and clipped to the feasible pressure range. Thus, structural memory does not perform a new unconstrained pressure search; it only provides limited evidence for adjusting a weakly supported CBR recommendation. The gate logic is illustrated in Figure 6.

Figure 6 Sparse-tail support audit and bounded correction rule.

Descriptor CBR is used as the default recommendation path. A structural correction is permitted only when the descriptor-supported pressure is weakly supported within the training fold or falls into a sparse pressure tail. The correction is capped, rounded to the executable 0.1 pressure grid, and passed to the review-aware output logic.

This rule is intentionally asymmetric. Structural evidence is not allowed to override CBR everywhere, because unconstrained structural matching can be unreliable in small historical databases. Instead, the method asks a narrower question: when descriptor CBR is likely to rely on weak local evidence, does the structural memory provide enough additional evidence to make a small, bounded adjustment. This selective design is consistent with conservative process recommendation: method behavior changes only under weak evidence, while supported historical cases remain traceable and auditable. The case-level gains and pressure-bin behavior of this rule are reported in the mechanism analysis section rather than used to define the method.

## 4.4 Recommendation card, empirical intervals, and review triggers

For each target PCB side, KOTMA-SR produces a recommendation card rather than only a point estimate. The card includes the recommended pressure, the empirical velocity suggestion, the descriptor-CBR pressure, any structural correction, the retrieved neighbors and their weights, uncertainty intervals, runtime, and review reasons. The card is intended as an engineer-facing decision artifact: it shows not only what pressure is recommended, but also which historical cases support the recommendation, whether structural correction was used, and why manual review may be required. Review triggers are activated when evidence is weak, the target appears outside the training-fold descriptor coverage, the interval is wide, or the sparse-tail rule indicates that the recommendation depends on limited local support. These triggers implement selective recommendation behavior by separating routine cases from cases that require additional engineering inspection.

The uncertainty intervals are empirical intervals calibrated only from training-fold residuals inside the nested validation protocol. They are calibrated under the same leakage-safe protocol used for model selection and do not use residuals from the held-out target side or its paired physical-board side. They are not presented as certified safety bounds. Their function is operational: they help engineers distinguish routine recommendations from cases requiring extra inspection. This aligns with conformal and prediction-set research showing that uncertainty sets can improve human decision making when they are displayed as decision aids rather than hidden model diagnostics.

## 4.5 Algorithmic summary and leakage controls

For each outer fold, all preprocessing, descriptor scaling, support thresholds, calibration residuals, and hyperparameter choices are fit using only the training physical boards. For a held-out target side, KOTMA-SR retrieves descriptor neighbors, computes or looks up structural similarities to training cases, audits local pressure support, either keeps the CBR safeguard or applies a bounded structural correction, rounds the final pressure to the executable grid, and generates the recommendation card. No held-out side, its paired physical-board side, or its residual enters tuning, scaling, or interval calibration. The procedure is summarized in Algorithm 1 and evaluated as a leakage-safe engineer-facing decision-support pipeline rather than as an oracle fitted on all available records.

Algorithm 1. KOTMA-SR recommendation for one outer validation fold.


## 5. Experimental design

The experimental design follows the industrial scope defined above. All experiments use the current historical database and evaluate retrospective pressure recovery for 34 PCB sides from 21 physical boards. The primary protocol is physical-board grouped nested leave-one-board-out validation. In each outer fold, one physical board is held out; if both A and B sides are present, both are excluded from the training data. Hyperparameters are selected in an inner grouped validation loop over the remaining boards. The final model for that fold is then refit on the outer-training boards and evaluated on the held-out side or sides. This protocol is designed to prevent A/B-side leakage caused by shared board-level identity, geometry, or production context. It is stricter than random side-level splitting and better matches the intended use case of recommending settings for unseen physical boards. The grouped validation system and its leakage barriers are summarized in Figure 7. Protocol-sensitivity results are reported later as diagnostic evidence rather than used to define the primary validation protocol.

Figure 7 Physical-board grouped nested validation with leakage barriers.

The primary evaluation uses the current historical database of 34 PCB sides from 21 physical boards, with A/B sides treated as nested within physical boards. In each outer leave-one-board-out fold, a complete physical board is held out; when both A and B sides are available, both sides are excluded together to prevent leakage through shared board identity, geometry, or production context. Descriptor scaling, hyperparameter selection, support auditing, and interval calibration are performed only within the outer-training boards through inner grouped validation. Held-out board outcomes are used only for final evaluation and never enter descriptor scaling, tuning, calibration, or recommendation. The lower row summarizes the evaluation evidence package, including primary benchmark comparisons, mechanism diagnostics, trust diagnostics, robustness tests, negative controls, and sample-efficiency analysis. This design supports a leakage-controlled, current-database-only retrospective claim.

The primary metric is pressure mean absolute error in raw pressure units. Two engineering-window recovery rates are also reported: the fraction of sides within ±0.2 and within ±0.4 of the historically executed pressure. These window metrics are secondary because a method can achieve a high ±0.4 rate by predicting a common pressure while still having larger average error. Median absolute error, accepted coverage, accepted within-window recovery, and median runtime are reported as additional diagnostics. Thus, the evaluation distinguishes primary pressure-recovery accuracy from engineering-window and selective-recommendation diagnostics. Paired comparisons use side-level paired statistics and physical-board cluster-bootstrap intervals, with the latter treated as the primary inference because physical boards are the independence unit. Bootstrap intervals are widely used for robust uncertainty estimation when analytic sampling distributions are undesirable [32].

The baseline suite is designed to separate several explanations for performance. First, CBR baselines include Top-1 CBR, local median CBR, weighted kNN-CBR, and local mode CBR. Second, tabular machine-learning baselines include Ridge, Elastic Net, RBF-SVR, Random Forest, ExtraTrees, CatBoost, XGBoost, LightGBM, and Gaussian Process regression. These baselines test whether the proposed method is merely recovering a conventional descriptor-to-pressure regression relation. Third, structural baselines include Wasserstein-only, GW-only, FGW-only, and descriptor-plus-FGW retrieval. These baselines test whether unconstrained structural matching is sufficient. Fourth, naive historical controls include training median, training mode, nearest pad-count only, and random historical pressure. Finally, an exploratory graph neural network baseline is included as a small-sample diagnostic rather than as a primary comparator, because end-to-end graph learning is not expected to be stable with 34 side-level observations. Tree boosting baselines are included because XGBoost and LightGBM are widely used high-performing tabular learners [33,34], while Random Forest and CatBoost provide complementary ensemble references for small industrial tabular datasets [35,36]. The exploratory graph baseline is included only as a diagnostic comparator, drawing on graph convolution and graph expressive-power references rather than as a claim that deep graph learning is suitable for the present sample size [41,44]. Together, the baseline suite tests whether the observed performance can be explained by simple case reuse, tabular regression, structural matching alone, or trivial historical priors.

Several additional analyses test the industrial decision-support behavior. Ablations compare descriptor CBR, FGW-only retrieval, descriptor-plus-FGW retrieval, and the sparse-tail correction mechanism. Mechanism stratification separates common-support cases from sparse-tail cases. Calibration analyses evaluate empirical interval coverage at nominal 80% and 90% levels overall and by review status. Robustness analyses perturb pad missingness, position noise, size noise, shape availability, and super-node counts. Sample-efficiency analyses evaluate performance under reduced numbers of training physical boards. Protocol-sensitivity analysis compares grouped validation with diagnostic side-level splitting to show how validation choices affect the observed performance pattern. These analyses are included to communicate not only an aggregate score, but also when the system works, when it should defer, and which assumptions matter for industrial use.

The implementation was run in manuscript mode with fixed random seed 2026. The environment used Python 3.9.21 with NumPy 1.26.4, pandas 2.2.3, SciPy 1.13.1, scikit-learn 1.6.1, and POT 0.9.6.post1. Table 4 summarizes the evaluation protocol and evidence package.

Table 4 Experimental protocol and evidence package.


## 6. Results

## 6.1 Primary retrospective pressure-setting recovery

Under physical-board grouped nested validation, KOTMA-SR achieved the lowest primary MAE among the main methods evaluated in the primary protocol. Its pressure MAE was 0.2647, compared with 0.3235 for descriptor CBR, 0.3148 for an unconstrained KOTMA-SR variant, 0.3059 for the training median, and 0.4235 for the training mode. Relative to descriptor CBR, this corresponds to an 18.2% reduction in MAE. The median absolute error also decreased from 0.4000 for CBR to 0.1000 for KOTMA-SR. Engineering-window recovery improved from 41.2% to 55.9% within ±0.2 and from 73.5% to 79.4% within ±0.4. These results indicate that KOTMA-SR improves average retrospective pressure recovery while preserving an executable engineering-window interpretation. These primary results are summarized in Figure 8 and Table 5.

Figure 8 Primary retrospective first-article pressure-setting recovery performance.

KOTMA-SR achieved a pressure MAE of 0.2647 versus 0.3235 for descriptor CBR and improved recovery within both ±0.2 and ±0.4 engineering windows. Panel c reports paired side-level error differences relative to CBR, where positive values indicate lower absolute error for KOTMA-SR. The physical-board cluster-bootstrap interval for the MAE advantage over CBR was [0.0161, 0.1118].

Table 5 Primary grouped retrospective pressure-recovery results.

The paired evidence supports a bounded improvement over CBR. The mean MAE advantage of KOTMA-SR over CBR was 0.0588, with a physical-board cluster-bootstrap confidence interval of [0.0161, 0.1118] and a bootstrap probability of 0.9988 that KOTMA-SR was better. The side-level Wilcoxon test was borderline (p = 0.0526), which is expected in part because pressure recommendations are rounded to a discrete 0.1 grid and many sides tie exactly. Therefore, the cluster-bootstrap interval is used as the primary inference, while the Wilcoxon test is reported as a supplementary paired diagnostic. This inference strategy is consistent with the physical-board grouping used in the validation protocol.

Strong tabular baselines were competitive. CatBoost, Ridge, and ExtraTrees each obtained an MAE of approximately 0.2912, while Random Forest obtained 0.2941. KOTMA-SR had the best MAE point estimate, but the evidence does not support statistically significant superiority over all strong baselines. Some secondary window metrics also favored simple baselines; for example, Ridge achieved a ?0.4 recovery rate of 82.4%, and the training median and training mode reached 88.2% within ?0.4 despite worse MAE. These results indicate that KOTMA-SR should be interpreted as a selective, traceable recommendation strategy with favorable MAE, not as a universally dominant predictor on every metric. The full grouped benchmark is provided in Figure 9.

Figure 9 Mechanism diagnostics and sparse-tail behavior.

The extended grouped benchmark includes CBR variants, tabular machine-learning baselines, structural OT variants, naive historical controls, and exploratory comparators. KOTMA-SR has the best MAE point estimate under the physical-board grouped protocol, while cluster-bootstrap intervals versus strong baselines such as CatBoost and Ridge do not support universal superiority. This figure therefore supports a bounded performance claim rather than an absolute dominance claim.

## 6.2 Mechanism: bounded sparse-tail correction

The ablation results in this subsection are reported as mechanism diagnostics and should not be interpreted as replacements for the primary grouped nested evaluation reported in Section 6.1. The primary evaluation estimates the full KOTMA-SR decision-support pipeline under physical-board grouped outer holdout, fold-local model selection, and training-fold calibration. In contrast, the mechanism analysis isolates the contribution of descriptor CBR, structural matching, naive descriptor-structure fusion, and sparse-tail bounded correction under controlled settings. This distinction is important because the ablation values explain why the method works, whereas the primary protocol estimates its retrospective decision-support performance.

Under the mechanism-diagnostic protocol used in this subsection, Descriptor CBR achieved an ablation MAE of 0.2882, FGW-only retrieval achieved 0.3262, and descriptor-plus-FGW retrieval achieved 0.2917. The sparse-tail correction variant achieved the best ablation MAE of 0.2382 while preserving a ±0.4 recovery rate of 79.4%. This value should be interpreted as mechanism-level evidence rather than as a replacement for the primary grouped nested evaluation result reported in Section 6.1. The pattern supports the design choice made in Section 4: structural evidence is useful when it is used as a bounded corrective signal under weak descriptor support, whereas unconstrained structural retrieval alone is not reliable enough for this small industrial database. The mechanism and ablation results are summarized in Table 6.

Table 6 Mechanism and ablation summary.

The mechanism-stratified results make this interpretation more precise. In the common-support stratum, which contained 27 sides from 18 physical boards, KOTMA-SR and CBR had essentially identical MAE, both approximately 0.2667. In the sparse-tail stratum, which contained 7 sides from 6 physical boards, CBR MAE was 0.5429, while KOTMA-SR MAE was 0.2571. The mean gain over CBR in this stratum was 0.2857. Thus, the system improves mainly where descriptor retrieval is locally weak, while preserving the CBR safeguard when the historical neighborhood is well supported.

Gate-threshold sensitivity is reported in Figure 10. This analysis evaluates whether the sparse-tail mechanism is overly dependent on a single support threshold or correction cap. The best region occurs near the selected setting, but the performance pattern remains interpretable across nearby gate configurations. These results support the role of the sparse-tail gate as a conservative decision rule rather than an unconstrained optimization device.

Figure 10 Gate-threshold sensitivity.

Sensitivity of MAE, within-window recovery, correction rate, and review burden to sparse-tail support and correction-cap settings. Gate parameters are selected inside the training folds.

This result is important for the industrial interpretation of the method. A purely structural model would be difficult to justify when historical evidence is sparse and the production consequence of a poor recommendation may be costly. Conversely, a pure CBR model may fail when the nearest descriptor case lies in a weakly supported pressure tail. KOTMA-SR resolves this tension by making the structural module conditional and bounded. The method therefore behaves less like a black-box optimizer and more like an engineering assistant that changes its reasoning mode only when local case evidence is weak.

## 6.3 Interval calibration, selective review, and recommendation-card output

KOTMA-SR accepted 82.4% of the held-out PCB sides for direct recommendation and flagged the remaining sides for manual review. Among the accepted sides, the within ±0.4 recovery rate was 82.1%. These values indicate that selective recommendation is usable in the current retrospective database, but they should be interpreted as engineering-readiness evidence rather than prospective deployment validation. A conservative industrial threshold of 85% accepted within-window recovery was not reached. Therefore, the result supports KOTMA-SR as an engineer-supervised decision aid rather than as a system for unsupervised release. The selective-recommendation and interval-calibration behavior is summarized in Figure 11, while Table 8 illustrates how recommendation evidence is communicated to engineers.

Figure 11 Interval calibration and selective recommendation behavior.

The figure summarizes accepted-coverage behavior, empirical interval calibration, confidence-support relationships, and review-trigger distribution in the current retrospective database. KOTMA-SR accepted 82.4% of held-out sides for direct recommendation and achieved 82.1% within ±0.4 among accepted sides. Empirical interval coverage was close to the nominal 80% level and modestly below the nominal 90% level, indicating useful but not certified uncertainty calibration.


The empirical intervals were reasonably calibrated at the 80% level and modestly under-covered at the 90% level. Overall, the nominal 80% interval achieved 79.4% empirical coverage with a mean width of 0.9435, while the nominal 90% interval achieved 85.3% empirical coverage with a mean width of 1.5488. Conditional calibration showed that accepted cases were better covered than manual-review cases: accepted sides achieved 82.1% coverage at the nominal 80% level and 89.3% at the nominal 90% level, whereas manual-review sides achieved 66.7% at both levels. The interval design follows the spirit of conformal and quantile-based predictive uncertainty methods, but the small database means that the intervals should be interpreted empirically rather than as certified deployment guarantees [37,38]. Because the manual-review subgroup is small, these subgroup values should be interpreted as diagnostic evidence rather than stable estimates of future review-case coverage.

Interval comparison with Ridge and Top-1 CBR showed that KOTMA-SR provides competitive uncertainty summaries rather than uniquely superior calibration. At nominal 80% coverage, all three methods achieved 79.4% empirical coverage, while KOTMA-SR had a mean interval width of 0.9624, Ridge 1.1012, and Top-1 CBR 1.1424. At nominal 90% coverage, all three achieved 85.3% empirical coverage, with KOTMA-SR width 1.5594, Ridge 1.4935, and Top-1 CBR 1.5112. The value of KOTMA-SR intervals therefore lies not only in numerical width, but in their integration with traceable case evidence, bounded structural correction, and explicit review-trigger logic. This is why review triggers are reported together with intervals: predictive uncertainty and OOD-style diagnostics are most useful when they alter the recommended action rather than merely decorate a point estimate [39,40].

## 6.4 Robustness, sample efficiency, and control evidence

Robustness tests showed that recommendations were stable under several simulated input perturbations. Pad missingness at 1%, 5%, and 10% produced mean recommendation shifts of 0.0000, 0.0029, and 0.0118, respectively, with a maximum shift of 0.4 at the highest missingness level. Position noise and size noise produced no mean pressure shift in the tested settings. Varying the number of super-nodes from 40 to 100 did not change pressure recommendations, although it caused small changes in review flags at lower super-node counts. The main sensitivity was complete shape-feature removal: when all shape information was removed, the mean recommendation shift increased to 0.1853 and the review-flag change rate reached 20.6%. This result indicates that KOTMA-SR is robust to moderate geometric perturbations but depends on retaining meaningful pad-shape information. Robustness evidence is summarized in Figure 12.

Figure 12 Robustness under input perturbations.

The figure reports recommendation shifts and perturbed MAE under pad missingness, position noise, size noise, shape-feature removal, and super-node-count changes. Moderate perturbations cause limited changes, whereas complete shape-feature removal produces the largest recommendation shift.

Sample-efficiency analysis showed that performance improved as more physical boards were available in the historical case base. With 5 training physical boards, KOTMA-SR had MAE 0.3569, compared with 0.3824 for Top-1 CBR. With 10 boards, the corresponding values were 0.3216 and 0.4118; with 15 boards, 0.2853 and 0.3333; and with 20 boards, 0.2647 and 0.3235. These results suggest that selective structural correction becomes more useful as the historical case memory grows, while very small histories remain challenging.

Negative controls help rule out trivial explanations for the observed mechanism-level gain. Under the same diagnostic setting used for the control suite, the sparse-tail correction variant obtained an MAE of 0.2382, compared with 0.3471 for random historical pressure, 0.3059 for nearest pad-count only, and 0.3059 for the training median. This comparison indicates that the mechanism-level improvement is not explained by random reuse of historical pressures, simple pad-count proximity, or prediction of a common historical pressure. The training median had the highest ±0.4 recovery rate, again confirming that window recovery alone is not a sufficient endpoint. The exploratory GNN baseline was unstable under the current small database, with seed-level MAE ranging from 0.5382 to 0.7382 and ±0.4 recovery between 41.2% and 50.0%. This diagnostic result should not be generalized to larger SMT datasets; graph neural networks can be effective when sufficient graph-labeled data are available, but their expressive capacity does not remove the sample-size limitation in the present database [41,44]. The robustness, sample-efficiency, negative-control, and exploratory baseline evidence is summarized in Table 9.

Table 9 Control and robustness evidence summary.

Taken together, the results support a conservative industrial claim. KOTMA-SR improves retrospective first-article pressure recovery over descriptor CBR in the current database, obtains the best MAE point estimate among the evaluated methods, and provides recommendation cards with traceable evidence, empirical intervals, and review triggers. At the same time, the evidence remains retrospective, single-database, and pressure-recovery based. The appropriate conclusion is that KOTMA-SR is a promising knowledge-based process-recommendation method for sparse high-reliability SMT histories, pending prospective engineer-supervised validation and external-site evaluation.


## 7. Discussion

## 7.1 Implications for first-article solder-paste printing process setting

The main industrial value of KOTMA-SR is not to replace process engineers, but to organize sparse historical experience into an inspectable first-article recommendation workflow. In the current database, KOTMA-SR reduced pressure MAE relative to descriptor CBR while preserving the CBR safeguard for most supported cases. This behavior is suitable for high-reliability SMT production, where an unsupported recommendation may be more costly than requesting additional engineering review. The method therefore supports an engineer-supervised workflow in which each pressure suggestion is accompanied by retrieved evidence, empirical uncertainty, and escalation conditions.

The distinction between recovery and optimization is central to interpreting the results. Each PCB side in the present database has only one historically executed pressure, so the study cannot determine whether an unobserved alternative pressure would have produced better SPI or downstream quality. The target pressure is a historical engineering setting, not a counterfactual optimum. The evidence should therefore be understood as leakage-aware retrospective recovery of engineering practice. This is still useful in high-mix production, because a traceable and historically plausible starting point can reduce the cognitive burden of first-article preparation and provide a structured basis for engineer review.

## 7.2 Methodological implications for sparse manufacturing histories

The ablation and mechanism analyses show that structural information is useful only when it is used conservatively. FGW-only retrieval and naive descriptor-plus-FGW fusion did not explain the main gain. Instead, the improvement was concentrated in sparse-tail cases, where descriptor CBR had weak local pressure support. In common-support cases, KOTMA-SR largely preserved descriptor CBR behavior. This selective pattern is desirable: the system avoids unnecessary intervention when the historical case base already provides adequate descriptor evidence and activates structural reasoning mainly when conventional retrieval is likely to be fragile.

This finding clarifies the methodological contribution. The paper does not propose a new FGW distance and does not claim that structural matching alone solves SMT process recommendation. The contribution is a process-recommendation workflow that places structure-aware pad-field matching inside a support audit, a bounded correction rule, and a review-aware output format. This integration links historical case reuse, structural process evidence, empirical uncertainty, and executable process constraints for sparse first-article pressure setting.

## 7.3 Operational readiness and review boundary

The review-readiness analysis indicates that KOTMA-SR is useful but not deployment-complete. The system accepted 82.4% of held-out sides and achieved 82.1% within ±0.4 among accepted recommendations. The nominal 80% interval was close to empirical coverage, whereas the nominal 90% interval showed modest under-coverage. These results support the use of empirical intervals and review triggers as decision aids, but they do not justify unsupervised release.

The accepted within-window rate did not exceed a conservative 85% engineering-readiness threshold. This does not invalidate the method; rather, it defines its current maturity. KOTMA-SR is best positioned as an engineering assistant for first-article preparation: it can recommend a starting pressure, show supporting cases, and identify conditions that require closer review. It should not be interpreted as a certified safe controller or a fully autonomous SMT recipe generator.

7.4 Limitations

The most important limitation is the current-database-only retrospective design. The database contains 34 PCB sides from 21 physical boards and lacks reliable timestamps, site identifiers, and prospective deployment logs. Physical-board grouped nested validation reduces leakage within the available data, but it does not establish temporal generalization, external-site generalization, or production deployment success.

A second limitation is the absence of counterfactual quality feedback. Because only one executed setting is recorded for each PCB side, the study cannot estimate how alternative pressures would affect solder-paste inspection results, solder-joint defects, or downstream reliability. Therefore, the current evidence supports pressure recovery rather than quality-aware process optimization. Standard assembly and soldering requirements remain necessary after the recommendation is used, so the proposed card should be treated as a first-article preparation aid rather than a release decision [43,47].

A third limitation concerns input representation. Robustness tests showed stability under moderate pad missingness, position noise, size noise, and super-node-count variation, but complete shape-feature removal produced larger recommendation shifts and more review-flag changes. This suggests that prospective use would require controlled feature extraction, data-quality checks, and clear rules for handling incomplete PCB geometry. In particular, land-pattern and package-assembly guidelines imply that pad geometry and package context should be treated as process-relevant information rather than incidental CAD metadata [52,53].

Finally, strong tabular baselines were competitive. KOTMA-SR achieved the best MAE point estimate, but the evidence does not establish statistically significant superiority over every strong baseline. This result is unsurprising because ensemble learners are strong comparators for tabular industrial prediction even when they do not provide the same process-case traceability [33,36]. The appropriate claim is that KOTMA-SR provides a favorable combination of pressure-recovery accuracy, traceability, sparse-tail reasoning, and review-aware decision support, rather than universal predictive dominance.


## 8. Conclusion

This paper presented KOTMA-SR, a knowledge-guided process-recommendation method for first-article solder-paste printing pressure setting under sparse process histories. The framework retains descriptor CBR as an auditable default, uses FGW-based structural memory as bounded complementary evidence, activates correction mainly under sparse-tail support, and returns engineer-facing recommendation cards with empirical intervals and review triggers. In a current historical aerospace SMT database containing 34 PCB sides from 21 physical boards, KOTMA-SR reduced pressure MAE from 0.3235 for descriptor CBR to 0.2647 under physical-board grouped nested validation. The paired physical-board cluster-bootstrap interval for the MAE advantage over CBR was [0.0161, 0.1118], and the system accepted 82.4% of held-out sides, achieving 82.1% within ±0.4 among accepted recommendations.

These results support a bounded manufacturing-process recommendation claim. KOTMA-SR can organize historical SMT process knowledge, structural PCB evidence, empirical uncertainty, and review logic into a practical first-article recommendation workflow. However, the evidence remains retrospective, single-database, and pressure-recovery based. It does not establish autonomous process control, defect reduction, solder-deposit quality optimization, or external deployment readiness. Future work should evaluate the framework prospectively with engineer feedback, richer solder-paste inspection and defect outcomes, and temporally or externally separated production data.


## Data availability

The raw production database contains enterprise SMT process records and PCB geometry information subject to commercial restrictions. Anonymized derived tables, figure source data, and manuscript summary results are available from the corresponding author upon reasonable request and subject to enterprise approval. Raw pad-level coordinates and production records cannot be publicly released without additional masking or a data-use agreement.


## Code availability

The analysis pipeline was implemented in Python with fixed random seeds and recorded package versions. The code exports figure source data, benchmark summaries, calibration summaries, and robustness summaries. An anonymized research package is available from the corresponding author upon reasonable request after removal of enterprise-sensitive paths, identifiers, and production records.

Funding

This work was supported by the National Natural Science Foundation of China [Grant No. 52275507]; the Sichuan Provincial Science and Technology Program [Grant No. 2026YFHZ0277]; and the Natural Science Foundation Project of CAPU [Grant No. ZZH0623059].


## Declaration of competing interest

The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

Author Contributions

Xin Su: Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Data Curation, Writing - Original Draft, Writing - Review & Editing, Visualization.

Yichen Liu: Writing - Review & Editing, Supervision, Project administration.


## Acknowledgements

The authors acknowledge the engineering and production personnel who supported the collection and interpretation of the historical SMT process records.


## References

[1]	C.-H. Lee, K.-X. Lin, C.-W. Chou, Surrogate-based optimization framework for enhancing SMT process quality and productivity in electronics manufacturing services, Int. J. Adv. Manuf. Technol. 136 (2025) 5103–5122. https://doi.org/10.1007/s00170-025-15032-w.

[2]	Q. Zhang, P. Li, Y.-B. Zhao, Y. Kang, Human-on-the-loop control in surface mount technology via deep reinforcement learning, IET Control Theory Appl. 19 (2025) e70028. https://doi.org/10.1049/cth2.70028.

[3]	A. Aamodt, E. Plaza, Case-based reasoning: Foundational issues, methodological variations, and system approaches, AI Commun. 7 (1994) 39–59. https://doi.org/10.3233/AIC-1994-7104.

[4]	Q. Zhao, D. Wu, Y. Shen, J. Li, Q. Yu, S. Zhang, J. Qi, J. Hu, HAIL: Human-in-the-loop assembly imitation learning system, J. Manuf. Syst. 86 (2026) 991–1006. https://doi.org/10.1016/j.jmsy.2026.04.020.

[5]	M.S. Bajestani, D. Mun, D.B. Kim, Human-in-the-loop and large language models in smart manufacturing: Current applications, challenges, and perspectives, J. Manuf. Syst. 86 (2026) 913–941. https://doi.org/10.1016/j.jmsy.2026.04.027.

[6]	J.C. Cresswell, Y. Sui, B. Kumar, N. Vouitsis, Conformal prediction sets improve human decision making, (2024). https://doi.org/10.48550/arXiv.2401.13744.

[7]	D. Zhang, A. Chatzimparmpas, N. Kamali, J. Hullman, Evaluating the utility of conformal prediction sets for AI-advised image labeling, in: Proceedings of the 2024 CHI Conference on Human Factors in Computing Systems, Association for Computing Machinery, New York, NY, USA, 2024: pp. 1–19. https://doi.org/10.1145/3613904.3642446.

[8]	G. Peyré, M. Cuturi, J. Solomon, Gromov-wasserstein averaging of kernel and distance matrices, in: Proceedings of The 33rd International Conference on Machine Learning, 2016. https://proceedings.mlr.press/v48/peyre16.html (accessed June 5, 2026).

[9]	T. Vayer, L. Chapel, R. Flamary, R. Tavenard, N. Courty, Fused gromov-wasserstein distance for structured objects, Algorithms 13 (2020) 212. https://doi.org/10.3390/a13090212.

[10]	J. Sousa, A. Sousa, F. Brueckner, L.P. Reis, A. Reis, Human-in-the-loop multi-objective bayesian optimization for directed energy deposition with in-situ monitoring, Rob. Comput. Integr. Manuf. 92 (2025) 102892. https://doi.org/10.1016/j.rcim.2024.102892.

[11]	S. Wang, P. Zou, X. Gong, M. Song, J. Peng, R.J. Jiao, Visual analytics and intelligent reasoning for smart manufacturing defect detection and judgement: A meta-learning approach with knowledge graph embedding case-based reasoning, J. Ind. Inf. Integr. 37 (2024) 100536. https://doi.org/10.1016/j.jii.2023.100536.

[12]	L. Guo, T. Hu, L. Dong, S. Ma, Ontology and production rules-based dynamic knowledge base construction methodology for machining process, J. Manuf. Syst. 77 (2024) 1027–1044. https://doi.org/10.1016/j.jmsy.2024.11.006.

[13]	S. Liu, A dynamic updating method of digital twin knowledge model based on fused memorizing-forgetting model, Adv. Eng. Inf. 57 (2023) 102115. https://doi.org/10.1016/j.aei.2023.102115.

[14]	D.H. Nguyen, K. Tsuda, On a linear fused gromov-wasserstein distance for graph structured data, Pattern Recognit. 138 (2023) 109351. https://doi.org/10.1016/j.patcog.2023.109351.

[15]	X. Ma, X. Chu, Y. Wang, Y. Lin, J. Zhao, L. Ma, W. Zhu, Fused gromov-wasserstein graph mixup for graph-level classifications, in: Advances in Neural Information Processing Systems 36, 2023.

[16]	J. Tang, X. Zhao, L. Kong, X. Zhou, J. Li, Fused gromov-wasserstein alignment for graph edit distance computation and beyond, Proc. VLDB Endow. 18 (2025) 3641–3654. https://doi.org/10.14778/3748191.3748221.

[17]	M. Piening, R. Beinert, A novel sliced fused gromov-wasserstein distance, in: Proceedings of the AAAI Conference on Artificial Intelligence, 2026: pp. 24828–24836. https://doi.org/10.1609/aaai.v40i29.39669.

[18]	C. Cao, Y. Zhang, Y. Ai, Q. Zhang, Unsupervised feature selection via unifying distribution alignment and structure preservation, Inf. Fusion 126 (2026) 103544. https://doi.org/10.1016/j.inffus.2025.103544.

[19]	H. Feng, Y. Sun, X. Hu, Z. Li, C. Chen, B. Wang, Y. Wang, Flexible exploration: a hyperspectral image classification framework based on dynamic scale and graph optimal transport, Inf. Fusion 128 (2026) 103962. https://doi.org/10.1016/j.inffus.2025.103962.

[20]	D. Li, S. Liu, B. Wang, C. Yu, P. Zheng, W. Li, Trustworthy AI for human-centric smart manufacturing: A survey, J. Manuf. Syst. 78 (2025) 308–327. https://doi.org/10.1016/j.jmsy.2024.11.020.

[21]	Y. Zhong, A. Karthikeyan, P. Pagilla, R.K. Mehta, S.T.S. Bukkapatnam, Human-centric integrated safety and quality assurance in collaborative robotic manufacturing systems, CIRP Ann. 73 (2024) 345–348. https://doi.org/10.1016/j.cirp.2024.04.008.

[22]	R.X. Gao, J. Krüger, M. Merklein, H.-C. Möhring, J. Váncza, Artificial intelligence in manufacturing: State of the art, perspectives, and future directions, CIRP Ann. 73 (2024) 723–749. https://doi.org/10.1016/j.cirp.2024.04.101.

[23]	J. Jeon, Y. Sim, H. Lee, C. Han, D. Yun, E. Kim, S.L. Nagendra, M.B.G. Jun, Y. Kim, S.W. Lee, J. Lee, ChatCNC: Conversational machine monitoring via large language model and real-time data retrieval augmented generation, J. Manuf. Syst. 79 (2025) 504–514. https://doi.org/10.1016/j.jmsy.2025.01.018.

[24]	K. Hu, X. Yao, F. Qiao, W. Shen, H. Wu, W. Yang, Digital twin-integrated bandit learning for LRM-driven multi-agent resilient production scheduling, J. Manuf. Syst. 86 (2026) 50–66. https://doi.org/10.1016/j.jmsy.2026.02.021.

[25]	L. Zhou, Towards trustworthy AI in industry 5.0: Ante-hoc interpretability with deep learning, Comput. Ind. Eng. 213 (2026) 111805. https://doi.org/10.1016/j.cie.2026.111805.

[26]	S. Liu, J. Xie, X. Wang, X. Qiao, You are my eyes: Integrating human intelligence and LLMs in AR-assisted motion planning for industrial mobile robots, Rob. Comput. Integr. Manuf. 98 (2026) 103174. https://doi.org/10.1016/j.rcim.2025.103174.

[27]	C. Chen, Leveraging large language models for smart manufacturing: Reviews, enablers, challenges, and opportunities, J. Manuf. Syst. 85 (2026) 593–612. https://doi.org/10.1016/j.jmsy.2026.02.008.

[28]	J. Leng, AIGC-empowered smart manufacturing: Prospects and challenges, Rob. Comput. Integr. Manuf. 97 (2026) 103076. https://doi.org/10.1016/j.rcim.2025.103076.

[29]	G. Shafer, V. Vovk, A tutorial on conformal prediction, J. Mach. Learn. Res. 9 (2008) 371-421.

[30]	G. De Toni, N. Okati, S. Thejaswi, E. Straitouri, M. Gomez-Rodriguez, Towards human-AI complementarity with prediction sets, Proceedings of Machine Learning Research (2024). https://doi.org/10.52202/079017-0986.

[31]	A. Heddoub, L. Homri, A. Siadat, Class-conditional conformal prediction with discriminant-analysis backbones for reliable open-set fault diagnosis in safety-critical industrial systems, J. Process Control 161 (2026) 103701. https://doi.org/10.1016/j.jprocont.2026.103701.

[32]	B. Efron, R.J. Tibshirani, An introduction to the bootstrap, Chapman & Hall/CRC, New York, 1993.

[33]	T. Chen, C. Guestrin, XGBoost: A scalable tree boosting system, in: Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, ACM, San Francisco California USA, 2016: pp. 785–794. https://doi.org/10.1145/2939672.2939785.

[34]	G. Ke, LightGBM: a highly efficient gradient boosting decision tree, in: Advances in Neural Information Processing Systems 30, 2017.

[35]	L. Breiman, Random forests, Mach. Learn. 45 (2001) 5–32. https://doi.org/10.1023/A:1010933404324.

[36]	L. Prokhorenkova, CatBoost: unbiased boosting with categorical features, in: Advances in Neural Information Processing Systems 31, 2018.

[37] A.N. Angelopoulos, S. Bates, A gentle introduction to conformal prediction and distribution-free uncertainty quantification, Found. Trends Mach. Learn. 16 (2023) 494-591. https://doi.org/10.1561/2200000101.

[38] Y. Romano, E. Patterson, E. Candes, Conformalized quantile regression, in: Advances in Neural Information Processing Systems, 2019.

[39] R.F. Barber, E.J. Candes, A. Ramdas, R.J. Tibshirani, Predictive inference with the jackknife+, Ann. Stat. 49 (2021) 486-507. https://doi.org/10.1214/20-AOS1965.

[40] D. Hendrycks, K. Gimpel, A baseline for detecting misclassified and out-of-distribution examples in neural networks, in: International Conference on Learning Representations, 2017.

[41] T.N. Kipf, M. Welling, Semi-supervised classification with graph convolutional networks, in: International Conference on Learning Representations, 2017.

[42] IPC, IPC-7525C: Stencil Design Guidelines, IPC International, Bannockburn, IL, 2021.

[43] IPC, IPC-A-610H: Acceptability of Electronic Assemblies, IPC International, Bannockburn, IL, 2020.

[44] K. Xu, W. Hu, J. Leskovec, S. Jegelka, How powerful are graph neural networks?, in: International Conference on Learning Representations, 2019.

[45] M. Cuturi, Sinkhorn distances: Lightspeed computation of optimal transport, in: Advances in Neural Information Processing Systems, 2013.

[46] G. Peyre, M. Cuturi, Computational optimal transport, Found. Trends Mach. Learn. 11 (2019) 355-607. https://doi.org/10.1561/2200000073.

[47] IPC, IPC J-STD-001H: Requirements for Soldered Electrical and Electronic Assemblies, IPC International, Bannockburn, IL, 2020.

[48] N.-C. Lee, Reflow Soldering Processes and Troubleshooting: SMT, BGA, CSP and Flip Chip Technologies, Newnes, Boston, 2002.

[49] C.F. Coombs, H.T. Holden, Printed Circuits Handbook, 7th ed., McGraw-Hill Education, New York, 2016.

[50] R.J. Klein Wassink, Soldering in Electronics, 2nd ed., Electrochemical Publications, Ayr, 1989.

[51] SMTA, Handbook of Electronics Assembly and Guide to SMTA Certification, Surface Mount Technology Association, 2014.

[52] IPC, IPC-7095D: Design and Assembly Process Implementation for BGAs, IPC International, Bannockburn, IL, 2020.

[53] IPC, IPC-7351B: Generic Requirements for Surface Mount Design and Land Pattern Standard, IPC International, Bannockburn, IL, 2010.

[54] N. Courty, R. Flamary, D. Tuia, A. Rakotomamonjy, Optimal transport for domain adaptation, IEEE Trans. Pattern Anal. Mach. Intell. 39 (2017) 1853-1865. https://doi.org/10.1109/TPAMI.2016.2615921.



## Tables

### Table 1. Problem notation and claim boundary.

| Symbol or term | Meaning in this study | Claim boundary |
|---|---|---|
| PCB side | One side of a physical PCB used as the recommendation object | A/B sides can differ and are evaluated as side-level recommendations |
| Physical board | Physical PCB identifier used as the leakage-control unit | All sides of a held-out physical board are excluded from training and tuning |
| \(x_i\) | Fixed-length board and pad-field descriptor vector | Used for auditable descriptor CBR retrieval |
| \(G_i\) | Structural pad-field representation after super-node coarsening | Used as complementary structural evidence |
| \(p_i\) | Historically executed first-article printing pressure | Treated as the retrospective recovery target |
| \(v_i\) | Historically executed squeegee velocity | Used to define an empirical velocity suggestion, not a learned optimization target |
| \(\hat{p}_q\) | Recommended pressure for held-out target side | Rounded to the executable pressure grid before evaluation |

### Table 2. Dataset scope of the current historical SMT database.

| Item | Value | Manuscript interpretation |
|---|---|---|
| PCB sides / physical boards | 34/21 | Side-level recommendation with physical-board grouped leakage control |
| A/B side count | A=19; B=15 | Both sides of a held-out physical board are excluded together |
| Pressure range and distribution | Feasible 5.0-8.0; observed median 6.0; mean 6.094 | Pressure is the active recommendation variable |
| Velocity range and distribution | Feasible 0.0-100.0; observed median 0.8; mean 0.821 | Velocity is treated as an empirical process anchor |
| Pad-count distribution | Min 622; median 40645; max 214526 | Variable-size pad fields motivate structural memory |
| Board span summary | x median 158.75; y median 119.00 | Board-size variation is part of the case representation |

### Table 3. Core methodological rules and fold-local parameter settings of KOTMA-SR.

| Method component | Core rule | Fold-local setting / parameter |
|---|---|---|
| Descriptor case memory | \(x_i\) contains log pad count, log board dimensions, pad-area mean/std, aperture-ratio mean/std, aspect-ratio mean/std, and x/y pad spans. | Twelve descriptor features are constructed for each PCB side. |
| Descriptor retrieval | Similarity is computed by Euclidean distance after training-fold z-score standardization. The nearest descriptor case supplies the CBR safeguard. | Retrieval neighbor count \(k_{ret}\) is selected from \(\{1,3,5\}\). The top-ranked neighborhood provides support evidence. |
| Super-node structural memory | Pad fields are coarsened by MiniBatchKMeans over normalized x/y position and pad area. Super-node positions and attributes are area-weighted aggregates. | The default number of super-nodes is \(K_{SN}=80\); robustness analysis evaluates \(K_{SN}\in\{40,60,80,100\}\). |
| FGW structural matching | Entropic FGW distance is computed over normalized feature cost and normalized intra-object distance matrices. | Entropic regularization is \(\varepsilon\); the FGW balance parameter \(\alpha\) is adaptive unless fixed in sensitivity analysis. |
| Sparse-tail support gate | Structural correction is triggered only when the descriptor CBR pressure has insufficient local support or falls outside the fold-local supported pressure range. | The minimum supported pressure-case count is \(n_{min}=2\). |
| Bounded structural correction | The final pressure starts from descriptor CBR. If the sparse-tail gate is triggered, the structural estimate can adjust the CBR pressure only within a capped correction range. | Correction cap \(c\) is selected from \(\{0.2,0.4,0.6\}\); the feasible pressure range is 5.0-8.0. |
| Empirical uncertainty intervals | Recommendation intervals are formed from inner-fold absolute residual quantiles and clipped to the feasible pressure range. | Nominal quantiles are 0.80 and 0.90. |
| Review triggers | Manual review is triggered by low effective neighbors, OOD descriptor distance, retrieval-prior disagreement, low confidence, or wide interval warning. | Minimum effective-neighbor threshold is 2.0; interval review-width threshold is 0.8. |

### Table 4. Algorithmic summary of KOTMA-SR for one outer validation fold.

| Step | Operation |
|---|---|
| Input | Training physical-board cases \(\mathcal{D}_{train}\), held-out target PCB side \(q\), fold-local hyperparameter grid, feasible pressure range \([5.0,8.0]\), and executable grid step 0.1. |
| 1 | Fit the descriptor scaler using \(\mathcal{D}_{train}\) only. |
| 2 | Select retrieval, structural, support, and correction parameters by inner physical-board grouped validation on \(\mathcal{D}_{train}\). |
| 3 | Build descriptor memory from fold-scaled descriptors in \(\mathcal{D}_{train}\). |
| 4 | Build structural memory by super-node coarsening for cases in \(\mathcal{D}_{train}\). |
| 5 | Retrieve descriptor neighbors of \(q\) and compute descriptor-CBR pressure \(p_{CBR}\). |
| 6 | Audit fold-local pressure support around \(p_{CBR}\). |
| 7 | If support is sufficient, keep \(p_{CBR}\); otherwise compute FGW structural-neighbor evidence and apply bounded sparse-tail correction. |
| 8 | Round the preliminary pressure to the executable grid and clip it to \([5.0,8.0]\). |
| 9 | Calibrate empirical intervals using inner-fold residuals from \(\mathcal{D}_{train}\) only. |
| 10 | Set review triggers from support strength, descriptor coverage, interval width, and OOD flags. |
| 11 | Return \(\hat{p}_q\), \(\hat{v}_q\), retrieved-neighbor evidence, uncertainty intervals, review reasons, and the recommendation card. |

### Table 5. Experimental protocol and evidence package.

| Component | Setting in this study | Purpose |
|---|---|---|
| Database | 34 PCB sides from 21 physical boards | Current historical SMT first-article records |
| Primary split | Physical-board grouped nested LOBO | Avoids A/B-side leakage during tuning and evaluation |
| Primary endpoint | Pressure MAE | Retrospective recovery of executed pressure |
| Secondary endpoints | Within ?0.2 and ?0.4 recovery; median error | Engineering-window diagnostics |
| Review endpoints | Direct-recommendation coverage; accepted within ?0.4; interval coverage | Measures selective recommendation behavior |
| Baselines | CBR, tabular ML, structural OT, naive historical controls, exploratory GNN | Separates CBR, regression, structural, and trivial explanations |
| Inference | Physical-board cluster bootstrap; side-level Wilcoxon diagnostic | Accounts for grouped physical-board dependence |
| Robustness | Pad, position, size, shape, and super-node perturbations | Tests sensitivity of industrial inputs |
| Mechanism | Ablation and sparse-tail strata | Explains why bounded correction helps |
| Control evidence | Random historical pressure, nearest pad-count only, training priors | Rules out trivial explanations |
| Sample efficiency / protocol sensitivity | Reduced training-board histories; grouped vs diagnostic side-level validation | Tests dependence on data size and validation choice |

### Table 6. Primary grouped retrospective pressure-recovery results.

| Method | MAE | Median absolute error | Within ?0.2 | Within ?0.4 | Direct-recommendation coverage | Accepted within ?0.4 |
|---|---:|---:|---:|---:|---:|---:|
| KOTMA-SR | 0.2647 | 0.1000 | 55.9% | 79.4% | 82.4% | 82.1% |
| Descriptor CBR | 0.3235 | 0.4000 | 41.2% | 73.5% | NA | NA |
| KOTMA-SR unconstrained | 0.3148 | 0.2141 | 47.1% | 67.6% | NA | NA |
| Training median | 0.3059 | 0.4000 | 38.2% | 88.2% | NA | NA |
| Training mode | 0.4235 | 0.4000 | 8.8% | 88.2% | NA | NA |

### Table 7. Mechanism and ablation summary.

| Analysis | Group or method | n sides | MAE | Within ?0.4 | Interpretation |
|---|---|---:|---:|---:|---|
| Ablation | Descriptor CBR | 34 | 0.2882 | 76.5% | Auditable default |
| Ablation | FGW only | 34 | 0.3262 | 70.6% | Structural matching alone is insufficient |
| Ablation | Descriptor + FGW | 34 | 0.2917 | 73.5% | Naive fusion does not explain the gain |
| Ablation | Sparse-tail correction | 34 | 0.2382 | 79.4% | Best mechanism-level variant |
| Stratum | Common support | 27 | 0.2667 | NA | KOTMA-SR preserves CBR behavior |
| Stratum | Sparse tail | 7 | 0.2571 | NA | Main source of gain over CBR |

### Table 8. Anonymized example of an engineer-facing first-article recommendation card.

| Field | Value |
|---|---|
| Target PCB side | Held-out side Q1 |
| Executable pressure grid | 5.0-8.0, rounded to 0.1 |
| Historical pressure / recommended pressure | 6.4 / 6.5 |
| Empirical velocity anchor | 0.8 |
| Descriptor nearest-case pressure | 7.0 |
| Structural evidence pressure | 6.41 |
| Sparse-tail support status | Weak descriptor support; structural correction permitted |
| Structural correction | Activated; bounded before grid rounding |
| Top-3 retrieved neighbors with weights | Case N1 (0.238); Case N2 (0.176); Case N3 (0.148) |
| 80% / 90% empirical intervals | [6.02, 6.98] / [5.70, 7.30] |
| Review flag and reasons | Yes; OOD descriptor distance and retrieval-prior disagreement |
| Recommended engineer action | Use as reviewed initial pressure, not direct production release. |
| Required first-article verification | Standard SPI, visual inspection, and process-engineer sign-off before release |
| Engineering interpretation | Engineer-reviewed starting pressure, not an autonomous quality optimum |

### Table 9. Control and robustness evidence summary.

| Evidence type | Main result | Interpretation |
|---|---|---|
| Pad missingness | Mean shift = 0.0000, 0.0029, and 0.0118 at 1%, 5%, and 10% missingness | Recommendations are stable under moderate pad loss |
| Position and size noise | No mean pressure shift in tested settings | Descriptor and structural memory are not highly sensitive to moderate coordinate or size noise |
| Super-node count | \(K_{SN}=40\) to 100 did not change pressure recommendations | Structural coarsening is stable over the tested range |
| Shape-feature removal | Mean shift = 0.1853; review-flag change rate = 20.6% | Pad-shape information is important and should be retained |
| Sample efficiency | MAE decreased from 0.3569 with 5 boards to 0.2647 with 20 boards | Larger historical case memory improves recommendation quality |
| Negative controls | KOTMA-SR outperformed random history, nearest pad-count only, and training median in MAE | Performance is not explained by trivial historical priors |
| Exploratory GNN | Seed-level MAE ranged from 0.5382 to 0.7382 | End-to-end graph learning is unstable in the current small database |
