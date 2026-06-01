#!/usr/bin/env python3
"""
Parse Boltz-2 confidence JSON files and rank ligands.

Run from project root:
  python3 analysis/01_confidence/parse_confidence.py

Expects results downloaded to analysis/results/ (run 00_download/download_results.sh first).
Outputs a ranked CSV: analysis/01_confidence/confidence_ranking.csv
"""
import json
import csv
from pathlib import Path

RESULTS_DIR = Path("analysis/results")
OUT_CSV = Path("analysis/01_confidence/confidence_ranking.csv")


def find_confidence_files(results_dir: Path):
    # Boltz-2 output: results/<ligand>/boltz_results_<ligand>/predictions/<ligand>/confidence_<ligand>_model_0.json
    return sorted(results_dir.rglob("confidence_*_model_0.json"))


def parse_one(conf_file: Path) -> dict:
    data = json.loads(conf_file.read_text())
    ligand_slug = conf_file.parts[2]  # analysis/results/<slug>/...
    return {
        "ligand":          ligand_slug,
        "confidence_score": round(data.get("confidence_score", 0.0), 4),
        "iptm":            round(data.get("iptm", 0.0), 4),
        "ligand_iptm":     round(data.get("ligand_iptm", data.get("iptm", 0.0)), 4),
        "ptm":             round(data.get("ptm", 0.0), 4),
        "complex_plddt":   round(data.get("complex_plddt", 0.0), 4),
        "complex_iplddt":  round(data.get("complex_iplddt", 0.0), 4),
    }


def main():
    conf_files = find_confidence_files(RESULTS_DIR)
    if not conf_files:
        print(f"No confidence files found under {RESULTS_DIR}/")
        print("Run analysis/00_download/download_results.sh first.")
        return

    rows = [parse_one(f) for f in conf_files]
    rows.sort(key=lambda r: r["iptm"], reverse=True)

    fields = ["rank", "ligand", "confidence_score", "iptm", "ligand_iptm", "ptm", "complex_plddt", "complex_iplddt"]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for i, row in enumerate(rows, 1):
            writer.writerow({"rank": i, **row})

    print(f"Ranked {len(rows)} ligands → {OUT_CSV}\n")
    print(f"{'Rank':<5} {'Ligand':<12} {'Conf':<8} {'iPTM':<8} {'lig_iPTM':<10} {'PTM':<8} {'pLDDT'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        print(f"{i:<5} {row['ligand']:<12} {row['confidence_score']:<8} {row['iptm']:<8} {row['ligand_iptm']:<10} {row['ptm']:<8} {row['complex_plddt']}")


if __name__ == "__main__":
    main()
