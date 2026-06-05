"""KBS-oriented publication figures for KOTMA-SR."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle


COLORS = {
    "KOTMA-SR": "#B03A48",
    "KOTMA-SR (unconstrained)": "#D98C95",
    "CBR": "#245A9A",
    "Training median": "#8C96A3",
    "Training mode": "#B7BEC8",
    "red": "#B03A48",
    "red_mid": "#D98C95",
    "red_soft": "#F4D9DC",
    "blue": "#245A9A",
    "blue_mid": "#7FA6D6",
    "blue_soft": "#DCE8F5",
    "neutral": "#E8EDF2",
    "neutral_mid": "#AAB4BF",
    "ink": "#263238",
    "muted": "#52616B",
}


def set_publication_style() -> None:
    sns.set_theme(style="white", context="paper")
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 6.4,
            "axes.labelsize": 6.4,
            "axes.titlesize": 7.2,
            "xtick.labelsize": 5.6,
            "ytick.labelsize": 5.6,
            "legend.fontsize": 5.5,
            "legend.frameon": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 130,
        }
    )


def save_pub(fig, base: Path, source: pd.DataFrame) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    source.to_csv(f"{base}_SourceData.csv", index=False)
    fig.savefig(f"{base}.svg", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(f"{base}.pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(f"{base}.png", dpi=300, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(f"{base}.tiff", dpi=600, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def _box(ax, xy, width, height, text, color, subtitle=None, edge=None, fontsize=6.2):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.010,rounding_size=0.018",
        linewidth=0.75,
        edgecolor=edge or COLORS["ink"],
        facecolor=color,
    )
    ax.add_patch(patch)
    ax.text(xy[0] + width / 2, xy[1] + height * (0.60 if subtitle else 0.50), text, ha="center", va="center", fontsize=fontsize, weight="bold")
    if subtitle:
        ax.text(xy[0] + width / 2, xy[1] + height * 0.27, subtitle, ha="center", va="center", fontsize=5.1, color=COLORS["muted"])
    return patch


def _arrow(ax, start, end, color=None, style="->", lw=0.9):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=8, color=color or COLORS["ink"], lw=lw))


def _panel(ax, label, title, label_x=-0.14):
    ax.text(label_x, 1.04, label, transform=ax.transAxes, fontsize=8, weight="bold")
    ax.set_title(title, loc="left", weight="bold", pad=3)


def _safe_summary(summary: pd.DataFrame) -> pd.Series:
    return summary.set_index("method").loc["KOTMA-SR"]


def _cbr_summary(summary: pd.DataFrame) -> pd.Series:
    return summary.set_index("method").loc["CBR"]


def _board_frame(records) -> pd.DataFrame:
    rows = []
    seen = set()
    for record in records:
        if record.board_id in seen:
            continue
        seen.add(record.board_id)
        rows.append(
            {
                "board_id": record.board_id,
                "pressure": record.press_raw,
                "velocity": record.velocity_raw,
                "pads": len(record.comps_raw),
                "board_area": record.board_dim[0] * record.board_dim[1],
            }
        )
    return pd.DataFrame(rows)


def plot_fig1_graphical_abstract(profile: str, summary: pd.DataFrame, traces: pd.DataFrame, output_dir: Path) -> None:
    """Opening figure: problem, knowledge reasoning, recommendation card and effect."""
    set_publication_style()
    safe, cbr = _safe_summary(summary), _cbr_summary(summary)
    fig = plt.figure(figsize=(7.2, 4.35))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.78, 0.72], hspace=0.18)
    ax = fig.add_subplot(gs[0])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    title = "KOTMA-SR: knowledge-guided first-article recommendation under sparse histories"
    if profile == "jms":
        title = "KOTMA-SR: review-aware first-article recommendation for high-mix SMT"
    ax.text(0.5, 1.03, title, ha="center", va="bottom", fontsize=9.3, weight="bold")
    ax.text(0.02, 0.91, "Industrial constraint", color=COLORS["blue"], fontsize=6.5, weight="bold")
    ax.text(0.39, 0.91, "Process-knowledge-guided reasoning", color=COLORS["red"], fontsize=6.5, weight="bold")
    ax.text(0.81, 0.91, "Traceable output", color=COLORS["blue"], fontsize=6.5, weight="bold")

    _box(ax, (0.02, 0.55), 0.15, 0.22, "Sparse PCB cases", COLORS["blue_soft"], "one executed setting\nper PCB side")
    _box(ax, (0.20, 0.55), 0.15, 0.22, "New PCB side", COLORS["neutral"], "geometry known;\nSPI hidden")
    for i, y in enumerate([0.33, 0.56, 0.76]):
        ax.add_patch(Rectangle((0.225 + 0.025 * i, y - 0.015), 0.07, 0.045, facecolor=COLORS["blue_mid"], edgecolor=COLORS["ink"], lw=0.35))

    _box(ax, (0.39, 0.62), 0.15, 0.16, "Case memory", COLORS["blue_soft"], "descriptor recall")
    _box(ax, (0.39, 0.37), 0.15, 0.16, "Structural memory", COLORS["red_soft"], "FGW re-ranking")
    _box(ax, (0.59, 0.50), 0.17, 0.19, "Selection gate", COLORS["red_soft"], "bounded tail correction\nor CBR default")
    _arrow(ax, (0.35, 0.66), (0.39, 0.70))
    _arrow(ax, (0.35, 0.66), (0.39, 0.45))
    _arrow(ax, (0.54, 0.70), (0.59, 0.61))
    _arrow(ax, (0.54, 0.45), (0.59, 0.57))

    _box(ax, (0.80, 0.43), 0.18, 0.34, "Recommendation card", COLORS["blue_soft"], None)
    ax.text(0.825, 0.63, "pressure      6.2", fontsize=6.2, weight="bold", color=COLORS["red"])
    ax.text(0.825, 0.56, "velocity       0.8", fontsize=6.2, weight="bold", color=COLORS["blue"])
    ax.text(0.825, 0.49, "verify      6.1-6.3", fontsize=6.0, color=COLORS["ink"])
    ax.text(0.825, 0.44, "evidence + review flag", fontsize=5.4, color=COLORS["muted"])
    _arrow(ax, (0.76, 0.59), (0.80, 0.59))
    ax.text(0.50, 0.17, "Active pressure search: 5.0-8.0 in 0.1 steps", ha="center", fontsize=6.0, color=COLORS["red"], weight="bold")
    ax.text(0.50, 0.10, "Empirical velocity anchor: default 0.8; engineer override allowed", ha="center", fontsize=5.8, color=COLORS["blue"], weight="bold")
    ax.text(0.50, 0.02, "Retrospective decision support for rapid verification; not autonomous quality optimization", ha="center", fontsize=5.5, color=COLORS["muted"])

    metrics = fig.add_subplot(gs[1])
    metrics.set_axis_off()
    cbr_mae, safe_mae = float(cbr["pressure_mae_raw"]), float(safe["pressure_mae_raw"])
    cbr_median, safe_median = float(cbr["pressure_median_abs_error_raw"]), float(safe["pressure_median_abs_error_raw"])
    cbr_02, safe_02 = 100 * float(cbr["within_0_2_raw_rate"]), 100 * float(safe["within_0_2_raw_rate"])
    cbr_04, safe_04 = 100 * float(cbr["within_0_4_raw_rate"]), 100 * float(safe["within_0_4_raw_rate"])
    metric_rows = [
        ("Pressure MAE", cbr_mae, safe_mae, f"{100 * (cbr_mae - safe_mae) / cbr_mae:.1f}% lower"),
        ("Median error", cbr_median, safe_median, f"{100 * (cbr_median - safe_median) / cbr_median:.1f}% lower"),
        ("Within +/-0.2", cbr_02, safe_02, f"{safe_02 - cbr_02:+.1f} pp"),
        ("Within +/-0.4", cbr_04, safe_04, f"{safe_04 - cbr_04:+.1f} pp"),
    ]
    for idx, (label, baseline, ours, delta) in enumerate(metric_rows):
        x = 0.015 + idx * 0.247
        metrics.add_patch(FancyBboxPatch((x, 0.08), 0.225, 0.82, boxstyle="round,pad=0.01,rounding_size=0.02", facecolor="#FAFBFC", edgecolor=COLORS["neutral_mid"], lw=0.6))
        metrics.text(x + 0.015, 0.72, label, fontsize=6.0, weight="bold")
        metrics.text(x + 0.015, 0.46, f"CBR  {baseline:.3g}", fontsize=5.6, color=COLORS["blue"])
        metrics.text(x + 0.015, 0.27, f"KOTMA-SR  {ours:.3g}", fontsize=5.6, color=COLORS["red"], weight="bold")
        metrics.text(x + 0.205, 0.16, delta, ha="right", fontsize=5.5, color=COLORS["red"], weight="bold")
    source = pd.DataFrame(metric_rows, columns=["metric", "CBR", "KOTMA-SR", "display_delta"])
    source["profile"] = profile
    save_pub(fig, output_dir / "Fig1_Graphical_Abstract", source)


def plot_fig2_architecture(profile: str, output_dir: Path) -> None:
    set_publication_style()
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.5, 0.97, "Layered knowledge architecture for leakage-safe first-article reasoning", ha="center", fontsize=9, weight="bold")
    ax.text(0.03, 0.87, "Knowledge inputs", color=COLORS["blue"], fontsize=6.5, weight="bold")
    ax.text(0.31, 0.87, "Representations", color=COLORS["blue"], fontsize=6.5, weight="bold")
    ax.text(0.56, 0.87, "Selective reasoner", color=COLORS["red"], fontsize=6.5, weight="bold")
    ax.text(0.83, 0.87, "Engineer-facing card", color=COLORS["blue"], fontsize=6.5, weight="bold")
    left = [
        ("PCB geometry", "pads, dimensions,\nshape distribution", 0.68),
        ("Process policy", "pressure active;\nvelocity anchored", 0.46),
        ("Historical cases", "executed pressure;\nSPI hidden at query", 0.24),
    ]
    for text, sub, y in left:
        _box(ax, (0.03, y), 0.19, 0.14, text, COLORS["blue_soft"], sub)
    reps = [
        ("Descriptor", "fold-local scaling", 0.63),
        ("Super-node graph", "physics-aware PCB", 0.36),
    ]
    for text, sub, y in reps:
        _box(ax, (0.30, y), 0.19, 0.17, text, COLORS["neutral"], sub)
    _box(ax, (0.56, 0.65), 0.20, 0.14, "CBR safeguard", COLORS["blue_soft"], "auditable nearest case")
    _box(ax, (0.56, 0.45), 0.20, 0.14, "FGW tail correction", COLORS["red_soft"], "bounded structural update")
    _box(ax, (0.56, 0.25), 0.20, 0.14, "Trust gate", COLORS["red_soft"], "interval, OOD, review")
    _box(ax, (0.82, 0.38), 0.16, 0.27, "Recommendation", COLORS["blue_soft"], "pressure + velocity\nwindow + evidence")
    for y in [0.75, 0.53, 0.31]:
        _arrow(ax, (0.22, y), (0.30, 0.72 if y > 0.55 else 0.45))
    _arrow(ax, (0.49, 0.72), (0.56, 0.72))
    _arrow(ax, (0.49, 0.45), (0.56, 0.52))
    _arrow(ax, (0.66, 0.65), (0.66, 0.59))
    _arrow(ax, (0.66, 0.45), (0.66, 0.39))
    _arrow(ax, (0.76, 0.32), (0.82, 0.50))
    ax.text(0.50, 0.10, "All scaling, tuning, calibration and review thresholds remain inside training folds", ha="center", fontsize=6.2, color=COLORS["red"], weight="bold")
    ax.text(0.50, 0.04, "Outer held-out PCB outcomes are revealed only once for retrospective evaluation", ha="center", fontsize=5.7, color=COLORS["muted"])
    source = pd.DataFrame(
        [
            {"layer": "input", "module": "PCB geometry"},
            {"layer": "input", "module": "process policy"},
            {"layer": "input", "module": "historical cases"},
            {"layer": "representation", "module": "descriptor"},
            {"layer": "representation", "module": "super-node graph"},
            {"layer": "reasoner", "module": "CBR safeguard"},
            {"layer": "reasoner", "module": "bounded FGW tail correction"},
            {"layer": "reasoner", "module": "trust gate"},
            {"layer": "output", "module": "recommendation card"},
        ]
    )
    source["profile"] = profile
    save_pub(fig, output_dir / "Fig2_Knowledge_Architecture", source)


def plot_fig3_process_knowledge(records, output_dir: Path) -> None:
    set_publication_style()
    data = _board_frame(records)
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.5), gridspec_kw={"width_ratios": [1.05, 1.05, 1.25]})
    _panel(axes[0], "a", "Pressure remains active")
    sns.histplot(data=data, x="pressure", discrete=True, color=COLORS["red"], ax=axes[0])
    axes[0].set_xlabel("Executed pressure")
    axes[0].set_ylabel("PCB sides")
    axes[0].axvspan(5.0, 8.0, color=COLORS["red_soft"], alpha=0.25, zorder=-1)
    _panel(axes[1], "b", "Velocity is empirically anchored")
    counts = data["velocity"].value_counts().sort_index()
    axes[1].bar(counts.index.astype(str), counts.values, color=[COLORS["blue"] if v == 0.8 else COLORS["blue_mid"] for v in counts.index])
    axes[1].set_xlabel("Executed velocity")
    axes[1].set_ylabel("PCB sides")
    axes[1].text(0.98, 0.94, f"{int((data['velocity'] == 0.8).sum())}/{len(data)} at 0.8", ha="right", va="top", transform=axes[1].transAxes, fontsize=5.8, color=COLORS["blue"], weight="bold")
    _panel(axes[2], "c", "Asymmetric recommendation space")
    axes[2].set_xlim(4.9, 8.1)
    axes[2].set_ylim(-0.05, 1.05)
    axes[2].hlines(0.70, 5.0, 8.0, color=COLORS["red"], lw=3)
    for x in np.arange(5.0, 8.01, 0.1):
        axes[2].vlines(x, 0.66, 0.74, color=COLORS["red_mid"], lw=0.45)
    axes[2].scatter(data["pressure"], np.full(len(data), 0.70), s=10, color=COLORS["red"], alpha=0.55)
    axes[2].hlines(0.28, 5.0, 8.0, color=COLORS["blue_mid"], lw=1)
    axes[2].scatter([6.5], [0.28], marker="s", s=65, color=COLORS["blue"], edgecolor="white", lw=0.5)
    axes[2].text(6.5, 0.14, "velocity locked to 0.8\n(engineer override allowed)", ha="center", fontsize=5.6, color=COLORS["blue"], weight="bold")
    axes[2].text(6.5, 0.84, "pressure search: 5.0-8.0, step 0.1", ha="center", fontsize=5.6, color=COLORS["red"], weight="bold")
    axes[2].set_xticks([5, 6, 7, 8])
    axes[2].set_yticks([])
    axes[2].set_xlabel("Executable process-setting axis")
    sns.despine(ax=axes[2], left=True)
    fig.tight_layout(w_pad=1.5)
    save_pub(fig, output_dir / "Fig3_Process_Knowledge", data)


def plot_fig4_structural_memory(records, engine, output_dir: Path) -> None:
    set_publication_style()
    boards = []
    seen = set()
    for record in records:
        if record.board_id not in seen:
            boards.append(record)
            seen.add(record.board_id)
        if len(boards) >= 2:
            break
    left, right = boards
    pos_a, feat_a, weight_a = left.ot_repr
    pos_b, feat_b, weight_b = right.ot_repr
    engine.compute_fgw_distance(left.ot_repr, right.ot_repr)
    coupling = np.asarray(engine.last_transport_plan)
    if coupling.ndim != 2 or coupling.shape != (len(weight_a), len(weight_b)):
        coupling = np.outer(np.asarray(weight_a), np.asarray(weight_b))
    fig = plt.figure(figsize=(7.2, 3.0))
    gs = fig.add_gridspec(1, 4, width_ratios=[1.15, 1.05, 1.25, 1.00], wspace=0.34)
    ax0, ax1, ax2, ax3 = [fig.add_subplot(gs[0, i]) for i in range(4)]
    _panel(ax0, "a", "Raw pad geometry")
    pads = np.asarray(left.comps_raw)
    pick = np.linspace(0, len(pads) - 1, min(450, len(pads)), dtype=int)
    ax0.scatter(pads[pick, 0], pads[pick, 1], s=3, color=COLORS["blue_mid"], alpha=0.55)
    ax0.set_xlabel("Normalized x")
    ax0.set_ylabel("Normalized y")
    _panel(ax1, "b", "Physics-aware super-nodes")
    ax1.scatter(pos_a[:, 0], pos_a[:, 1], s=10 + 900 * np.asarray(weight_a), color=COLORS["red"], alpha=0.75, edgecolor="white", lw=0.25)
    ax1.set_xlabel("Normalized x")
    ax1.set_yticks([])
    _panel(ax2, "c", "FGW alignment")
    ax2.scatter(pos_a[:, 0], pos_a[:, 1], s=8 + 500 * np.asarray(weight_a), color=COLORS["blue"], alpha=0.8)
    ax2.scatter(pos_b[:, 0] + 1.20, pos_b[:, 1], s=8 + 500 * np.asarray(weight_b), color=COLORS["red"], alpha=0.8)
    flat = np.argsort(coupling.ravel())[-min(30, coupling.size):]
    for flat_idx in flat:
        i, j = np.unravel_index(flat_idx, coupling.shape)
        strength = float(coupling[i, j] / (np.max(coupling) + 1e-12))
        ax2.plot([pos_a[i, 0], pos_b[j, 0] + 1.20], [pos_a[i, 1], pos_b[j, 1]], color=COLORS["red_mid"], alpha=0.08 + 0.38 * strength, lw=0.25 + 0.75 * strength)
    ax2.text(0.05, 0.96, "query", transform=ax2.transAxes, fontsize=5.6, color=COLORS["blue"], weight="bold")
    ax2.text(0.82, 0.96, "case", transform=ax2.transAxes, fontsize=5.6, color=COLORS["red"], weight="bold")
    ax2.set_xticks([])
    ax2.set_yticks([])
    sns.despine(ax=ax2, left=True, bottom=True)
    _panel(ax3, "d", "Conditional use")
    ax3.set_axis_off()
    _box(ax3, (0.04, 0.69), 0.90, 0.16, "Descriptor recall", COLORS["blue_soft"], "stable candidate pool", fontsize=5.8)
    _box(ax3, (0.04, 0.43), 0.90, 0.16, "FGW re-ranking", COLORS["red_soft"], "structure-sensitive evidence", fontsize=5.8)
    _box(ax3, (0.04, 0.17), 0.90, 0.16, "Bounded correction", COLORS["red_soft"], "only for sparse tails", fontsize=5.8)
    _arrow(ax3, (0.49, 0.69), (0.49, 0.59), color=COLORS["ink"])
    _arrow(ax3, (0.49, 0.43), (0.49, 0.33), color=COLORS["ink"])
    fig.tight_layout(w_pad=1.1)
    edge_rows = []
    for flat_idx in flat:
        i, j = np.unravel_index(flat_idx, coupling.shape)
        edge_rows.append(
            {
                "panel": "fgw_alignment",
                "query_node": i,
                "case_node": j,
                "coupling": coupling[i, j],
            }
        )
    source = pd.concat(
        [
            pd.DataFrame({"panel": "raw_pads", "x": pads[pick, 0], "y": pads[pick, 1]}),
            pd.DataFrame({"panel": "query_supernodes", "x": pos_a[:, 0], "y": pos_a[:, 1], "weight": weight_a}),
            pd.DataFrame({"panel": "case_supernodes", "x": pos_b[:, 0], "y": pos_b[:, 1], "weight": weight_b}),
            pd.DataFrame(edge_rows),
        ],
        ignore_index=True,
        sort=False,
    )
    save_pub(fig, output_dir / "Fig4_Structural_Memory", source)


def plot_fig5_safeguard(cases: pd.DataFrame, traces: pd.DataFrame, output_dir: Path) -> None:
    set_publication_style()
    fig = plt.figure(figsize=(7.2, 3.35))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.05, 1.0], hspace=0.47, wspace=0.75)
    ax = fig.add_subplot(gs[0, :])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.5, 1.03, "Sparse-tail bounded gate: enhance only when historical support is weak", ha="center", fontsize=8.8, weight="bold")
    _box(ax, (0.03, 0.38), 0.17, 0.28, "Descriptor CBR", COLORS["blue_soft"], "auditable nearest case")
    _box(ax, (0.27, 0.38), 0.18, 0.28, "Support audit", COLORS["neutral"], "fold-local pressure count")
    _box(ax, (0.54, 0.58), 0.19, 0.22, "CBR default", COLORS["blue_soft"], "retain supported case")
    _box(ax, (0.54, 0.19), 0.19, 0.22, "Bounded correction", COLORS["red_soft"], "FGW update <= 0.5")
    _box(ax, (0.81, 0.38), 0.16, 0.28, "Executable grid", COLORS["red_soft"], "round to 0.1 step")
    _arrow(ax, (0.20, 0.52), (0.27, 0.52))
    _arrow(ax, (0.45, 0.56), (0.54, 0.67), color=COLORS["blue"])
    _arrow(ax, (0.45, 0.48), (0.54, 0.30), color=COLORS["red"])
    _arrow(ax, (0.73, 0.67), (0.81, 0.56))
    _arrow(ax, (0.73, 0.30), (0.81, 0.48))
    ax.text(0.46, 0.69, "supported", fontsize=5.5, color=COLORS["blue"], weight="bold")
    ax.text(0.46, 0.31, "sparse tail", fontsize=5.5, color=COLORS["red"], weight="bold")

    ax1 = fig.add_subplot(gs[1, :2])
    _panel(ax1, "a", "Selective action frequency", label_x=-0.06)
    action_counts = traces["safety_action"].replace({"descriptor_cbr_safeguard": "CBR default", "bounded_structural_tail_correction": "bounded correction"}).value_counts()
    ax1.bar(action_counts.index, action_counts.values, color=[COLORS["blue"], COLORS["red"]])
    ax1.set_ylabel("PCB sides")
    ax1.tick_params(axis="x", rotation=12)
    ax2 = fig.add_subplot(gs[1, 2:])
    _panel(ax2, "b", "Board-level gain from bounded gate", label_x=-0.06)
    ordered = cases.sort_values("gain_vs_cbr_raw")
    colors = np.where(ordered["gain_vs_cbr_raw"] >= -1e-9, COLORS["red"], COLORS["blue"])
    ax2.axvline(0, color=COLORS["neutral_mid"], lw=0.8)
    ax2.scatter(ordered["gain_vs_cbr_raw"], np.arange(len(ordered)), c=colors, s=11)
    ax2.set_xlabel("CBR error - KOTMA-SR error")
    ax2.set_ylabel("Held-out PCB sides")
    ax2.set_yticks([])
    fig.tight_layout(w_pad=1.0)
    source = pd.concat([cases.assign(panel="board_gain"), traces.assign(panel="trace")], ignore_index=True, sort=False)
    save_pub(fig, output_dir / "Fig5_Sparse_Tail_Gate", source)


def plot_fig6_validation_system(output_dir: Path, n_sides: int = 34, n_physical_boards: int = 21) -> None:
    set_publication_style()
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.5, 0.96, "Leakage-safe validation system for sparse production histories", ha="center", fontsize=9, weight="bold")
    _box(ax, (0.04, 0.62), 0.18, 0.18, f"{n_sides} PCB sides", COLORS["blue_soft"], f"{n_physical_boards} physical boards")
    _box(ax, (0.30, 0.62), 0.18, 0.18, "Outer grouped LOBO", COLORS["red_soft"], "hold out both A/B sides")
    _box(ax, (0.56, 0.62), 0.18, 0.18, "Inner grouped LOBO", COLORS["blue_soft"], "tune only on histories")
    _box(ax, (0.81, 0.62), 0.15, 0.18, "One reveal", COLORS["red_soft"], "outer evaluation")
    _arrow(ax, (0.22, 0.71), (0.30, 0.71))
    _arrow(ax, (0.48, 0.71), (0.56, 0.71))
    _arrow(ax, (0.74, 0.71), (0.81, 0.71))
    ax.text(0.50, 0.52, "Outer outcomes never enter scaling, tuning, calibration or recommendation", ha="center", fontsize=6.1, color=COLORS["red"], weight="bold")
    cards = [
        ("Baselines", "CBR, median,\nunconstrained OT", 0.05, COLORS["blue_soft"]),
        ("Ablations", "FGW, safeguard,\nbounded update", 0.25, COLORS["red_soft"]),
        ("Small-sample", "5, 10, 20,\nall histories", 0.45, COLORS["blue_soft"]),
        ("Controls", "random memory,\npad-count only", 0.65, COLORS["red_soft"]),
        ("Trust", "intervals, OOD,\nreview, latency", 0.85, COLORS["blue_soft"]),
    ]
    for text, sub, x, color in cards:
        _box(ax, (x, 0.17), 0.13, 0.20, text, color, sub, fontsize=5.7)
    ax.text(0.5, 0.06, "Evidence matrix: performance + mechanism + robustness + transparency", ha="center", fontsize=6.1, color=COLORS["ink"], weight="bold")
    source = pd.DataFrame([{"experiment": text, "detail": sub.replace("\n", " "), "n_sides": n_sides, "n_physical_boards": n_physical_boards} for text, sub, _, _ in cards])
    save_pub(fig, output_dir / "Fig6_Validation_System", source)


def plot_fig7_primary_results(results: pd.DataFrame, paired: pd.DataFrame, output_dir: Path) -> None:
    set_publication_style()
    fig = plt.figure(figsize=(7.2, 3.25))
    gs = fig.add_gridspec(1, 4, width_ratios=[1.15, 1.30, 1.20, 0.92], wspace=0.62)
    axes = [fig.add_subplot(gs[0, i]) for i in range(4)]
    means = results.groupby("method", as_index=False)["pressure_abs_error_raw"].mean().sort_values("pressure_abs_error_raw")
    _panel(axes[0], "a", "Pressure recovery MAE")
    axes[0].barh(means["method"], means["pressure_abs_error_raw"], color=[COLORS.get(m, COLORS["neutral_mid"]) for m in means["method"]])
    axes[0].invert_yaxis()
    axes[0].set_xlabel("MAE")
    rates = results.groupby("method", as_index=False)[["within_0_2_raw", "within_0_4_raw"]].mean()
    _panel(axes[1], "b", "Engineering-window recovery")
    x = np.arange(len(rates))
    axes[1].bar(x - 0.16, 100 * rates["within_0_2_raw"], width=0.32, color=COLORS["red"], label="+/-0.2")
    axes[1].bar(x + 0.16, 100 * rates["within_0_4_raw"], width=0.32, color=COLORS["blue"], label="+/-0.4")
    axes[1].set_xticks(x, rates["method"], rotation=50, ha="right")
    axes[1].set_ylabel("PCB sides (%)")
    axes[1].legend(loc="lower left")
    wide = results.pivot(index="board_id", columns="method", values="pressure_abs_error_raw")
    _panel(axes[2], "c", "Paired difference vs CBR")
    delta = (wide["CBR"] - wide["KOTMA-SR"]).sort_values()
    axes[2].axvline(0, color=COLORS["neutral_mid"], lw=0.8)
    axes[2].scatter(delta, np.arange(len(delta)), c=np.where(delta >= -1e-9, COLORS["red"], COLORS["blue"]), s=12)
    axes[2].set_xlabel("CBR error - KOTMA-SR error")
    axes[2].set_yticks([])
    _panel(axes[3], "d", "Reviewer-facing statistics")
    axes[3].set_axis_off()
    row = paired[paired["comparator"].eq("CBR")].iloc[0]
    text = (
        f"mean gain  {row['mean_advantage_raw']:.3f}\n"
        f"Wilcoxon p  {row['p_wilcoxon']:.3f}\n"
        f"bootstrap P  {100 * row['prob_reference_better_bootstrap']:.1f}%\n"
        f"win/tie/loss  {int(row['reference_wins'])}/{int(row['ties'])}/{int(row['comparator_wins'])}"
    )
    axes[3].text(0.02, 0.78, text, va="top", fontsize=6.4, linespacing=1.65)
    axes[3].text(0.02, 0.18, "Paired analysis is\nreported transparently;\nCI remains disclosed.", fontsize=5.6, color=COLORS["muted"])
    fig.tight_layout(w_pad=1.1)
    source = pd.concat([results.assign(panel="outer_lobo"), paired.assign(panel="paired_statistics")], ignore_index=True, sort=False)
    save_pub(fig, output_dir / "Fig7_Primary_Results", source)


def plot_fig8_trust(selective: pd.DataFrame, intervals: pd.DataFrame, traces: pd.DataFrame, output_dir: Path) -> None:
    set_publication_style()
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.55))
    _panel(axes[0], "a", "Coverage-risk curve")
    valid = selective.dropna(subset=["pressure_mae_raw"])
    axes[0].plot(100 * valid["coverage"], valid["pressure_mae_raw"], marker="o", ms=3, color=COLORS["red"])
    axes[0].set_xlabel("Accepted coverage (%)")
    axes[0].set_ylabel("Accepted MAE")
    _panel(axes[1], "b", "Interval calibration")
    x = np.arange(len(intervals))
    axes[1].bar(x - 0.16, 100 * intervals["nominal_coverage"], width=0.32, color=COLORS["blue_mid"], label="nominal")
    axes[1].bar(x + 0.16, 100 * intervals["empirical_coverage"], width=0.32, color=COLORS["red"], label="empirical")
    axes[1].set_xticks(x, [f"{int(100*v)}%" for v in intervals["nominal_coverage"]])
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel("Coverage (%)")
    axes[1].legend()
    _panel(axes[2], "c", "Confidence and support")
    axes[2].scatter(traces["effective_neighbor_count"], traces["confidence"], c=np.where(traces["manual_review"], COLORS["red"], COLORS["blue"]), s=16, edgecolor="white", lw=0.25)
    axes[2].set_xlabel("Effective neighbors")
    axes[2].set_ylabel("Confidence")
    _panel(axes[3], "d", "Review triggers")
    reasons = traces["review_reasons"].fillna("").str.split(";").explode()
    counts = reasons[reasons.ne("")].value_counts()
    if counts.empty:
        counts = pd.Series({"none": 0})
    axes[3].barh(counts.index, counts.values, color=COLORS["red_mid"])
    axes[3].set_xlabel("PCB sides")
    fig.tight_layout(w_pad=1.25)
    source = pd.concat([selective.assign(panel="risk"), intervals.assign(panel="interval"), traces.assign(panel="trace")], ignore_index=True, sort=False)
    save_pub(fig, output_dir / "Fig8_Trust_Calibration", source)


def plot_fig9_evidence_matrix(ablation: pd.DataFrame, robustness: pd.DataFrame, sample: pd.DataFrame, controls: pd.DataFrame, output_dir: Path) -> None:
    set_publication_style()
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.65))
    _panel(axes[0], "a", "Clean ablation")
    abl = ablation.groupby("method", as_index=False)["pressure_abs_error_raw"].mean().sort_values("pressure_abs_error_raw")
    axes[0].barh(abl["method"], abl["pressure_abs_error_raw"], color=[COLORS["red"] if m == "Sparse-tail correction" else COLORS["blue_mid"] for m in abl["method"]])
    axes[0].invert_yaxis()
    axes[0].set_xlabel("MAE")
    _panel(axes[1], "b", "Geometry perturbation")
    rob = robustness.groupby("perturbation_pct", as_index=False)["recommended_pressure_shift_raw"].mean()
    axes[1].plot(100 * rob["perturbation_pct"], rob["recommended_pressure_shift_raw"], marker="o", color=COLORS["red"], ms=3)
    axes[1].set_xlabel("Geometry perturbation (%)")
    axes[1].set_ylabel("Recommendation shift")
    _panel(axes[2], "c", "Small-sample degradation")
    sam = sample.groupby(["method", "train_boards"], as_index=False)["pressure_abs_error_raw"].mean()
    for method, frame in sam.groupby("method"):
        axes[2].plot(frame["train_boards"], frame["pressure_abs_error_raw"], marker="o", ms=3, color=COLORS["red"] if method == "KOTMA-SR" else COLORS["blue"], label=method)
    axes[2].set_xlabel("Historical PCB sides")
    axes[2].set_ylabel("MAE")
    axes[2].legend()
    _panel(axes[3], "d", "Negative controls")
    neg = controls.groupby("method", as_index=False)["pressure_abs_error_raw"].mean().sort_values("pressure_abs_error_raw")
    axes[3].barh(neg["method"], neg["pressure_abs_error_raw"], color=[COLORS["red"] if m == "KOTMA-SR" else COLORS["blue_mid"] for m in neg["method"]])
    axes[3].invert_yaxis()
    axes[3].set_xlabel("MAE")
    fig.tight_layout(w_pad=1.1)
    source = pd.concat(
        [
            ablation.assign(panel="ablation"),
            robustness.assign(panel="robustness"),
            sample.assign(panel="sample_efficiency"),
            controls.assign(panel="negative_control"),
        ],
        ignore_index=True,
        sort=False,
    )
    save_pub(fig, output_dir / "Fig9_Evidence_Matrix", source)


def write_figure_manifest(profile: str, output_dir: Path) -> pd.DataFrame:
    claims = [
        ("Fig1_Graphical_Abstract", "opening", "The complete innovation and measured effect are visible in one opening figure."),
        ("Fig2_Knowledge_Architecture", "method", "Explicit process knowledge, structural memory and selective reasoning form one auditable architecture."),
        ("Fig3_Process_Knowledge", "innovation", "Pressure is actively recommended while velocity remains empirically anchored."),
        ("Fig4_Structural_Memory", "innovation", "PCB graph structure provides conditional evidence beyond tabular recall."),
        ("Fig5_Sparse_Tail_Gate", "innovation", "Structural reasoning modifies CBR only for fold-local sparse tails."),
        ("Fig6_Validation_System", "validation_design", "Nested LOBO separates tuning, calibration and held-out evaluation."),
        ("Fig7_Primary_Results", "validation", "KOTMA-SR improves retrospective pressure recovery against CBR."),
        ("Fig8_Trust_Calibration", "trust", "Risk-coverage, interval calibration and review triggers are disclosed."),
        ("Fig9_Evidence_Matrix", "robustness", "Ablation, perturbation, small-sample and negative-control evidence define the method boundary."),
    ]
    rows = []
    for figure, role, claim in claims:
        rows.append(
            {
                "profile": profile,
                "figure": figure,
                "role": role,
                "claim": claim,
                "source_data": f"{figure}_SourceData.csv",
                "svg_exists": int((output_dir / f"{figure}.svg").exists()),
                "pdf_exists": int((output_dir / f"{figure}.pdf").exists()),
                "tiff_exists": int((output_dir / f"{figure}.tiff").exists()),
                "png_exists": int((output_dir / f"{figure}.png").exists()),
            }
        )
    manifest = pd.DataFrame(rows)
    manifest.to_csv(output_dir / "figure_manifest.csv", index=False)
    return manifest


def generate_profile_figures(profile: str, records, artifacts: dict[str, pd.DataFrame], output_dir: str | Path, engine=None) -> pd.DataFrame:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_fig1_graphical_abstract(profile, artifacts["summary"], artifacts["traces"], output_dir)
    plot_fig2_architecture(profile, output_dir)
    plot_fig3_process_knowledge(records, output_dir)
    plot_fig4_structural_memory(records, engine, output_dir)
    plot_fig5_safeguard(artifacts["cases"], artifacts["traces"], output_dir)
    safe = artifacts["summary"].set_index("method").loc["KOTMA-SR"]
    plot_fig6_validation_system(output_dir, int(safe.get("n_sides", safe.get("n_boards", 34))), int(safe.get("n_physical_boards", 21)))
    plot_fig7_primary_results(artifacts["results"], artifacts["paired"], output_dir)
    plot_fig8_trust(artifacts["selective"], artifacts["intervals"], artifacts["traces"], output_dir)
    plot_fig9_evidence_matrix(artifacts["ablation"], artifacts["robustness"], artifacts["sample_efficiency"], artifacts["negative_controls"], output_dir)
    return write_figure_manifest(profile, output_dir)

