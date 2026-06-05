"""Red-blue supplementary figures for the KBS V2 evidence package."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .v1_figures import COLORS, save_pub, set_publication_style


def _title(ax, label: str, text: str) -> None:
    ax.text(-0.12, 1.04, label, transform=ax.transAxes, fontsize=8, weight="bold")
    ax.set_title(text, loc="left", fontsize=7.2, weight="bold")


def plot_s1_benchmark(summary: pd.DataFrame, paired: pd.DataFrame, output_dir: Path) -> None:
    set_publication_style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.4), gridspec_kw={"width_ratios": [1.2, 1.0]})
    ordered = summary.sort_values("pressure_mae_raw", ascending=True)
    colors = [COLORS["red"] if method == "KOTMA-SR" else COLORS["blue_mid"] for method in ordered["method"]]
    _title(axes[0], "a", "Physical-board grouped benchmark")
    axes[0].barh(ordered["method"], ordered["pressure_mae_raw"], color=colors)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Pressure MAE")
    forest = paired.sort_values("mean_advantage_raw")
    _title(axes[1], "b", "Cluster-bootstrap advantage vs KOTMA-SR")
    y = np.arange(len(forest))
    axes[1].axvline(0, color=COLORS["neutral_mid"], lw=0.8)
    axes[1].errorbar(
        forest["mean_advantage_raw"],
        y,
        xerr=[
            forest["mean_advantage_raw"] - forest["cluster_bootstrap_ci_low"],
            forest["cluster_bootstrap_ci_high"] - forest["mean_advantage_raw"],
        ],
        fmt="o",
        color=COLORS["red"],
        ecolor=COLORS["red_mid"],
        ms=3,
    )
    axes[1].set_yticks(y, forest["comparator"])
    axes[1].set_xlabel("Comparator MAE - KOTMA-SR MAE")
    fig.tight_layout(w_pad=1.2)
    source = pd.concat([summary.assign(panel="summary"), paired.assign(panel="paired")], ignore_index=True, sort=False)
    save_pub(fig, output_dir / "FigS1_Grouped_Benchmark", source)


def plot_s2_protocols(protocol_summary: pd.DataFrame, output_dir: Path) -> None:
    set_publication_style()
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    _title(ax, "a", "Validation protocol sensitivity")
    pivot = protocol_summary.pivot(index="method", columns="protocol", values="pressure_mae_raw")
    pivot.plot(kind="barh", ax=ax, color=[COLORS["blue"], COLORS["red_mid"]])
    ax.set_xlabel("Pressure MAE")
    ax.set_ylabel("")
    ax.legend(title="Protocol")
    fig.tight_layout()
    save_pub(fig, output_dir / "FigS2_Protocol_Sensitivity", protocol_summary)


def plot_s3_mechanism(cases: pd.DataFrame, output_dir: Path) -> None:
    set_publication_style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7))
    _title(axes[0], "a", "Bounded-correction case gains")
    sparse = cases[cases["stratum"].eq("sparse_tail")].sort_values("gain_vs_cbr_raw")
    axes[0].axvline(0, color=COLORS["neutral_mid"], lw=0.8)
    axes[0].barh(sparse["board_id"], sparse["gain_vs_cbr_raw"], color=np.where(sparse["gain_vs_cbr_raw"] >= 0, COLORS["red"], COLORS["blue"]))
    axes[0].set_xlabel("CBR error - KOTMA-SR error")
    _title(axes[1], "b", "Pressure-bin recovery")
    pressure = cases.groupby("observed_pressure_raw", as_index=False)[["safe_error_raw", "cbr_error_raw"]].mean()
    axes[1].plot(pressure["observed_pressure_raw"], pressure["safe_error_raw"], marker="o", color=COLORS["red"], label="KOTMA-SR")
    axes[1].plot(pressure["observed_pressure_raw"], pressure["cbr_error_raw"], marker="o", color=COLORS["blue"], label="CBR")
    axes[1].set_xlabel("Observed pressure")
    axes[1].set_ylabel("MAE")
    axes[1].legend()
    fig.tight_layout(w_pad=1.4)
    save_pub(fig, output_dir / "FigS3_Sparse_Tail_Cases", cases)


def plot_s4_gate(gate: pd.DataFrame, output_dir: Path) -> None:
    set_publication_style()
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.7))
    _title(axes[0], "a", "Safety-gate MAE")
    matrix = gate.pivot(index="min_supported_pressure_cases", columns="max_tail_adjustment_raw", values="pressure_mae_raw")
    sns.heatmap(matrix, cmap=sns.light_palette(COLORS["red"], as_cmap=True), annot=True, fmt=".3f", ax=axes[0], cbar_kws={"label": "MAE"})
    _title(axes[1], "b", "Gate Pareto map")
    axes[1].scatter(gate["within_0_4_raw_rate"], gate["pressure_mae_raw"], c=np.where(gate["pareto_front"], COLORS["red"], COLORS["blue_mid"]), s=30)
    axes[1].set_xlabel("Within +/-0.4")
    axes[1].set_ylabel("MAE")
    fig.tight_layout(w_pad=1.4)
    save_pub(fig, output_dir / "FigS4_Gate_Sensitivity", gate)


def plot_s5_robustness(robustness: pd.DataFrame, output_dir: Path) -> None:
    set_publication_style()
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.6))
    grouped = robustness.groupby(["perturbation", "level"], as_index=False).agg(shift=("recommendation_shift_raw", "mean"), error_delta=("perturbed_error_raw", lambda x: float(x.mean())))
    line_colors = {
        "pad_missing": COLORS["blue"],
        "position_noise": COLORS["blue_mid"],
        "size_noise": COLORS["red_mid"],
        "shape_missing": COLORS["red"],
        "super_node_count": COLORS["neutral_mid"],
    }
    _title(axes[0], "a", "Recommendation stability")
    for name, frame in grouped.groupby("perturbation"):
        x = frame["level"] if name == "super_node_count" else 100 * frame["level"]
        axes[0].plot(x, frame["shift"], marker="o", ms=3, color=line_colors[name], label=name.replace("_", " "))
    axes[0].set_xlabel("Perturbation level (%) / super-node count")
    axes[0].set_ylabel("Mean pressure shift")
    axes[0].legend(fontsize=4.8)
    _title(axes[1], "b", "Error under perturbation")
    for name, frame in grouped.groupby("perturbation"):
        x = frame["level"] if name == "super_node_count" else 100 * frame["level"]
        axes[1].plot(x, frame["error_delta"], marker="o", ms=3, color=line_colors[name], label=name.replace("_", " "))
    axes[1].set_xlabel("Perturbation level (%) / super-node count")
    axes[1].set_ylabel("Perturbed MAE")
    fig.tight_layout(w_pad=1.2)
    save_pub(fig, output_dir / "FigS5_Robustness", robustness)


def plot_s6_calibration(intervals: pd.DataFrame, output_dir: Path) -> None:
    set_publication_style()
    frame = intervals[intervals["layer"].isin(["overall", "stratum", "ood", "review"])].copy()
    frame["label"] = frame["layer"].astype(str) + ": " + frame["group"].astype(str)
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    _title(ax, "a", "Conditional conformal coverage")
    for nominal, group in frame.groupby("nominal_coverage"):
        color = COLORS["blue"] if nominal < 0.85 else COLORS["red"]
        ax.plot(group["label"], 100 * group["empirical_coverage"], marker="o", color=color, label=f"{int(100*nominal)}% nominal")
        ax.axhline(100 * nominal, color=COLORS["neutral_mid"], lw=0.5, ls="--")
    ax.tick_params(axis="x", rotation=35)
    ax.set_ylabel("Empirical coverage (%)")
    ax.legend()
    fig.tight_layout()
    save_pub(fig, output_dir / "FigS6_Conditional_Calibration", intervals)


def plot_s7_velocity(velocity: pd.DataFrame, output_dir: Path) -> None:
    set_publication_style()
    fig, ax = plt.subplots(figsize=(4.8, 2.5))
    _title(ax, "a", "Empirical velocity policy")
    rows = pd.DataFrame(
        [
            {"strategy": "Fixed 0.8", "mae": velocity["fixed_0_8_abs_error"].mean()},
            {"strategy": "Fold-local mode", "mae": velocity["fold_mode_abs_error"].mean()},
        ]
    )
    ax.bar(rows["strategy"], rows["mae"], color=[COLORS["blue"], COLORS["red"]])
    ax.set_ylabel("Velocity MAE")
    fig.tight_layout()
    save_pub(fig, output_dir / "FigS7_Velocity_Policy", velocity)


def plot_s8_gnn(gnn: pd.DataFrame, output_dir: Path) -> None:
    if "pressure_abs_error_raw" not in gnn:
        return
    set_publication_style()
    fig, ax = plt.subplots(figsize=(4.8, 2.5))
    _title(ax, "a", "Exploratory small-n GNN variability")
    seed = gnn.groupby("seed", as_index=False)["pressure_abs_error_raw"].mean()
    ax.scatter(seed["seed"].astype(str), seed["pressure_abs_error_raw"], color=COLORS["red"], s=24)
    ax.axhline(seed["pressure_abs_error_raw"].mean(), color=COLORS["blue"], lw=1, label="seed mean")
    ax.set_xlabel("Random seed")
    ax.set_ylabel("Pressure MAE")
    ax.legend()
    fig.tight_layout()
    save_pub(fig, output_dir / "FigS8_Exploratory_GNN", gnn)


def plot_s9_interval_comparators(summary: pd.DataFrame, output_dir: Path) -> None:
    set_publication_style()
    labels = [f"{row.method}\n{int(100 * row.nominal_coverage)}%" for row in summary.itertuples()]
    x = np.arange(len(labels))
    method_colors = {"KOTMA-SR": COLORS["red"], "Top-1 CBR": COLORS["blue"], "Ridge": COLORS["neutral_mid"]}
    colors = [method_colors[method] for method in summary["method"]]
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.7))
    _title(axes[0], "a", "Grouped OOF interval calibration")
    axes[0].bar(x, summary["empirical_coverage"], color=colors)
    axes[0].axhline(0.80, color=COLORS["ink"], ls="--", lw=0.8)
    axes[0].set_xticks(x, labels, rotation=20, ha="right")
    axes[0].set_ylabel("Empirical coverage")
    axes[0].set_ylim(0.0, 1.0)
    _title(axes[1], "b", "Interval efficiency")
    axes[1].bar(x, summary["mean_interval_width_raw"], color=colors)
    axes[1].set_xticks(x, labels, rotation=20, ha="right")
    axes[1].set_ylabel("Mean interval width")
    fig.tight_layout(w_pad=1.2)
    save_pub(fig, output_dir / "FigS9_Interval_Comparators", summary)


def write_supplementary_manifest(output_dir: Path) -> pd.DataFrame:
    rows = []
    for png in sorted(output_dir.glob("FigS*.png")):
        stem = png.stem
        rows.append(
            {
                "figure": stem,
                "profile": "supplementary",
                "role": "supplementary_evidence",
                "claim": "Supplementary validation evidence.",
                "source_data": f"{stem}_SourceData.csv",
                "svg_exists": int((output_dir / f"{stem}.svg").exists()),
                "pdf_exists": int((output_dir / f"{stem}.pdf").exists()),
                "tiff_exists": int((output_dir / f"{stem}.tiff").exists()),
                "png_exists": int((output_dir / f"{stem}.png").exists()),
            }
        )
    manifest = pd.DataFrame(rows)
    manifest.to_csv(output_dir / "figure_manifest.csv", index=False)
    return manifest


def generate_supplementary_figures(artifacts: dict[str, pd.DataFrame], output_dir: str | Path) -> pd.DataFrame:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_s1_benchmark(artifacts["benchmark_summary"], artifacts["benchmark_paired"], output_dir)
    plot_s2_protocols(artifacts["protocol_summary"], output_dir)
    plot_s3_mechanism(artifacts["mechanism_cases"], output_dir)
    plot_s4_gate(artifacts["gate_sensitivity"], output_dir)
    plot_s5_robustness(artifacts["robustness_v2"], output_dir)
    plot_s6_calibration(artifacts["conditional_intervals"], output_dir)
    plot_s7_velocity(artifacts["velocity_policy"], output_dir)
    plot_s8_gnn(artifacts["exploratory_gnn"], output_dir)
    plot_s9_interval_comparators(artifacts["interval_comparators"], output_dir)
    return write_supplementary_manifest(output_dir)

