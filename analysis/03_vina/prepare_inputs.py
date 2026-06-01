#!/usr/bin/env python3
"""
Prepare AutoDock Vina inputs from Boltz-2 results.

For each ligand:
  1. Extract the protein (chain A) from the Boltz-2 CIF → PDB
  2. Generate a 3D ligand conformation from SMILES → SDF
  3. Convert both to PDBQT using OpenBabel
  4. Compute the Vina search box from the predicted ligand center of mass

Dependencies:
  pip3 install rdkit biopython numpy
  sudo apt-get install -y openbabel

Run from project root:
  python3 analysis/03_vina/prepare_inputs.py
"""
import csv
import subprocess
import numpy as np
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import AllChem
from Bio import PDB

RESULTS_DIR  = Path("analysis/results")
LIGAND_CSV   = Path("raw/Hackathon Siglec-6 In Silico Library JLH.csv")
OUT_DIR      = Path("analysis/03_vina/inputs")
BOX_PADDING  = 10.0  # Å padding around ligand center for Vina search box
BOX_SIZE     = 22.0  # Å box side length


def find_structure(slug: str) -> Path | None:
    matches = list(RESULTS_DIR.rglob(f"{slug}*/model_0.cif"))
    return matches[0] if matches else None


def extract_protein_pdb(cif_path: Path, out_pdb: Path):
    parser = PDB.MMCIFParser(QUIET=True)
    structure = parser.get_structure("s", str(cif_path))
    io = PDB.PDBIO()
    io.set_structure(structure)

    class ChainASelect(PDB.Select):
        def accept_chain(self, chain):
            return chain.id == "A"

    io.save(str(out_pdb), ChainASelect())


def get_ligand_center(cif_path: Path) -> np.ndarray:
    parser = PDB.MMCIFParser(QUIET=True)
    structure = parser.get_structure("s", str(cif_path))
    coords = []
    for chain in structure.get_chains():
        if chain.id == "B":
            for atom in chain.get_atoms():
                coords.append(atom.coord)
    if not coords:
        raise ValueError(f"No chain B atoms found in {cif_path}")
    return np.mean(coords, axis=0)


def smiles_to_sdf(smiles: str, out_sdf: Path):
    mol = Chem.MolFromSmiles(smiles)
    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
    AllChem.MMFFOptimizeMolecule(mol)
    writer = Chem.SDWriter(str(out_sdf))
    writer.write(mol)
    writer.close()


def to_pdbqt(in_path: Path, out_path: Path, is_receptor: bool = False):
    flags = ["-xr"] if is_receptor else ["-xn", "--partialcharge", "gasteiger"]
    subprocess.run(
        ["obabel", str(in_path), "-O", str(out_path)] + flags,
        check=True, capture_output=True
    )


def write_box_config(center: np.ndarray, out_path: Path):
    out_path.write_text(
        f"center_x = {center[0]:.3f}\n"
        f"center_y = {center[1]:.3f}\n"
        f"center_z = {center[2]:.3f}\n"
        f"size_x = {BOX_SIZE}\n"
        f"size_y = {BOX_SIZE}\n"
        f"size_z = {BOX_SIZE}\n"
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(LIGAND_CSV) as f:
        ligands = list(csv.DictReader(f))

    for row in ligands:
        slug = row["structure"].replace(" ", "_")
        smiles = row["smiles"].strip()
        lig_dir = OUT_DIR / slug
        lig_dir.mkdir(exist_ok=True)

        cif = find_structure(slug)
        if cif is None:
            print(f"  SKIP {slug}: no Boltz-2 structure found")
            continue

        print(f"  {slug}...")

        # Protein
        pdb_path   = lig_dir / "receptor.pdb"
        pdbqt_rec  = lig_dir / "receptor.pdbqt"
        extract_protein_pdb(cif, pdb_path)
        to_pdbqt(pdb_path, pdbqt_rec, is_receptor=True)

        # Ligand
        sdf_path   = lig_dir / "ligand.sdf"
        pdbqt_lig  = lig_dir / "ligand.pdbqt"
        smiles_to_sdf(smiles, sdf_path)
        to_pdbqt(sdf_path, pdbqt_lig)

        # Box
        center = get_ligand_center(cif)
        write_box_config(center, lig_dir / "box.txt")

    print(f"\nInputs ready in {OUT_DIR}/")


if __name__ == "__main__":
    main()
