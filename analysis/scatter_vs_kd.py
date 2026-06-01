#!/usr/bin/env python3
"""
Scatter plots: computational scores vs experimental Kd values.

Panels:
  1. Boltz-2 predicted binding affinity vs Kd
  2–4. Vina score-only (Boltz-2, AF3-MSA, AF3-ColabFold) vs Kd
  5–7. Vina redock (Boltz-2, AF3-MSA, AF3-ColabFold) vs Kd

X-axis: pKd = -log10(Kd in M) = 6 - log10(Kd in µM)  [higher = tighter]
Y-axis: each score  [Boltz-2 affinity: higher = better; Vina: lower/more-negative = better]

Run from project root:
  uv run --with pandas --with matplotlib --with scipy --with numpy python3 analysis/scatter_vs_kd.py

Outputs:
  analysis/scatter_vs_kd.png   — 7-panel figure (for PPT)
  analysis/scatter_vs_kd.csv   — merged data table
"""
import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr

# ── paths ──────────────────────────────────────────────────────────────────
ROOT       = Path(".")
KD_CSV     = ROOT / "analysis/Singlec-6_Kd-13-values.csv"
RESULTS    = ROOT / "analysis/results"
VINA_DIR   = ROOT / "analysis/03_vina/results"
OUT_PNG    = ROOT / "analysis/scatter_vs_kd.png"
OUT_CSV    = ROOT / "analysis/scatter_vs_kd.csv"

VINA_SOURCES = ["boltz2", "af3msa", "af3colabfold"]
SOURCE_LABELS = {
    "boltz2":       "Boltz-2",
    "af3msa":       "AF3 (AF3-MSA)",
    "af3colabfold": "AF3 (ColabFold-MSA)",
}


# ── data loading ───────────────────────────────────────────────────────────

def load_kd() -> pd.DataFrame:
    df = pd.read_csv(KD_CSV)
    df["ligand"] = df["structure"].str.strip().str.replace(" ", "_")
    df["kd_uM"]  = pd.to_numeric(df["Kd (uM)"], errors="coerce")
    df["pKd"]    = 6 - np.log10(df["kd_uM"])   # pKd = -log10(Kd in M)
    return df[["ligand", "kd_uM", "pKd"]].dropna()


def load_boltz2_affinity() -> pd.DataFrame:
    rows = []
    for f in sorted(RESULTS.rglob("affinity_*.json")):
        ligand = f.parts[2]
        d = json.loads(f.read_text())
        rows.append({"ligand": ligand, "boltz2_affinity": d.get("affinity_pred_value")})
    return pd.DataFrame(rows)


def load_vina_scores(score_type: str) -> pd.DataFrame:
    """score_type: 'score_only' or 'redock'"""
    dfs = []
    for src in VINA_SOURCES:
        fname = VINA_DIR / f"{score_type}_{src}.csv"
        if not fname.exists():
            print(f"  WARNING: {fname} not found — skipping")
            continue
        df = pd.read_csv(fname)
        col = "vina_score_kcal_mol" if score_type == "score_only" else "vina_redock_kcal_mol"
        if col not in df.columns:
            # try alternate column name
            col = [c for c in df.columns if "score" in c or "redock" in c][0]
        df = df[["ligand", col]].rename(columns={col: f"{score_type}_{src}"})
        dfs.append(df)
    if not dfs:
        return pd.DataFrame(columns=["ligand"])
    result = dfs[0]
    for df in dfs[1:]:
        result = result.merge(df, on="ligand", how="outer")
    return result


# ── plotting ───────────────────────────────────────────────────────────────

def annotate_stats(ax, x, y, color="black"):
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if len(x) < 3:
        return
    r, p_r   = pearsonr(x, y)
    rho, p_s = spearmanr(x, y)
    ax.text(0.05, 0.95,
            f"r = {r:.2f}  (p={p_r:.3f})\nρ = {rho:.2f}  (p={p_s:.3f})",
            transform=ax.transAxes, fontsize=7.5, va="top",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))


