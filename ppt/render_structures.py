#!/usr/bin/env python3
"""
Render binding site overview: one aligned receptor + 14 ligand centroids per method.

All 3 methods are aligned to the SAME reference structure (Boltz-2 cpd_1) so the
protein is in an identical orientation across all 3 panels — enabling direct comparison
of where each method places the ligands.

Run from project root:
  uv run --with gemmi --with numpy --with matplotlib python3 ppt/render_structures.py

Output: ppt/fig_binding_overview.png
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import gemmi
import csv
from pathlib import Path

ROOT     = Path(".")
OUT      = Path("ppt/fig_binding_overview.png")
CONF_CSV = ROOT / "analysis/af3/confidence_comparison.csv"

DARK_BG = "#1A1A2E"
MID_BG  = "#16213E"

SOURCES = [
    ("Boltz-2",              "boltz2",       ROOT / "analysis/results"),
    ("AF3  ·  AF3-MSA",      "af3msa",       ROOT / "AF3_outputs/w-MSA-search_outs"),
    ("AF3  ·  ColabFold-MSA","af3colabfold", ROOT / "AF3_outputs/w-colabfold-MSA_outs"),
]

POCKET_CUTOFF = 20.0   # Å — show Cα within this distance of any ligand centroid
LABEL_TOP_N   = 3      # label only the top-N compounds by iPTM per panel
GLOBAL_REF_SLUG = "cpd_1"   # reference compound (Boltz-2) — all structures aligned to this


# ── structure helpers ───────────────────────────────────────────────────────

def find_cif(src_key: str, src_dir: Path, slug: str) -> Path | None:
    if src_key == "boltz2":
        matches = list(src_dir.rglob(f"{slug}_model_0.cif"))
    else:
        matches = list(src_dir.glob(f"{slug}_model.cif"))
    return matches[0] if matches else None


def ca_positions(model) -> np.ndarray:
    pts = []
    for ch in model:
        if ch.name == "A":
            for res in ch:
                if "CA" in res:
                    a = res["CA"][0]
                    pts.append([a.pos.x, a.pos.y, a.pos.z])
    return np.array(pts) if pts else np.empty((0, 3))


def ligand_centroid(model) -> np.ndarray | None:
    pts = []
    for ch in model:
        if ch.name == "B":
            for res in ch:
                for atom in res:
                    if atom.element.name not in ("H", "D"):
                        pts.append([atom.pos.x, atom.pos.y, atom.pos.z])
    return np.mean(pts, axis=0) if pts else None


def apply_transform(model, transform):
    for ch in model:
        for res in ch:
            for atom in res:
                atom.pos = gemmi.Position(transform.apply(atom.pos))


def pocket_ca(ca_all: np.ndarray, centroids: np.ndarray) -> np.ndarray:
    if len(ca_all) == 0 or centroids is None or len(centroids) == 0:
        return ca_all
    keep = np.zeros(len(ca_all), dtype=bool)
    for c in centroids:
        keep |= (np.linalg.norm(ca_all - c, axis=1) <= POCKET_CUTOFF)
    return ca_all[keep]


# ── alignment ───────────────────────────────────────────────────────────────

def load_global_reference() -> tuple:
    """Load Boltz-2 cpd_1 as the shared reference. Returns (polymer, ca_array)."""
    src_dir = ROOT / "analysis/results"
    cif = find_cif("boltz2", src_dir, GLOBAL_REF_SLUG)
    if cif is None:
        raise FileNotFoundError(f"Global reference CIF not found for {GLOBAL_REF_SLUG}")
    st    = gemmi.read_structure(str(cif))
    model = st[0]
    return model["A"].get_polymer(), ca_positions(model)


def process_source(src_key: str, src_dir: Path, slugs: list,
                   iptm_map: dict, ref_polymer, ca_ref: np.ndarray):
    """Align all structures to the global reference; return centroids in that frame."""
    ptype = gemmi.PolymerType.PeptideL
    centroids, iptm_vals, labels = [], [], []

    for slug in slugs:
        cif = find_cif(src_key, src_dir, slug)
        if cif is None:
            continue
        st    = gemmi.read_structure(str(cif))
        model = st[0]

        mob_polymer = model["A"].get_polymer()
        try:
            sup = gemmi.calculate_superposition(
                ref_polymer, mob_polymer, ptype, gemmi.SupSelect.CaP
            )
            apply_transform(model, sup.transform)
        except Exception as e:
            print(f"    superposition failed for {slug}/{src_key}: {e}")

        c = ligand_centroid(model)
        if c is not None:
            centroids.append(c)
            iptm_vals.append(iptm_map.get(slug, 0.5))
            labels.append(slug)

    return np.array(centroids) if centroids else None, iptm_vals, labels


# ── viewing angle ────────────────────────────────────────────────────────────

def shared_view_angle(all_centroids_list: list) -> tuple[float, float]:
    """Compute a single viewing angle that best shows spread across ALL methods."""
    combined = np.vstack([c for c in all_centroids_list if c is not None and len(c)])
    if len(combined) < 3:
        return 20, 45
    centered = combined - combined.mean(axis=0)
    _, _, vt = np.linalg.svd(centered)
    # vt[2] = least-variance axis → look along it so max spread is in-plane
    normal = vt[2]
    elev = float(np.degrees(np.arcsin(np.clip(normal[2], -1, 1))))
    azim = float(np.degrees(np.arctan2(normal[1], normal[0])))
    return elev, azim


# ── main ────────────────────────────────────────────────────────────────────

def main():
    # Load confidence scores
    boltz_iptm, af3msa_iptm, af3cf_iptm = {}, {}, {}
    with open(CONF_CSV) as f:
        for row in csv.DictReader(f):
            slug = row["ligand"]
            boltz_iptm[slug]  = float(row["boltz2_iptm"])
            af3msa_iptm[slug] = float(row["af3_af3msa_iptm"])
            af3cf_iptm[slug]  = float(row["af3_colabfoldmsa_iptm"])

    slugs     = sorted(boltz_iptm.keys())
    iptm_maps = {"boltz2": boltz_iptm, "af3msa": af3msa_iptm, "af3colabfold": af3cf_iptm}

    # Load single global reference
    print(f"Loading global reference: Boltz-2 {GLOBAL_REF_SLUG} ...")
    ref_polymer, ca_ref = load_global_reference()
    print(f"  Reference: {len(ca_ref)} Cα atoms")

    # Process all 3 sources (align to global reference)
    results = []
    for title, src_key, src_dir in SOURCES:
        print(f"\nProcessing {title} ...")
        centroids, iptm_vals, labels = process_source(
            src_key, src_dir, slugs, iptm_maps[src_key], ref_polymer, ca_ref
        )
        results.append((title, centroids, iptm_vals, labels))
        if centroids is not None:
            print(f"  {len(centroids)} ligand centroids collected")

    # Compute one shared viewing angle from all centroids combined
    elev, azim = shared_view_angle([r[1] for r in results])
    print(f"\nShared view angle: elev={elev:.1f}°  azim={azim:.1f}°")

    # Pocket Cα is the same for all panels (reference structure)
    all_centroids_combined = np.vstack(
        [r[1] for r in results if r[1] is not None and len(r[1])]
    )
    ca_pocket = pocket_ca(ca_ref, all_centroids_combined)
    print(f"Pocket residues within {POCKET_CUTOFF} Å: {len(ca_pocket)} Cα")

    # ── figure ───────────────────────────────────────────────────────────
    cmap = plt.cm.RdYlGn
    norm = mcolors.Normalize(vmin=0.55, vmax=0.95)

    fig = plt.figure(figsize=(18, 6.5))
    fig.patch.set_facecolor(DARK_BG)

    axes = []
    for col, (title, centroids, iptm_vals, labels) in enumerate(results):
        ax = fig.add_subplot(1, 3, col + 1, projection="3d")
        ax.set_facecolor(MID_BG)
        axes.append(ax)

        # Protein pocket trace — identical across all 3 panels
        if len(ca_pocket) > 1:
            ax.plot(ca_pocket[:, 0], ca_pocket[:, 1], ca_pocket[:, 2],
                    color="#AAAACC", lw=0.8, alpha=0.18, zorder=1)
            ax.scatter(ca_pocket[:, 0], ca_pocket[:, 1], ca_pocket[:, 2],
                       color="#AAAACC", s=3, alpha=0.12, zorder=1)

        # Ligand centroids
        if centroids is not None and len(centroids):
            ax.scatter(
                centroids[:, 0], centroids[:, 1], centroids[:, 2],
                c=iptm_vals, cmap=cmap, norm=norm,
                s=280, zorder=5, edgecolors="white", linewidths=0.6, alpha=0.95
            )

            # Label top N by iPTM; all others shown smaller/fainter
            ranked = sorted(zip(iptm_vals, labels, centroids),
                            key=lambda x: x[0], reverse=True)
            for rank, (iptm, lbl, pos) in enumerate(ranked):
                short  = lbl.replace("cpd_", "c")
                is_top = rank < LABEL_TOP_N
                ax.text(pos[0], pos[1], pos[2] + 1.8,
                        short,
                        fontsize=8.5 if is_top else 6.5,
                        fontweight="bold" if is_top else "normal",
                        color="white", alpha=1.0 if is_top else 0.6,
                        ha="center", va="bottom", zorder=6)

            # Spread annotation
            spread = np.std(np.linalg.norm(centroids - centroids.mean(axis=0), axis=1))
            ax.text2D(0.5, 0.02, f"spread σ = {spread:.1f} Å",
                      transform=ax.transAxes, fontsize=8, color="#AAAACC",
                      ha="center",
                      bbox=dict(facecolor=MID_BG, edgecolor="none", alpha=0.7))

        # Same angle for all 3 panels
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(title, color="white", fontsize=12, pad=10, fontweight="bold")
        ax.set_axis_off()

    # Shared colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, shrink=0.55, pad=0.02,
                        orientation="vertical", aspect=20)
    cbar.set_label("iPTM confidence\n(higher = better)", color="white",
                   fontsize=10, labelpad=8)
    cbar.ax.yaxis.set_tick_params(labelcolor="white", labelsize=9)
    cbar.outline.set_edgecolor("#444466")
    cbar.set_ticks([0.6, 0.7, 0.8, 0.9])

    fig.text(
        0.5, 0.96,
        "All 3 methods aligned to same reference  ·  Each sphere = ligand center of mass  ·  "
        "Faint trace = binding pocket (20 Å)  ·  Bold labels = top 3 by iPTM",
        ha="center", va="top", fontsize=9, color="#AAAACC"
    )
    fig.suptitle(
        "Binding Site Overview — All 14 Ligands, Same Reference Frame Across Methods",
        color="white", fontsize=14, y=1.04, fontweight="bold"
    )

    plt.tight_layout(rect=[0, 0, 0.93, 1.0])
    fig.savefig(str(OUT), dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close(fig)
    print(f"\nSaved: {OUT}")


if __name__ == "__main__":
    main()
