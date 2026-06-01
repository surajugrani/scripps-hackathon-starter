#!/usr/bin/env python3
"""
Generate all figures as PNGs into ppt/ directory.
Run from project root.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import json
import glob
from pathlib import Path
from scipy import stats

# ── Dark theme palette ─────────────────────────────────────────────────────
DARK_BG   = "#1A1A2E"
MID_BG    = "#16213E"
ACCENT    = "#0F3A67"
BOLTZ     = "#2E86AB"   # teal
AF3A      = "#A23B72"   # magenta
AF3B      = "#F18F01"   # amber
WHITE     = "#FFFFFF"
LGRAY     = "#CCCCCC"
DGRAY     = "#888888"

def setup_dark(fig, axes=None):
    fig.patch.set_facecolor(DARK_BG)
    if axes is None:
        return
    if not hasattr(axes, '__iter__'):
        axes = [axes]
    for ax in axes:
        ax.set_facecolor(MID_BG)
        ax.tick_params(colors=WHITE)
        ax.xaxis.label.set_color(WHITE)
        ax.yaxis.label.set_color(WHITE)
        ax.title.set_color(WHITE)
        for spine in ax.spines.values():
            spine.set_edgecolor("#444466")

OUT = Path("ppt")


# ═══════════════════════════════════════════════════════════════════════════
# Figure 1 – Confidence Rankings
# ═══════════════════════════════════════════════════════════════════════════
def fig_confidence_ranking():
    # Load data
    boltz = pd.read_csv("analysis/01_confidence/confidence_ranking.csv")
    af3a  = pd.read_csv("analysis/af3/confidence_af3msa.csv")
    af3b  = pd.read_csv("analysis/af3/confidence_colabfoldmsa.csv")

    # Load Boltz-2 affinity from JSON files
    aff_data = {}
    for jf in glob.glob("analysis/results/*/boltz_results_*/predictions/*/affinity_*.json"):
        parts = Path(jf).parts
        # slug is the 3rd part from 'analysis/results/<slug>/...'
        slug = parts[2]  # analysis/results/cpd_1/...
        with open(jf) as f:
            d = json.load(f)
        aff_data[slug] = d["affinity_pred_value"]

    # Sort by Boltz-2 iPTM descending
    boltz_sorted = boltz.sort_values("iptm", ascending=False)
    ligands = boltz_sorted["ligand"].tolist()

    # Lookup dicts
    af3a_map = dict(zip(af3a["ligand"], af3a["iptm"]))
    af3b_map = dict(zip(af3b["ligand"], af3b["iptm"]))
    boltz_map = dict(zip(boltz["ligand"], boltz["iptm"]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    setup_dark(fig, [ax1, ax2])

    x = np.arange(len(ligands))
    w = 0.26
    bar_kwargs = dict(edgecolor="none", zorder=3)

    # Left subplot: grouped iPTM bars
    b1 = ax1.bar(x - w, [boltz_map.get(l, 0) for l in ligands], w, label="Boltz-2", color=BOLTZ, **bar_kwargs)
    b2 = ax1.bar(x,     [af3a_map.get(l, 0)  for l in ligands], w, label="AF3-MSA", color=AF3A, **bar_kwargs)
    b3 = ax1.bar(x + w, [af3b_map.get(l, 0)  for l in ligands], w, label="AF3-ColabFold", color=AF3B, **bar_kwargs)

    # SA dashed reference lines
    sa_boltz = boltz_map.get("sa", 0)
    sa_af3a  = af3a_map.get("sa", 0)
    sa_af3b  = af3b_map.get("sa", 0)
    ax1.axhline(sa_boltz, ls="--", lw=1.2, color=BOLTZ, alpha=0.6)
    ax1.axhline(sa_af3a,  ls="--", lw=1.2, color=AF3A,  alpha=0.6)
    ax1.axhline(sa_af3b,  ls="--", lw=1.2, color=AF3B,  alpha=0.6)

    # Annotate lines
    ax1.text(len(ligands)-0.5, sa_boltz+0.003, "sa Boltz", color=BOLTZ, fontsize=7.5)
    ax1.text(len(ligands)-0.5, sa_af3a+0.003,  "sa AF3-MSA", color=AF3A, fontsize=7.5)
    ax1.text(len(ligands)-0.5, sa_af3b+0.003,  "sa CF", color=AF3B, fontsize=7.5)

    ax1.set_xticks(x)
    ax1.set_xticklabels(ligands, rotation=45, ha="right", fontsize=9, color=WHITE)
    ax1.set_ylabel("iPTM score", color=WHITE, fontsize=11)
    ax1.set_title("iPTM Confidence — All 3 Methods", color=WHITE, fontsize=13, pad=10)
    ax1.legend(fontsize=9, facecolor=MID_BG, labelcolor=WHITE, edgecolor="#444466")
    ax1.set_ylim(0.5, 1.02)
    ax1.grid(axis="y", alpha=0.2, color=LGRAY)
    ax1.yaxis.set_tick_params(labelcolor=WHITE)

    # Right subplot: Boltz-2 predicted affinity
    # Exclude 'sa' since it may not have affinity or it's not in cpd list
    cpd_ligands = [l for l in ligands]
    aff_vals = [aff_data.get(l, np.nan) for l in cpd_ligands]

    # Color by affinity value (blue scale)
    norm_vals = np.array([v if not np.isnan(v) else 0 for v in aff_vals])
    cmap = plt.cm.Blues_r
    vmin, vmax = min(norm_vals), max(norm_vals)
    if vmax == vmin:
        vmax = vmin + 1
    colors2 = [cmap(0.3 + 0.7*(v - vmin)/(vmax - vmin)) for v in norm_vals]

    bars2 = ax2.bar(x, aff_vals, color=colors2, edgecolor="none", zorder=3)
    ax2.axhline(0, color=LGRAY, lw=0.8, ls="-", alpha=0.5)

    ax2.set_xticks(x)
    ax2.set_xticklabels(cpd_ligands, rotation=45, ha="right", fontsize=9, color=WHITE)
    ax2.set_ylabel("Boltz-2 predicted affinity (log Kd proxy)", color=WHITE, fontsize=11)
    ax2.set_title("Boltz-2 Predicted Affinity", color=WHITE, fontsize=13, pad=10)
    ax2.grid(axis="y", alpha=0.2, color=LGRAY)
    ax2.yaxis.set_tick_params(labelcolor=WHITE)

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax2, shrink=0.6, pad=0.02)
    cbar.ax.yaxis.set_tick_params(labelcolor=WHITE)
    cbar.set_label("affinity score", color=WHITE, fontsize=9)
    cbar.outline.set_edgecolor("#444466")

    fig.suptitle("Siglec-6 Cofolding — Confidence Rankings", color=WHITE, fontsize=15, y=1.01)
    plt.tight_layout()
    out_path = OUT / "fig_confidence_ranking.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close(fig)
    print(f"Saved: {out_path}")


# ═══════════════════════════════════════════════════════════════════════════
# Figure 2 – AF3 Structural Divergence
# ═══════════════════════════════════════════════════════════════════════════
def fig_af3_divergence():
    rmsd_data = {
        "cpd_1": 18.25, "cpd_2": 5.16,  "cpd_3": 10.09, "cpd_4": 29.03,
        "cpd_5": 3.60,  "cpd_6": 13.12, "cpd_7": 75.67, "cpd_8": 5.89,
        "cpd_9": 76.97, "cpd_10": 30.53,"cpd_11": 26.12,"cpd_12": 77.88,
        "cpd_13": 75.41,"sa": 12.90
    }

    ligands = list(rmsd_data.keys())
    rmsds   = list(rmsd_data.values())

    def bar_color(v):
        if v > 30:   return "#E83A3A"
        elif v > 10: return "#F18F01"
        else:        return "#44BF6E"

    colors = [bar_color(v) for v in rmsds]

    fig, ax = plt.subplots(figsize=(14, 5))
    setup_dark(fig, ax)

    x = np.arange(len(ligands))
    bars = ax.bar(x, rmsds, color=colors, edgecolor="none", zorder=3)

    # Threshold lines
    ax.axhline(30, ls="--", lw=1.2, color="#E83A3A", alpha=0.7, label=">30 Å (red)")
    ax.axhline(10, ls="--", lw=1.2, color="#F18F01", alpha=0.7, label="10–30 Å (orange)")

    ax.set_xticks(x)
    ax.set_xticklabels(ligands, rotation=45, ha="right", fontsize=10, color=WHITE)
    ax.set_ylabel("Cα RMSD between AF3-MSA and AF3-ColabFold (Å)", color=WHITE, fontsize=11)
    ax.set_title("AF3 Structural Divergence: Same Confidence Score, Different Structure",
                 color=WHITE, fontsize=14, pad=12)
    ax.grid(axis="y", alpha=0.2, color=LGRAY)
    ax.yaxis.set_tick_params(labelcolor=WHITE)

    # Annotation text box
    textstr = (
        "Mean RMSD: 32.9 Å\n"
        "Max: 77.9 Å (cpd_12)\n\n"
        "iPTM divergence:\n"
        "  Mean |ΔiPTM| = 0.034\n"
        "  Max |ΔiPTM| = 0.08 (cpd_1)\n"
        "  Spearman ρ = 0.60"
    )
    props = dict(boxstyle="round", facecolor=MID_BG, edgecolor="#444466", alpha=0.9)
    ax.text(0.97, 0.97, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment="top", horizontalalignment="right",
            bbox=props, color=WHITE)

    # Legend for colors
    red_p   = mpatches.Patch(color="#E83A3A", label=">30 Å  (strongly divergent)")
    oran_p  = mpatches.Patch(color="#F18F01", label="10–30 Å  (moderate divergence)")
    green_p = mpatches.Patch(color="#44BF6E", label="<10 Å  (similar structures)")
    ax.legend(handles=[red_p, oran_p, green_p], fontsize=9,
              facecolor=MID_BG, labelcolor=WHITE, edgecolor="#444466", loc="upper left")

    plt.tight_layout()
    out_path = OUT / "fig_af3_divergence.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close(fig)
    print(f"Saved: {out_path}")


# ═══════════════════════════════════════════════════════════════════════════
# Figure 3 – Scatter vs Kd
# ═══════════════════════════════════════════════════════════════════════════
def fig_scatter_vs_kd():
    # Kd data (uM) — compound IDs need underscore form
    kd_raw = {
        "cpd_1": 53.3, "cpd_2": 63.5, "cpd_3": 12.8, "cpd_4": 49.9,
        "cpd_5": 8.0,  "cpd_6": 92.6, "cpd_7": 16.5, "cpd_8": 40.4,
        "cpd_9": 6.5,  "cpd_10": 5.1, "cpd_11": 90.4,"cpd_12": 4.7,
        "cpd_13": 5.7
    }
    pkd = {k: 6 - np.log10(v) for k, v in kd_raw.items()}

    # Boltz-2 affinity from JSONs
    aff_data = {}
    for jf in glob.glob("analysis/results/*/boltz_results_*/predictions/*/affinity_*.json"):
        parts = Path(jf).parts
        slug = parts[2]
        with open(jf) as f:
            d = json.load(f)
        aff_data[slug] = d["affinity_pred_value"]

    def load_vina(fpath, col="vina_local_kcal_mol", id_col="ligand"):
        df = pd.read_csv(fpath)
        return dict(zip(df[id_col], df[col]))

    lo_b2  = load_vina("analysis/03_vina/results/local_only_boltz2.csv")
    lo_a3  = load_vina("analysis/03_vina/results/local_only_af3msa.csv")
    lo_ac  = load_vina("analysis/03_vina/results/local_only_af3colabfold.csv")
    rd_b2  = load_vina("analysis/03_vina/results/redock_boltz2.csv", col="vina_redock_kcal_mol")
    rd_a3  = load_vina("analysis/03_vina/results/redock_af3msa.csv", col="vina_redock_kcal_mol")
    rd_ac  = load_vina("analysis/03_vina/results/redock_af3colabfold.csv", col="vina_redock_kcal_mol")

    cpds = sorted(pkd.keys())

    def mk_xy(d, cap=None):
        xs, ys, ids = [], [], []
        for c in cpds:
            if c in pkd and c in d:
                y = d[c]
                if cap is not None and y > cap:
                    y = cap
                xs.append(pkd[c])
                ys.append(y)
                ids.append(c)
        return np.array(xs), np.array(ys), ids

    panels = [
        ("Boltz-2\nPredicted Affinity",   aff_data,  "#2E86AB",  None,  "Affinity score (higher=better)",   False),
        ("Vina Local-only\n(Boltz-2)",    lo_b2,     "#A23B72",  None,  "Vina local-only (kcal/mol)",        True),
        ("Vina Local-only\n(AF3-MSA)",    lo_a3,     "#C45BAA",  None,  "Vina local-only (kcal/mol)",        True),
        ("Vina Local-only\n(AF3-ColabFold)", lo_ac,  "#E8A0D5",  None,  "Vina local-only (kcal/mol)",        True),
        ("Vina Redock\n(Boltz-2)",         rd_b2,    "#F18F01",  None,  "Vina redock (kcal/mol)",            True),
        ("Vina Redock\n(AF3-MSA)",         rd_a3,    "#C73E1D",  None,  "Vina redock (kcal/mol)",            True),
        ("Vina Redock\n(AF3-ColabFold)",   rd_ac,    "#44BF6E",  None,  "Vina redock (kcal/mol)",            True),
    ]

    fig = plt.figure(figsize=(22, 10))
    setup_dark(fig)
    fig.patch.set_facecolor(DARK_BG)

    # 2-row layout: 4 on top, 4 on bottom (last panel is summary)
    n_panels = 7
    positions = []
    for i in range(4):
        positions.append((2, 4, i+1))      # row1 cols 1-4
    for i in range(3):
        positions.append((2, 4, i+5))      # row2 cols 1-3
    # Panel 8: summary text in row2 col4
    ax_summary = fig.add_subplot(2, 4, 8)
    ax_summary.set_facecolor(MID_BG)
    for spine in ax_summary.spines.values():
        spine.set_edgecolor("#444466")
    ax_summary.set_xticks([])
    ax_summary.set_yticks([])

    best_corrs = []

    for idx, (title, data, clr, cap, ylabel, lower_is_better) in enumerate(panels):
        ax = fig.add_subplot(positions[idx][0], positions[idx][1], positions[idx][2])
        setup_dark(fig, ax)

        xs, ys, ids = mk_xy(data, cap=cap)

        if len(xs) < 3:
            ax.set_title(title, color=WHITE, fontsize=10)
            continue

        ax.scatter(xs, ys, color=clr, s=55, zorder=4, edgecolors="none", alpha=0.9)

        # Labels
        for xi, yi, lid in zip(xs, ys, ids):
            short = lid.replace("cpd_", "c")
            ax.annotate(short, (xi, yi), textcoords="offset points", xytext=(4, 3),
                        fontsize=7, color=LGRAY)

        # Regression line
        slope, intercept, r, p, _ = stats.linregress(xs, ys)
        rho, _ = stats.spearmanr(xs, ys)
        xline = np.linspace(xs.min(), xs.max(), 100)
        ax.plot(xline, slope*xline + intercept, lw=1.5, color=WHITE, alpha=0.6, ls="--")

        # Annotation
        annot = f"r = {r:.2f}\nρ = {rho:.2f}"
        ax.text(0.05, 0.95, annot, transform=ax.transAxes, fontsize=8,
                color=WHITE, va="top",
                bbox=dict(facecolor=MID_BG, edgecolor="#444466", alpha=0.8))

        if cap is not None:
            has_capped = any(data.get(c, -999) > cap for c in cpds if c in pkd)
            if has_capped:
                ax.text(0.5, 0.02, f"capped at +{cap:.0f}", transform=ax.transAxes,
                        fontsize=7, color="#FFAA44", ha="center",
                        bbox=dict(facecolor=MID_BG, edgecolor="none", alpha=0.7))

        ax.set_xlabel("pKd (higher = tighter binding)", color=WHITE, fontsize=9)
        ax.set_ylabel(ylabel, color=WHITE, fontsize=9)
        ax.set_title(title, color=WHITE, fontsize=10, pad=6)
        ax.grid(alpha=0.15, color=LGRAY)
        ax.tick_params(colors=WHITE, labelsize=8)

        best_corrs.append((abs(r), abs(rho), title.replace("\n", " "), r, rho))

    # Summary text panel
    best_corrs.sort(reverse=True)
    summary_lines = ["Best correlations\nwith pKd:\n"]
    for _, _, name, r, rho in best_corrs[:4]:
        summary_lines.append(f"{name[:25]}\n  r={r:+.2f}, ρ={rho:+.2f}\n")
    summary_text = "\n".join(summary_lines)
    ax_summary.text(0.05, 0.95, summary_text, transform=ax_summary.transAxes,
                    fontsize=9, color=WHITE, va="top",
                    bbox=dict(facecolor=MID_BG, edgecolor="#444466", alpha=0.9))
    ax_summary.set_title("Best Correlations", color=WHITE, fontsize=10)

    fig.suptitle("Computational Scores vs Experimental Kd  (n=13 compounds)  —  Local-only replaces Score-only",
                 color=WHITE, fontsize=15, y=1.01)
    plt.tight_layout()
    out_path = OUT / "fig_scatter_vs_kd.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close(fig)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    fig_confidence_ranking()
    fig_af3_divergence()
    fig_scatter_vs_kd()
    print("All figures generated.")