def scatter_panel(ax, x, y, labels, title, xlabel, ylabel, color):
    mask = ~(np.isnan(x) | np.isnan(y))
    ax.scatter(x[mask], y[mask], color=color, edgecolors="white", s=60, zorder=3)
    for xi, yi, lab in zip(x[mask], y[mask], np.array(labels)[mask]):
        ax.annotate(lab, (xi, yi), fontsize=6.5, xytext=(3, 3),
                    textcoords="offset points", color="#444")
    # regression line
    if mask.sum() >= 3:
        m, b = np.polyfit(x[mask], y[mask], 1)
        xr = np.linspace(x[mask].min(), x[mask].max(), 100)
        ax.plot(xr, m * xr + b, "--", color=color, alpha=0.5, lw=1.2)
    ax.set_title(title, fontsize=9, fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.25, lw=0.5)
    annotate_stats(ax, x, y)


def main():
    kd = load_kd()
    boltz_aff = load_boltz2_affinity()
    score_only = load_vina_scores("score_only")
    redock     = load_vina_scores("redock")

    # Merge everything on ligand
    merged = kd.copy()
    for df in [boltz_aff, score_only, redock]:
        if not df.empty:
            merged = merged.merge(df, on="ligand", how="left")

    merged.to_csv(OUT_CSV, index=False)
    print(f"Merged data → {OUT_CSV}")
    print(merged.to_string(index=False))

    # ── figure: 7 panels in 2 rows (4 top, 3 bottom) ──────────────────────
    COLORS = {
        "boltz2_affinity":       "#2E86AB",
        "score_only_boltz2":     "#A23B72",
        "score_only_af3msa":     "#C45BAA",
        "score_only_af3colabfold": "#E8A0D5",
        "redock_boltz2":         "#F18F01",
        "redock_af3msa":         "#C73E1D",
        "redock_af3colabfold":   "#3B1F2B",
    }

    panels = [
        # (col, title, ylabel, color_key)
        ("boltz2_affinity",
         "Boltz-2 Predicted Affinity",
         "Predicted affinity (higher = tighter)",
         "boltz2_affinity"),
        ("score_only_boltz2",
         "Vina Score-Only — Boltz-2",
         "Vina score (kcal/mol)",
         "score_only_boltz2"),
        ("score_only_af3msa",
         "Vina Score-Only — AF3 (AF3-MSA)",
         "Vina score (kcal/mol)",
         "score_only_af3msa"),
        ("score_only_af3colabfold",
         "Vina Score-Only — AF3 (ColabFold-MSA)",
         "Vina score (kcal/mol)",
         "score_only_af3colabfold"),
        ("redock_boltz2",
         "Vina Redock — Boltz-2",
         "Vina redock score (kcal/mol)",
         "redock_boltz2"),
        ("redock_af3msa",
         "Vina Redock — AF3 (AF3-MSA)",
         "Vina redock score (kcal/mol)",
         "redock_af3msa"),
        ("redock_af3colabfold",
         "Vina Redock — AF3 (ColabFold-MSA)",
         "Vina redock score (kcal/mol)",
         "redock_af3colabfold"),
    ]

    fig, axes = plt.subplots(2, 4, figsize=(18, 9))
    axes = axes.flatten()

    x_vals  = merged["pKd"].values.astype(float)
    labels  = merged["ligand"].values

    for i, (col, title, ylabel, ckey) in enumerate(panels):
        ax = axes[i]
        if col not in merged.columns:
            ax.text(0.5, 0.5, "Data not yet\navailable",
                    ha="center", va="center", transform=ax.transAxes, fontsize=9, color="gray")
            ax.set_title(title, fontsize=9, fontweight="bold")
            ax.axis("off")
            continue
        y_vals = pd.to_numeric(merged[col], errors="coerce").values.astype(float)
        scatter_panel(ax, x_vals, y_vals, labels,
                      title=title,
                      xlabel="pKd  (6 − log₁₀[Kd/µM])  →  tighter binding",
                      ylabel=ylabel,
                      color=COLORS[ckey])

    # Hide the unused 8th panel
    axes[7].set_visible(False)

    fig.suptitle("Computational Scores vs Experimental Kd — Siglec-6 Ligand Library",
                 fontsize=12, fontweight="bold", y=1.01)
    plt.tight_layout()
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    print(f"\nFigure → {OUT_PNG}")


if __name__ == "__main__":
    main()
