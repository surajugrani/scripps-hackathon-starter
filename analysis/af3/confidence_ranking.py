#!/usr/bin/env python3
"""
Parse AF3 confidence scores for both MSA conditions and compare with Boltz-2.

Run from project root:
  uv run --with pandas analysis/af3/confidence_ranking.py

Outputs (in analysis/af3/):
  confidence_af3msa.csv        — AF3 with AF3's own MSA search
  confidence_colabfoldmsa.csv  — AF3 with ColabFold MSA
  confidence_comparison.csv    — all three methods side by side, ranked by Boltz-2 iPTM
"""
import json
import csv
from pathlib import Path

import pandas as pd

AF3_DIR   = Path("AF3_outputs")
BOLTZ_CSV = Path("analysis/01_confidence/confidence_ranking.csv")
OUT_DIR   = Path("analysis/af3")

CONDITIONS = {
    "af3msa":        AF3_DIR / "w-MSA-search_outs",
    "colabfoldmsa":  AF3_DIR / "w-colabfold-MSA_outs",
}


def parse_af3_condition(cond_dir: Path) -> list[dict]:
    rows = []
    for summary_file in sorted(cond_dir.glob("*_summary_confidences.json")):
        ligand = summary_file.stem.replace("_summary_confidences", "")
        data   = json.loads(summary_file.read_text())

        # chain_pair_pae_min[0][1] = min PAE from protein (chain 0) to ligand (chain 1)
        pae_matrix = data.get("chain_pair_pae_min", [[None, None], [None, None]])
        prot_to_lig_pae = pae_matrix[0][1] if pae_matrix and len(pae_matrix[0]) > 1 else None

        rows.append({
            "ligand":           ligand,
            "iptm":             round(data.get("iptm", 0.0), 4),
            "ptm":              round(data.get("ptm",  0.0), 4),
            "ranking_score":    round(data.get("ranking_score", 0.0), 4),
            "prot_lig_pae_min": round(prot_to_lig_pae, 2) if prot_to_lig_pae is not None else None,
            "has_clash":        data.get("has_clash", 0.0),
        })
    rows.sort(key=lambda r: r["iptm"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def print_table(rows: list[dict], label: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"{'Rank':<5} {'Ligand':<10} {'iPTM':<8} {'PTM':<8} {'RankScore':<11} {'PAE(P→L)'}")
    print("-" * 55)
    for r in rows:
        pae = f"{r['prot_lig_pae_min']:.2f}" if r["prot_lig_pae_min"] is not None else "N/A"
        print(f"{r['rank']:<5} {r['ligand']:<10} {r['iptm']:<8} {r['ptm']:<8} {r['ranking_score']:<11} {pae}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_data = {}
    for cond_name, cond_dir in CONDITIONS.items():
        if not cond_dir.exists():
            print(f"WARNING: {cond_dir} not found, skipping.")
            continue
        rows = parse_af3_condition(cond_dir)
        all_data[cond_name] = rows
        out_csv = OUT_DIR / f"confidence_{cond_name}.csv"
        fields = ["rank", "ligand", "iptm", "ptm", "ranking_score", "prot_lig_pae_min", "has_clash"]
        with open(out_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print_table(rows, f"AF3 — {cond_name}")
        print(f"\n  → {out_csv}")

    # Cross-method comparison
    if not BOLTZ_CSV.exists():
        print(f"\nBoltz-2 CSV not found at {BOLTZ_CSV}, skipping comparison.")
        return

    boltz_df = pd.read_csv(BOLTZ_CSV).rename(columns={
        "iptm": "boltz2_iptm", "ptm": "boltz2_ptm",
        "confidence_score": "boltz2_conf", "rank": "boltz2_rank",
    })

    comp = boltz_df[["ligand", "boltz2_rank", "boltz2_iptm", "boltz2_conf"]].copy()

    for cond_name, rows in all_data.items():
        cond_df = pd.DataFrame(rows)[["ligand", "iptm", "ranking_score", "rank"]].rename(columns={
            "iptm":          f"af3_{cond_name}_iptm",
            "ranking_score": f"af3_{cond_name}_score",
            "rank":          f"af3_{cond_name}_rank",
        })
        comp = comp.merge(cond_df, on="ligand", how="left")

    comp = comp.sort_values("boltz2_rank")
    comp_csv = OUT_DIR / "confidence_comparison.csv"
    comp.to_csv(comp_csv, index=False)

    print(f"\n{'='*80}")
    print("  CROSS-METHOD COMPARISON (sorted by Boltz-2 rank)")
    print(f"{'='*80}")
    print(comp.to_string(index=False))
    print(f"\n  → {comp_csv}")


if __name__ == "__main__":
    main()
