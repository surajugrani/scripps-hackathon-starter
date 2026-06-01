#!/usr/bin/env python3
"""
AutoDock Vina pipeline for all 3 cofolding sources × all 14 ligands.

Steps per source:
  1. prepare  — extract protein/ligand from CIF → PDBQT, compute box
  2. score    — Vina score-only on the predicted pose (no search)
  3. redock   — Vina full search in predicted pocket, compute RMSD vs predicted pose

Sources:
  boltz2        analysis/results/<slug>/boltz_results_<slug>/predictions/<slug>/<slug>_model_0.cif
  af3msa        AF3_outputs/w-MSA-search_outs/<slug>_model.cif
  af3colabfold  AF3_outputs/w-colabfold-MSA_outs/<slug>_model.cif

Run from project root:
  uv run --with rdkit --with numpy python3 analysis/03_vina/run_vina.py

Requires: vina binary and obabel on PATH (sudo apt install autodock-vina openbabel)

Outputs in analysis/03_vina/results/:
  score_only_<source>.csv
  redock_<source>.csv
"""
import csv
import re
import subprocess
import tempfile
import numpy as np
from pathlib import Path

import gemmi
from rdkit import Chem
from rdkit.Chem import AllChem

# ── paths ──────────────────────────────────────────────────────────────────
ROOT         = Path(".")
LIGAND_CSV   = ROOT / "raw/Hackathon Siglec-6 In Silico Library JLH.csv"
VINA_INPUTS  = ROOT / "analysis/03_vina/inputs"
VINA_RESULTS = ROOT / "analysis/03_vina/results"
DOCKED_DIR   = ROOT / "analysis/03_vina/docked"
BOX_SIZE     = 30.0   # Å  (22 too small for score_only — ligand outside grid error)
NUM_MODES      = 5

SOURCES = {
    "boltz2":       ROOT / "analysis/results",
    "af3msa":       ROOT / "AF3_outputs/w-MSA-search_outs",
    "af3colabfold": ROOT / "AF3_outputs/w-colabfold-MSA_outs",
}


# ── helpers ────────────────────────────────────────────────────────────────

def find_cif(source_name: str, source_dir: Path, slug: str) -> Path | None:
    if source_name == "boltz2":
        matches = list(source_dir.rglob(f"{slug}_model_0.cif"))
    else:
        matches = list(source_dir.glob(f"{slug}_model.cif"))
    return matches[0] if matches else None


