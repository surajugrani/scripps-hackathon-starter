#!/usr/bin/env python3
"""
Generate 3-panel contact heatmap (one per cofolding method) + cross-method bullet points.

Run from project root:
  uv run --with pandas --with matplotlib --with numpy python3 ppt/contact_heatmap.py

Outputs:
  ppt/contact_heatmap.png   — 3-panel figure for PPT slide
  ppt/contact_bullets.txt   — auto-generated bullet points for the slide
"""
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap

ROOT = Path(".")
SOURCES = {
    "Boltz-2":          ROOT / "analysis/02_interactions/interactions.csv",
    "AF3  (AF3-MSA)":   ROOT / "analysis/af3/interactions_af3msa.csv",
    "AF3  (ColabFold-MSA)": ROOT / "analysis/af3/interactions_colabfoldmsa.csv",
}
OUT_PNG     = ROOT / "ppt/contact_heatmap.png"
OUT_BULLETS = ROOT / "ppt/contact_bullets.txt"
HOTSPOT_MIN = 3   # residue must be contacted by this many ligands in ≥1 method to appear

ITYPE_RANK = {"PolarContact": 2, "Hydrophobic": 1, "VdwContact": 0}
COLORS = {
    "PolarContact": "#4EA8DE",   # blue
    "Hydrophobic":  "#F4A261",   # orange
    "VdwContact":   "#8D99AE",   # gray
    "None":         "#1A1A2E",   # background (no contact)
}


# ── helpers ────────────────────────────────────────────────────────────────

def load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def dominant_itype(group: pd.DataFrame) -> str:
    """For a (ligand, residue) group, return the highest-priority interaction type."""
    if group.empty:
        return "None"
    return max(group["interaction"], key=lambda t: ITYPE_RANK.get(t, 0))


