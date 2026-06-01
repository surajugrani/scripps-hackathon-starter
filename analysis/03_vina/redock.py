#!/usr/bin/env python3
"""
Redock ligands into the Boltz-2 predicted binding pocket using AutoDock Vina,
then compute RMSD between the Boltz-2 pose and the top Vina pose.

Run from project root after score_only.py:
  python3 analysis/03_vina/redock.py --top 5

The --top N flag selects the N best ligands from score_only_results.csv.
Outputs:
  analysis/03_vina/redock_results.csv   — Vina scores + RMSD vs Boltz-2 pose
  analysis/03_vina/docked/<slug>/       — Vina output poses (PDBQT)
"""
import argparse
import csv
import subprocess
import re
from pathlib import Path

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem

INPUTS_DIR     = Path("analysis/03_vina/inputs")
SCORE_CSV      = Path("analysis/03_vina/score_only_results.csv")
DOCKED_DIR     = Path("analysis/03_vina/docked")
OUT_CSV        = Path("analysis/03_vina/redock_results.csv")


def read_top_slugs(n: int) -> list[str]:
    with open(SCORE_CSV) as f:
        rows = list(csv.DictReader(f))
    # Already sorted by score (most negative = best)
    return [r["ligand"] for r in rows[:n]]


def run_vina(receptor: Path, ligand: Path, box_cfg: Path, out_dir: Path) -> tuple[float | None, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdbqt = out_dir / "docked.pdbqt"
    box = {}
    for line in box_cfg.read_text().splitlines():
        k, v = line.split("=")
        box[k.strip()] = v.strip()

    result = subprocess.run([
        "vina",
        "--receptor", str(receptor),
        "--ligand",   str(ligand),
        "--center_x", box["center_x"],
        "--center_y", box["center_y"],
        "--center_z", box["center_z"],
        "--size_x",   box["size_x"],
        "--size_y",   box["size_y"],
        "--size_z",   box["size_z"],
        "--out",      str(out_pdbqt),
        "--exhaustiveness", "16",
        "--num_modes", "5",
    ], capture_output=True, text=True)

    score = None
    for line in result.stdout.splitlines():
        m = re.match(r"\s*1\s+([-\d.]+)", line)
        if m:
            score = float(m.group(1))
            break

    return score, out_pdbqt


def rmsd_pdbqt_vs_sdf(boltz_sdf: Path, vina_pdbqt: Path) -> float | None:
    """RMSD between Boltz-2 ligand pose (SDF) and top Vina pose (PDBQT), heavy atoms only."""
    try:
        ref = Chem.SDMolSupplier(str(boltz_sdf), removeHs=True)[0]
        # Extract first model from PDBQT
        pdbqt_text = vina_pdbqt.read_text()
        first_model = pdbqt_text.split("MODEL")[1].split("ENDMDL")[0] if "MODEL" in pdbqt_text else pdbqt_text
        probe = Chem.MolFromPDBBlock(
            "\n".join(l for l in first_model.splitlines() if l.startswith(("ATOM", "HETATM"))),
            removeHs=True
        )
        if ref is None or probe is None:
            return None
        # Align by atom order (assumes same atom ordering)
        ref_conf  = ref.GetConformer().GetPositions()
        prob_conf = probe.GetConformer().GetPositions()
        n = min(len(ref_conf), len(prob_conf))
        diff = ref_conf[:n] - prob_conf[:n]
        return float(np.sqrt((diff ** 2).sum(axis=1).mean()))
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=5, help="Redock top N ligands from score_only results")
    args = parser.parse_args()

    slugs = read_top_slugs(args.top)
    print(f"Redocking top {len(slugs)} ligands: {slugs}\n")

    rows = []
    for slug in slugs:
        rec     = INPUTS_DIR / slug / "receptor.pdbqt"
        lig     = INPUTS_DIR / slug / "ligand.pdbqt"
        boltz_sdf = INPUTS_DIR / slug / "ligand.sdf"
        box_cfg = INPUTS_DIR / slug / "box.txt"
        out_dir = DOCKED_DIR / slug

        print(f"  {slug}...")
        score, out_pdbqt = run_vina(rec, lig, box_cfg, out_dir)
        rmsd = rmsd_pdbqt_vs_sdf(boltz_sdf, out_pdbqt) if out_pdbqt.exists() else None

        print(f"    Vina score: {score} kcal/mol   RMSD vs Boltz-2: {rmsd:.2f} Å" if rmsd else f"    Vina score: {score}")
        rows.append({"ligand": slug, "vina_redock_score": score, "rmsd_vs_boltz2_A": round(rmsd, 3) if rmsd else "N/A"})

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ligand", "vina_redock_score", "rmsd_vs_boltz2_A"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nRedock results → {OUT_CSV}")


if __name__ == "__main__":
    main()