def load_smiles(csv_path: Path) -> dict[str, str]:
    smiles = {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            slug = row["structure"].strip().replace(" ", "_")
            smiles[slug] = row["smiles"].strip()
    return smiles


def extract_chain_pdb(cif_path: Path, chain_name: str, out_pdb: Path):
    """Write one chain from a CIF to PDB using gemmi."""
    st = gemmi.read_structure(str(cif_path))
    new_st = gemmi.Structure()
    new_st.name = st.name
    new_model = gemmi.Model("1")
    for ch in st[0]:
        if ch.name == chain_name:
            new_model.add_chain(ch.clone())
    new_st.add_model(new_model)
    new_st.cell = st.cell
    new_st.write_pdb(str(out_pdb))


def ligand_center(cif_path: Path) -> np.ndarray:
    st = gemmi.read_structure(str(cif_path))
    coords = []
    for ch in st[0]:
        if ch.name == "B":
            for res in ch:
                for atom in res:
                    coords.append([atom.pos.x, atom.pos.y, atom.pos.z])
    return np.mean(coords, axis=0)


def pdb_to_pdbqt_receptor(pdb: Path, pdbqt: Path):
    subprocess.run(
        ["obabel", str(pdb), "-O", str(pdbqt), "-xr"],
        check=True, capture_output=True
    )


def pdb_to_pdbqt_ligand(pdb: Path, pdbqt: Path):
    """Convert a ligand PDB (predicted pose, no Hs) to PDBQT via obabel."""
    subprocess.run(
        ["obabel", str(pdb), "-O", str(pdbqt), "-h", "--partialcharge", "gasteiger"],
        check=True, capture_output=True
    )


def smiles_to_pdbqt(smiles: str, pdbqt: Path) -> Path:
    """Generate 3D conformer from SMILES → SDF → PDBQT."""
    mol = Chem.MolFromSmiles(smiles)
    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
    AllChem.MMFFOptimizeMolecule(mol)
    with tempfile.NamedTemporaryFile(suffix=".sdf", delete=False) as f:
        tmp_sdf = Path(f.name)
    writer = Chem.SDWriter(str(tmp_sdf))
    writer.write(mol)
    writer.close()
    subprocess.run(
        ["obabel", str(tmp_sdf), "-O", str(pdbqt), "--partialcharge", "gasteiger"],
        check=True, capture_output=True
    )
    tmp_sdf.unlink(missing_ok=True)
    return pdbqt


def write_box(center: np.ndarray, path: Path):
    path.write_text(
        f"center_x = {center[0]:.3f}\n"
        f"center_y = {center[1]:.3f}\n"
        f"center_z = {center[2]:.3f}\n"
        f"size_x = {BOX_SIZE}\n"
        f"size_y = {BOX_SIZE}\n"
        f"size_z = {BOX_SIZE}\n"
    )


def vina_score_only(receptor: Path, ligand: Path, box: Path) -> float | None:
    cfg = {}
    for line in box.read_text().splitlines():
        k, v = line.split("=")
        cfg[k.strip()] = v.strip()
    r = subprocess.run([
        "vina",
        "--receptor",  str(receptor),
        "--ligand",    str(ligand),
        "--center_x",  cfg["center_x"],
        "--center_y",  cfg["center_y"],
        "--center_z",  cfg["center_z"],
        "--size_x",    cfg["size_x"],
        "--size_y",    cfg["size_y"],
        "--size_z",    cfg["size_z"],
        "--score_only",
    ], capture_output=True, text=True)
    # score_only output: "Estimated Free Energy of Binding   : -3.126 (kcal/mol)"
    m = re.search(r"Estimated Free Energy of Binding\s*:\s*([-\d.]+)", r.stdout)
    if m:
        return float(m.group(1))
    # redock output: table row "  1     -7.3  ..."
    for line in r.stdout.splitlines():
        if re.match(r"\s*1\s+([-\d.]+)", line):
            return float(line.split()[1])
    return None


def vina_redock(receptor: Path, ligand: Path, box: Path, out_pdbqt: Path) -> float | None:
    cfg = {}
    for line in box.read_text().splitlines():
        k, v = line.split("=")
        cfg[k.strip()] = v.strip()
    r = subprocess.run([
        "vina",
        "--receptor",       str(receptor),
        "--ligand",         str(ligand),
        "--center_x",       cfg["center_x"],
        "--center_y",       cfg["center_y"],
        "--center_z",       cfg["center_z"],
        "--size_x",         cfg["size_x"],
        "--size_y",         cfg["size_y"],
        "--size_z",         cfg["size_z"],
        "--out",            str(out_pdbqt),
        "--num_modes",      str(NUM_MODES),
    ], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        m = re.match(r"\s*1\s+([-\d.]+)", line)
        if m:
            return float(m.group(1))
    return None


def rmsd_pdbqt_vs_pose(pose_pdb: Path, docked_pdbqt: Path) -> float | None:
    """RMSD between the predicted ligand pose (PDB) and top Vina pose (PDBQT), heavy atoms."""
    try:
        ref_st = gemmi.read_structure(str(pose_pdb))
        ref_coords = np.array([[a.pos.x, a.pos.y, a.pos.z]
                                for ch in ref_st[0] for res in ch for a in res
                                if a.element.name not in ("H", "D")])

        pdbqt_text = docked_pdbqt.read_text()
        if "MODEL" in pdbqt_text:
            first_model = pdbqt_text.split("MODEL")[1].split("ENDMDL")[0]
        else:
            first_model = pdbqt_text
        probe_coords = []
        for line in first_model.splitlines():
            if line.startswith(("ATOM", "HETATM")):
                atom_name = line[12:16].strip()
                if not atom_name.startswith("H"):
                    try:
                        x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
                        probe_coords.append([x, y, z])
                    except ValueError:
                        pass
        probe_coords = np.array(probe_coords)

        n = min(len(ref_coords), len(probe_coords))
        if n == 0:
            return None
        diff = ref_coords[:n] - probe_coords[:n]
        return float(np.sqrt((diff ** 2).sum(axis=1).mean()))
    except Exception:
        return None


# ── main pipeline ──────────────────────────────────────────────────────────

def prepare(source_name: str, source_dir: Path, slug: str, smiles: str) -> dict | None:
    """Prepare all PDBQT inputs for one ligand/source. Returns paths dict or None on failure."""
    cif = find_cif(source_name, source_dir, slug)
    if cif is None:
        print(f"    SKIP: no CIF found for {slug} in {source_dir}")
        return None

    out_dir = VINA_INPUTS / source_name / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    receptor_pdb   = out_dir / "receptor.pdb"
    receptor_pdbqt = out_dir / "receptor.pdbqt"
    lig_pose_pdb   = out_dir / "ligand_pose.pdb"    # predicted coords → score-only
    lig_pose_pdbqt = out_dir / "ligand_pose.pdbqt"
    lig_fresh_pdbqt= out_dir / "ligand_fresh.pdbqt" # from SMILES → redocking
    box_txt        = out_dir / "box.txt"

    try:
        extract_chain_pdb(cif, "A", receptor_pdb)
        pdb_to_pdbqt_receptor(receptor_pdb, receptor_pdbqt)

        extract_chain_pdb(cif, "B", lig_pose_pdb)
        pdb_to_pdbqt_ligand(lig_pose_pdb, lig_pose_pdbqt)

        smiles_to_pdbqt(smiles, lig_fresh_pdbqt)

        center = ligand_center(cif)
        write_box(center, box_txt)
    except Exception as e:
        print(f"    ERROR preparing {slug}/{source_name}: {e}")
        return None

    return {
        "receptor": receptor_pdbqt,
        "lig_pose": lig_pose_pdbqt,
        "lig_fresh": lig_fresh_pdbqt,
        "box": box_txt,
    }


def run_source(source_name: str, source_dir: Path, smiles_map: dict[str, str]):
    print(f"\n{'='*60}")
    print(f"  Source: {source_name}")
    print(f"{'='*60}")

    score_rows  = []
    redock_rows = []

    slugs = sorted(smiles_map.keys())
    for slug in slugs:
        smiles = smiles_map[slug]
        print(f"\n  [{slug}]")

        paths = prepare(source_name, source_dir, slug, smiles)
        if paths is None:
            continue

        # Score-only (predicted pose)
        score = vina_score_only(paths["receptor"], paths["lig_pose"], paths["box"])
        print(f"    score-only: {score} kcal/mol")
        score_rows.append({"ligand": slug, "vina_score_kcal_mol": score})

        # Redock (fresh conformer)
        docked_dir  = DOCKED_DIR / source_name / slug
        docked_dir.mkdir(parents=True, exist_ok=True)
        out_pdbqt   = docked_dir / "docked.pdbqt"
        redock_score = vina_redock(paths["receptor"], paths["lig_fresh"], paths["box"], out_pdbqt)
        rmsd = rmsd_pdbqt_vs_pose(paths["lig_pose"].parent / "ligand_pose.pdb", out_pdbqt) if out_pdbqt.exists() else None
        rmsd_str = f"{rmsd:.2f}" if rmsd else "N/A"
        print(f"    redock:     {redock_score} kcal/mol   RMSD vs predicted: {rmsd_str} Å")
        redock_rows.append({"ligand": slug, "vina_redock_kcal_mol": redock_score, "rmsd_vs_pose_A": rmsd_str})

    VINA_RESULTS.mkdir(parents=True, exist_ok=True)

    # Score-only CSV
    score_rows.sort(key=lambda r: r["vina_score_kcal_mol"] if r["vina_score_kcal_mol"] is not None else 0)
    score_csv = VINA_RESULTS / f"score_only_{source_name}.csv"
    with open(score_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rank", "ligand", "vina_score_kcal_mol"])
        w.writeheader()
        for i, row in enumerate(score_rows, 1):
            w.writerow({"rank": i, **row})
    print(f"\n  Score-only → {score_csv}")

    # Print score-only table
    print(f"\n  {'Rank':<5} {'Ligand':<10} {'Vina Score (kcal/mol)'}")
    print("  " + "-"*35)
    for i, row in enumerate(score_rows, 1):
        print(f"  {i:<5} {row['ligand']:<10} {row['vina_score_kcal_mol']}")

    # Redock CSV
    redock_csv = VINA_RESULTS / f"redock_{source_name}.csv"
    with open(redock_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ligand", "vina_redock_kcal_mol", "rmsd_vs_pose_A"])
        w.writeheader()
        w.writerows(redock_rows)
    print(f"\n  Redock → {redock_csv}")

    return score_rows, redock_rows


def main():
    smiles_map = load_smiles(LIGAND_CSV)
    print(f"Loaded {len(smiles_map)} ligands: {sorted(smiles_map.keys())}")

    all_scores  = {}
    all_redocks = {}
    for source_name, source_dir in SOURCES.items():
        if not source_dir.exists():
            print(f"\nSkipping {source_name}: {source_dir} not found")
            continue
        scores, redocks = run_source(source_name, source_dir, smiles_map)
        all_scores[source_name]  = {r["ligand"]: r["vina_score_kcal_mol"] for r in scores}
        all_redocks[source_name] = {r["ligand"]: r["vina_redock_kcal_mol"] for r in redocks}

    # Combined comparison CSV
    slugs = sorted(smiles_map.keys())
    comp_rows = []
    for slug in slugs:
        row = {"ligand": slug}
        for src in SOURCES:
            row[f"score_{src}"]  = all_scores.get(src, {}).get(slug)
            row[f"redock_{src}"] = all_redocks.get(src, {}).get(slug)
        comp_rows.append(row)

    comp_csv = VINA_RESULTS / "vina_comparison_all_sources.csv"
    fields = ["ligand"] + [f"{t}_{s}" for t in ("score", "redock") for s in SOURCES]
    with open(comp_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(comp_rows)
    print(f"\nCombined comparison → {comp_csv}")


if __name__ == "__main__":
    main()