def build_matrix(df: pd.DataFrame, ligands: list, residues: list) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns:
      presence  — bool array (n_residues × n_ligands)
      itype_int — int array encoding interaction type (for coloring)
    """
    n_res, n_lig = len(residues), len(ligands)
    presence  = np.zeros((n_res, n_lig), dtype=bool)
    itype_int = np.zeros((n_res, n_lig), dtype=int)   # 0=none, 1=vdw, 2=hydro, 3=polar

    res_idx = {r: i for i, r in enumerate(residues)}
    lig_idx = {l: i for i, l in enumerate(ligands)}

    for (lig, res), grp in df.groupby(["ligand", "residue"]):
        if lig in lig_idx and res in res_idx:
            ri, li = res_idx[res], lig_idx[lig]
            presence[ri, li] = True
            dt = dominant_itype(grp)
            itype_int[ri, li] = {"None": 0, "VdwContact": 1, "Hydrophobic": 2, "PolarContact": 3}[dt]

    return presence, itype_int


def residue_sort_key(res: str) -> int:
    """Extract sequence number for sorting."""
    import re
    m = re.search(r"(\d+)", res)
    return int(m.group(1)) if m else 9999


# ── load data ──────────────────────────────────────────────────────────────

dfs = {}
for name, path in SOURCES.items():
    if path.exists():
        dfs[name] = load(path)
    else:
        print(f"WARNING: {path} not found — skipping")

if not dfs:
    raise SystemExit("No interaction files found. Run the contact analysis scripts first.")

# All ligands (sorted naturally)
all_ligands = sorted(
    set(lig for df in dfs.values() for lig in df["ligand"].unique()),
    key=lambda s: (int(s.split("_")[1]) if "_" in s and s.split("_")[1].isdigit() else 999, s)
)

# Hot-spot residues: contacted by HOTSPOT_MIN+ ligands in at least one method
residue_counts = defaultdict(lambda: defaultdict(int))
for name, df in dfs.items():
    for res, grp in df.groupby("residue"):
        residue_counts[res][name] = grp["ligand"].nunique()

hotspot_residues = sorted(
    [res for res, counts in residue_counts.items()
     if max(counts.values()) >= HOTSPOT_MIN],
    key=residue_sort_key
)

# sa-unique residues: contacted by sa but not hot-spots among analogs
sa_residues_per_method = {}
for name, df in dfs.items():
    sa_res = set(df[df["ligand"] == "sa"]["residue"].unique())
    sa_residues_per_method[name] = sa_res

all_sa_residues = sorted(
    set(r for rs in sa_residues_per_method.values() for r in rs)
    - set(hotspot_residues),
    key=residue_sort_key
)

# Full row list: hot-spots + divider (None) + sa-unique
DIVIDER = "── sialic acid ──"
all_rows = hotspot_residues + [DIVIDER] + all_sa_residues

print(f"Hot-spot residues: {len(hotspot_residues)}")
print(f"sa-unique residues: {len(all_sa_residues)}")
print(f"Ligands: {all_ligands}")


# ── cross-method analysis for bullet points ────────────────────────────────

source_names = list(dfs.keys())

# Residues that are hot-spots in ALL 3 methods
def is_hotspot(res, name):
    return residue_counts[res].get(name, 0) >= HOTSPOT_MIN

consistent_residues = [r for r in hotspot_residues
                       if all(is_hotspot(r, n) for n in source_names)]
method_only = {n: [r for r in hotspot_residues
                   if is_hotspot(r, n) and not all(is_hotspot(r, m) for m in source_names)]
               for n in source_names}

# Ligands: consistent binding mode = contacted same top-3 residues in ≥2 methods
def top_residues(name, ligand, n=5):
    if name not in dfs:
        return set()
    sub = dfs[name][dfs[name]["ligand"] == ligand]
    return set(sub.nsmallest(n, "min_dist")["residue"].tolist())

lig_consistency = {}
for lig in all_ligands:
    top_sets = [top_residues(n, lig) for n in source_names if n in dfs]
    if len(top_sets) >= 2:
        # Jaccard similarity between all pairs
        sims = []
        for i in range(len(top_sets)):
            for j in range(i+1, len(top_sets)):
                a, b = top_sets[i], top_sets[j]
                if a | b:
                    sims.append(len(a & b) / len(a | b))
        lig_consistency[lig] = np.mean(sims) if sims else 0.0

consistent_ligs = sorted([l for l, s in lig_consistency.items() if s >= 0.4],
                          key=lambda l: -lig_consistency[l])
divergent_ligs  = sorted([l for l, s in lig_consistency.items() if s < 0.2],
                          key=lambda l: lig_consistency[l])


# ── write bullet points ────────────────────────────────────────────────────

lines = []
lines.append("CONTACT ANALYSIS — SLIDE BULLET POINTS")
lines.append("=" * 55)
lines.append("")
lines.append("● Consistent hot-spot residues (all 3 methods agree):")
if consistent_residues:
    lines.append(f"  {', '.join(consistent_residues)}")
else:
    lines.append("  None — no residue reached hot-spot threshold in all 3 methods")

lines.append("")
lines.append("● Method-specific hot-spots:")
for name in source_names:
    uniq = method_only[name]
    short = name.replace("AF3  ", "AF3 ").replace("  (", " (")
    lines.append(f"  {short}: {', '.join(uniq) if uniq else 'none unique'}")

lines.append("")
lines.append("● Compounds with CONSISTENT binding mode across methods")
lines.append("  (Jaccard similarity of top-5 contacted residues ≥ 0.40):")
lines.append(f"  {', '.join(consistent_ligs) if consistent_ligs else 'none'}")
lines.append(f"  (avg similarity: { {l: f'{lig_consistency[l]:.2f}' for l in consistent_ligs} })")

lines.append("")
lines.append("● Compounds with DIVERGENT binding modes across methods")
lines.append("  (Jaccard similarity < 0.20 — pose varies by method):")
lines.append(f"  {', '.join(divergent_ligs) if divergent_ligs else 'none'}")

lines.append("")
lines.append("● Boltz-2 binding clusters identified:")
lines.append("  Cluster A (hydrophobic pocket): cpd_1, cpd_3, cpd_6, cpd_7, cpd_8, cpd_9")
lines.append("             Key residues: LEU48, CYS46, VAL47, VAL171")
lines.append("  Cluster B (charged/aromatic): cpd_2, cpd_4, cpd_5, cpd_11, cpd_13")
lines.append("             Key residues: ARG122, LYS129, TYR130, PHE68")
lines.append("")
lines.append("● AF3 (both conditions) consistently predicts TRP127, TYR61, TYR62,")
lines.append("  TYR130, MET128 as the primary binding face — aromatic/Trp-rich pocket")
lines.append("")
lines.append("● Sialic acid (natural ligand control) contacts a DISTINCT binding site")
lines.append("  in all 3 methods — no overlap with synthetic analog hot-spots:")
lines.append("  Boltz-2:  ARG147, GLU227, HIS146, THR225, MET226 (polar-rich, sequence ~144–229)")
lines.append("  AF3:      ARG113, ARG114, ASN116 (consistent between both AF3 conditions)")
lines.append("  → Synthetic analogs may be targeting a different sub-pocket than the")
lines.append("    natural carbohydrate ligand — or predictions for sa are uncertain")

bullet_text = "\n".join(lines)
OUT_BULLETS.write_text(bullet_text)
print("\n" + bullet_text)


# ── plot ───────────────────────────────────────────────────────────────────

itype_cmap = ListedColormap(["#1A1A2E", COLORS["VdwContact"],
                              COLORS["Hydrophobic"], COLORS["PolarContact"]])

n_methods = len(dfs)
n_rows = len(all_rows)
fig, axes = plt.subplots(1, n_methods,
                          figsize=(5.5 * n_methods, max(10, n_rows * 0.32 + 2)))
if n_methods == 1:
    axes = [axes]

fig.patch.set_facecolor("#1A1A2E")

for ax, (name, df) in zip(axes, dfs.items()):
    # Build full matrix including divider row and sa residues
    n_res, n_lig = len(all_rows), len(all_ligands)
    itype_mat = np.full((n_res, n_lig), -1, dtype=float)  # -1 = divider

    res_idx = {r: i for i, r in enumerate(all_rows)}
    lig_idx = {l: i for i, l in enumerate(all_ligands)}

    for (lig, res), grp in df.groupby(["ligand", "residue"]):
        if lig in lig_idx and res in res_idx:
            ri, li = res_idx[res], lig_idx[lig]
            dt = dominant_itype(grp)
            itype_mat[ri, li] = {"None": 0, "VdwContact": 1,
                                  "Hydrophobic": 2, "PolarContact": 3}[dt]

    # Divider row → special value -1 stays, show as mid-gray stripe
    div_idx = res_idx[DIVIDER]
    itype_mat[div_idx, :] = -1

    # Custom colormap: -1=divider(gold), 0=none, 1=vdw, 2=hydro, 3=polar
    from matplotlib.colors import BoundaryNorm
    cmap_ext = ListedColormap(["#3A3020",        # -1 divider (gold-tint dark)
                                "#1A1A2E",        #  0 no contact
                                COLORS["VdwContact"],
                                COLORS["Hydrophobic"],
                                COLORS["PolarContact"]])
    norm = BoundaryNorm([-1.5, -0.5, 0.5, 1.5, 2.5, 3.5], cmap_ext.N)

    ax.imshow(itype_mat, aspect="auto", cmap=cmap_ext, norm=norm, interpolation="nearest")

    # Gridlines (skip divider row)
    ax.set_xticks(np.arange(-0.5, n_lig, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which="minor", color="#2A2A4A", linewidth=0.7)
    ax.tick_params(which="minor", bottom=False, left=False)

    # X labels
    ax.set_xticks(range(n_lig))
    ax.set_xticklabels([l.replace("cpd_", "c") for l in all_ligands],
                        rotation=45, ha="right", fontsize=8, color="white")

    # Y labels — on EVERY panel
    ax.set_yticks(range(n_rows))
    ylabels = []
    for r in all_rows:
        if r == DIVIDER:
            ylabels.append("── sialic acid ──")
        else:
            ylabels.append(r)
    ax.set_yticklabels(ylabels, fontsize=7.5, color="white")

    # Make divider label gold and bold
    for tick, label in zip(ax.yaxis.get_major_ticks(), ylabels):
        if label == "── sialic acid ──":
            tick.label1.set_color("#FFD700")
            tick.label1.set_fontweight("bold")
            tick.label1.set_fontsize(7)

    ax.set_title(name, fontsize=11, fontweight="bold", color="white", pad=8)
    ax.set_facecolor("#1A1A2E")
    for spine in ax.spines.values():
        spine.set_edgecolor("#3A3A5A")

    # Highlight divider row with a gold line
    ax.axhline(div_idx - 0.5, color="#FFD700", linewidth=1.2, alpha=0.6)
    ax.axhline(div_idx + 0.5, color="#FFD700", linewidth=1.2, alpha=0.6)

    # Star markers for consistent hot-spots
    for i, res in enumerate(all_rows):
        if res in consistent_residues:
            ax.annotate("★", xy=(-0.8, i), xycoords=("data", "data"),
                         fontsize=8, color="#FFD700", ha="center", va="center",
                         annotation_clip=False)

# Legend
patches = [
    mpatches.Patch(color=COLORS["PolarContact"], label="Polar contact  (≤3.5 Å, N/O/S)"),
    mpatches.Patch(color=COLORS["Hydrophobic"],  label="Hydrophobic  (C–C, ≤4.5 Å)"),
    mpatches.Patch(color=COLORS["VdwContact"],   label="vdW contact  (≤5.0 Å)"),
    mpatches.Patch(color="#1A1A2E",              label="No contact", ec="#3A3A5A"),
]
fig.legend(handles=patches, loc="lower center", ncol=4,
           fontsize=9, facecolor="#1A1A2E", edgecolor="#3A3A5A",
           labelcolor="white", framealpha=0.9,
           bbox_to_anchor=(0.5, -0.02))

# Star note
if consistent_residues:
    fig.text(0.01, -0.04,
             f"★ = consistent hot-spot in all 3 methods: {', '.join(consistent_residues)}",
             fontsize=8.5, color="#FFD700", ha="left")

fig.suptitle("Protein–Ligand Contact Heatmap  (hot-spot residues, 3+ ligands)",
             fontsize=13, fontweight="bold", color="white", y=1.01)
plt.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(str(OUT_PNG), dpi=150, bbox_inches="tight", facecolor="#1A1A2E")
print(f"\nFigure → {OUT_PNG}")
