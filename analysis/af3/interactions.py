#!/usr/bin/env python3
"""
Distance-based protein-ligand contact analysis for AF3 structures (both MSA conditions).

Run from project root:
  uv run --with gemmi --with pandas analysis/af3/interactions.py

Outputs (in analysis/af3/):
  interactions_af3msa.csv          hotspot_residues_af3msa.csv
  interactions_colabfoldmsa.csv    hotspot_residues_colabfoldmsa.csv
  hotspot_comparison.csv           — residues shared across methods
"""
from pathlib import Path
from collections import defaultdict

import gemmi
import pandas as pd

AF3_DIR = Path("AF3_outputs")
OUT_DIR = Path("analysis/af3")
BOLTZ_HOTSPOT_CSV = Path("analysis/02_interactions/hotspot_residues.csv")

CONDITIONS = {
    "af3msa":       AF3_DIR / "w-MSA-search_outs",
    "colabfoldmsa": AF3_DIR / "w-colabfold-MSA_outs",
}

HOTSPOT_MIN_LIGANDS = 3
GENERIC_CUTOFF      = 5.0
POLAR_CUTOFF        = 3.5
HYDROPHOBIC_CUTOFF  = 4.5


def classify_contact(lig_el: str, prot_el: str, dist: float) -> str:
    polar = {"N", "O", "S"}
    if (lig_el in polar or prot_el in polar) and dist <= POLAR_CUTOFF:
        return "PolarContact"
    if lig_el == "C" and prot_el == "C" and dist <= HYDROPHOBIC_CUTOFF:
        return "Hydrophobic"
    return "VdwContact"


def get_contacts(cif_path: Path) -> list[dict]:
    st = gemmi.read_structure(str(cif_path))
    model = st[0]

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


def run_condition(cond_name: str, cond_dir: Path):
    cif_files = sorted(cond_dir.glob("*_model.cif"))
    if not cif_files:
        print(f"  No CIF files in {cond_dir}")
        return None, None

    all_rows = []
    residue_contacts: dict[str, set] = defaultdict(set)

    for cif in cif_files:
        ligand = cif.stem.replace("_model", "")
        print(f"  {ligand}...", end=" ", flush=True)
        contacts = get_contacts(cif)
        print(f"{len(contacts)} contacts")
        for c in contacts:
            all_rows.append({"ligand": ligand, **c})
            residue_contacts[c["residue"]].add(ligand)

    interactions_csv = OUT_DIR / f"interactions_{cond_name}.csv"
    pd.DataFrame(all_rows).to_csv(interactions_csv, index=False)

    hotspots = [
        {"residue": res, "n_ligands": len(ligs), "ligands": ", ".join(sorted(ligs))}
        for res, ligs in residue_contacts.items()
        if len(ligs) >= HOTSPOT_MIN_LIGANDS
    ]
    hotspots.sort(key=lambda r: r["n_ligands"], reverse=True)
    hotspot_df = pd.DataFrame(hotspots)
    hotspot_csv = OUT_DIR / f"hotspot_residues_{cond_name}.csv"
    hotspot_df.to_csv(hotspot_csv, index=False)

    print(f"\n  Hot-spots (contacted by {HOTSPOT_MIN_LIGANDS}+ ligands):")
    print(f"  {'Residue':<20} N ligands")
    print("  " + "-" * 35)
    for h in hotspots[:15]:
        print(f"  {h['residue']:<20} {h['n_ligands']}")

    return hotspot_df, residue_contacts


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_hotspot_residues: dict[str, pd.DataFrame] = {}

    for cond_name, cond_dir in CONDITIONS.items():
        print(f"\n{'='*55}")
        print(f"  AF3 — {cond_name}")
        print(f"{'='*55}")
        if not cond_dir.exists():
            print(f"  WARNING: {cond_dir} not found, skipping.")
            continue
        hotspot_df, _ = run_condition(cond_name, cond_dir)
        if hotspot_df is not None and not hotspot_df.empty:
            all_hotspot_residues[cond_name] = hotspot_df

    # Cross-method hotspot comparison
    if BOLTZ_HOTSPOT_CSV.exists() and all_hotspot_residues:
        boltz_df = pd.read_csv(BOLTZ_HOTSPOT_CSV)[["residue", "n_ligands"]].rename(
            columns={"n_ligands": "boltz2_n"}
        )
        comp = boltz_df.copy()
        for cond_name, hdf in all_hotspot_residues.items():
            cond_col = hdf[["residue", "n_ligands"]].rename(columns={"n_ligands": f"af3_{cond_name}_n"})
            comp = comp.merge(cond_col, on="residue", how="outer")

        comp = comp.fillna(0).sort_values("boltz2_n", ascending=False)
        comp_csv = OUT_DIR / "hotspot_comparison.csv"
        comp.to_csv(comp_csv, index=False)

        print(f"\n{'='*65}")
        print("  HOTSPOT COMPARISON — Boltz-2 vs AF3 conditions")
        print(f"{'='*65}")
        print(comp.to_string(index=False))
        print(f"\n  → {comp_csv}")


if __name__ == "__main__":
    main()
