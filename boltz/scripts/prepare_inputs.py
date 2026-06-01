#!/usr/bin/env python3
"""
Generate one Boltz-2 YAML input file per ligand.

Reads:
  raw/Siglex_Vtyp_C2typ1_C2typ2.fasta  — protein sequence
  raw/Hackathon Siglec-6 In Silico Library JLH.csv  — ligand SMILES

Writes:
  boltz/inputs/<name>.yaml  — one file per ligand
  boltz/inputs/manifest.txt — ordered list of filenames (used by entrypoint to map array index → file)

Run from the project root:
  python boltz/scripts/prepare_inputs.py
"""
import csv
import re
from pathlib import Path

FASTA = Path("raw/Siglex_Vtyp_C2typ1_C2typ2.fasta")
CSV   = Path("raw/Hackathon Siglec-6 In Silico Library JLH.csv")
OUT   = Path("boltz/inputs")

# Path to the MSA *inside the container* (mounted/downloaded at runtime)
MSA_CONTAINER_PATH = "/data/msa.a3m"


def read_sequence(fasta_path: Path) -> str:
    lines = []
    for line in fasta_path.read_text().splitlines():
        if not line.startswith(">"):
            lines.append(line.strip())
    return "".join(lines)


def safe_name(raw: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", raw.strip())


def make_yaml(sequence: str, smiles: str) -> str:
    return f"""\
version: 1
sequences:
  - protein:
      id: A
      sequence: {sequence}
      msa: {MSA_CONTAINER_PATH}
  - ligand:
      id: B
      smiles: "{smiles}"
properties:
  - affinity:
      binder: B
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sequence = read_sequence(FASTA)

    names = []
    with open(CSV, newline="") as f:
        for row in csv.DictReader(f):
            name = safe_name(row["structure"])
            smiles = row["smiles"].strip()
            yaml_path = OUT / f"{name}.yaml"
            yaml_path.write_text(make_yaml(sequence, smiles))
            names.append(yaml_path.name)
            print(f"  wrote {yaml_path}")

    manifest = OUT / "manifest.txt"
    manifest.write_text("\n".join(names) + "\n")
    print(f"\nManifest ({len(names)} ligands) → {manifest}")


if __name__ == "__main__":
    main()
