#!/usr/bin/env python3
"""
Compute protein-ligand interactions for all Boltz-2 predictions.

Uses gemmi distance-based contact search directly on mmCIF files
(avoids ProLIF/MDAnalysis hydrogen requirement).

Contact thresholds:
  polar_cutoff    3.5 Å  — proxy for H-bond / polar contact (N or O on either side)
  hydrophobic_cutoff 4.5 Å — C–C hydrophobic contact
  generic_cutoff  5.0 Å  — catch-all within 5 Å

Run from project root:
  uv run --with gemmi --with pandas analysis/02_interactions/prolif_analysis.py

Outputs:
  analysis/02_interactions/interactions.csv   — per-ligand interaction table
  analysis/02_interactions/hotspot_residues.csv — residues contacted by N+ ligands
"""
from pathlib import Path
from collections import defaultdict

import gemmi
import pandas as pd

RESULTS_DIR  = Path("analysis/results")
OUT_DIR      = Path("analysis/02_interactions")
INTERACTIONS_CSV = OUT_DIR / "interactions.csv"
HOTSPOT_CSV      = OUT_DIR / "hotspot_residues.csv"

HOTSPOT_MIN_LIGANDS = 3
GENERIC_CUTOFF      = 5.0   # Å — all contacts within this distance
POLAR_CUTOFF        = 3.5   # Å — N/O on either side → polar contact
HYDROPHOBIC_CUTOFF  = 4.5   # Å — C–C contacts → hydrophobic


def find_cif_files(results_dir: Path):
    return sorted(results_dir.rglob("*_model_0.cif"))


def ligand_slug(cif_path: Path) -> str:
    return cif_path.parts[2]  # analysis/results/<slug>/...


def classify_contact(lig_atom_el: str, prot_atom_el: str, dist: float) -> str:
    polar_elements = {"N", "O", "S"}
    if (lig_atom_el in polar_elements or prot_atom_el in polar_elements) and dist <= POLAR_CUTOFF:
        return "PolarContact"
    if lig_atom_el == "C" and prot_atom_el == "C" and dist <= HYDROPHOBIC_CUTOFF:
        return "Hydrophobic"
    return "VdwContact"


def get_contacts(cif_path: Path) -> list[dict]:
    st = gemmi.read_structure(str(cif_path))
    model = st[0]

    # Collect ligand atoms (chain B)
    lig_atoms = []
    for chain in model:
        if chain.name == "B":
            for res in chain:
                for atom in res:
                    lig_atoms.append((atom.pos, atom.element.name))

    if not lig_atoms:
        return []

    ns = gemmi.NeighborSearch(model, st.cell, GENERIC_CUTOFF)
    ns.populate(include_h=False)

    best: dict[tuple, dict] = {}
    for lig_pos, lig_el in lig_atoms:
        for mark in ns.find_atoms(lig_pos, "\0", radius=GENERIC_CUTOFF):
            cra = mark.to_cra(model)
            if cra.chain.name == "B":
                continue
            if cra.residue.entity_type != gemmi.EntityType.Polymer:
                continue
            prot_el = cra.atom.element.name
            dist = lig_pos.dist(cra.atom.pos)
            itype = classify_contact(lig_el, prot_el, dist)
            resid = f"{cra.residue.name}{cra.residue.seqid}"
            key = (resid, itype)
            if key not in best or dist < best[key]["min_dist"]:
                best[key] = {"residue": resid, "interaction": itype, "min_dist": round(dist, 2)}

    return list(best.values())


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cif_files = find_cif_files(RESULTS_DIR)
    if not cif_files:
        print(f"No structure files found under {RESULTS_DIR}/")
        print("Run analysis/00_download/download_results.sh first.")
        return

    all_rows = []
    residue_contacts: dict[str, set] = defaultdict(set)

    for cif in cif_files:
        slug = ligand_slug(cif)
        print(f"Processing {slug}...", end=" ", flush=True)
        contacts = get_contacts(cif)
        print(f"{len(contacts)} contacts")
        for c in contacts:
            all_rows.append({"ligand": slug, **c})
            residue_contacts[c["residue"]].add(slug)

    if not all_rows:
        print("No contacts found — check structure file format.")
        return

    interactions_df = pd.DataFrame(all_rows)
    interactions_df.to_csv(INTERACTIONS_CSV, index=False)
    print(f"\nInteraction table ({len(all_rows)} rows) → {INTERACTIONS_CSV}")

    # Hot-spot residues
    hotspots = [
        {"residue": res, "n_ligands": len(ligs), "ligands": ", ".join(sorted(ligs))}
        for res, ligs in residue_contacts.items()
        if len(ligs) >= HOTSPOT_MIN_LIGANDS
    ]
    hotspots.sort(key=lambda r: r["n_ligands"], reverse=True)
    pd.DataFrame(hotspots).to_csv(HOTSPOT_CSV, index=False)

    print(f"\nHot-spot residues (contacted by {HOTSPOT_MIN_LIGANDS}+ ligands) → {HOTSPOT_CSV}")
    print(f"\n{'Residue':<20} {'N ligands':<12} Ligands")
    print("-" * 70)
    for h in hotspots[:20]:
        print(f"  {h['residue']:<18} {h['n_ligands']:<12} {h['ligands']}")


if __name__ == "__main__":
    main()
