#!/usr/bin/env python3
"""
Run AutoDock Vina in local_only mode on all predicted poses (all 3 sources × 14 ligands).

local_only performs energy minimization of the predicted pose within the binding box —
no global conformational search, unlike full redocking. Better than score_only because
the pose is allowed to relax before scoring.

Reads existing PDBQT inputs from analysis/03_vina/inputs/<source>/<slug>/ (already
prepared by run_vina.py or prepare_inputs.py — does NOT re-prepare anything).

Run from project root:
  python3 analysis/03_vina/local_only.py

Outputs in analysis/03_vina/results/:
  local_only_boltz2.csv
  local_only_af3msa.csv
  local_only_af3colabfold.csv

Also updates vina_comparison_all_sources.csv: replaces score_* columns with local_*
while keeping existing redock_* columns untouched.
"""
import csv
import re
import subprocess
from pathlib import Path

VINA_INPUTS  = Path("analysis/03_vina/inputs")
VINA_RESULTS = Path("analysis/03_vina/results")
DOCKED_DIR   = Path("analysis/03_vina/docked")

SOURCES = ["boltz2", "af3msa", "af3colabfold"]


def vina_local_only(receptor: Path, ligand: Path, box: Path, out_pdbqt: Path) -> float | None:
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
        "--out",       str(out_pdbqt),
        "--local_only",
    ], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        m = re.match(r"\s*1\s+([-\d.]+)", line)
        if m:
            return float(m.group(1))
    m = re.search(r"Estimated Free Energy of Binding\s*:\s*([-\d.]+)", r.stdout)
    if m:
        return float(m.group(1))
    return None


def run_source(source_name: str) -> list[dict]:
    src_dir = VINA_INPUTS / source_name
    if not src_dir.exists():
        print(f"  SKIP {source_name}: no inputs at {src_dir}")
        return []

    slugs = sorted(d.name for d in src_dir.iterdir() if d.is_dir())
    rows = []

    for slug in slugs:
        rec  = src_dir / slug / "receptor.pdbqt"
        lig  = src_dir / slug / "ligand_pose.pdbqt"
        box  = src_dir / slug / "box.txt"

        if not (rec.exists() and lig.exists() and box.exists()):
            print(f"    SKIP {slug}: missing receptor/ligand_pose/box in inputs")
            continue

        out_dir = DOCKED_DIR / source_name / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        out_pdbqt = out_dir / "local_only.pdbqt"

        score = vina_local_only(rec, lig, box, out_pdbqt)
        print(f"    {slug:15s}  {score} kcal/mol")
        rows.append({"ligand": slug, "vina_local_kcal_mol": score})

    return rows


def write_local_csv(source_name: str, rows: list[dict]):
    sorted_rows = sorted(rows, key=lambda r: r["vina_local_kcal_mol"] if r["vina_local_kcal_mol"] is not None else 0)
    out_csv = VINA_RESULTS / f"local_only_{source_name}.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rank", "ligand", "vina_local_kcal_mol"])
        w.writeheader()
        for i, row in enumerate(sorted_rows, 1):
            w.writerow({"rank": i, **row})
    print(f"  → {out_csv}")
    return sorted_rows


def update_comparison_csv(all_locals: dict[str, dict]):
    """Replace score_* columns with local_* in vina_comparison_all_sources.csv,
    keeping redock_* columns from the existing file unchanged."""
    comp_csv = VINA_RESULTS / "vina_comparison_all_sources.csv"

    # Load existing redock data (keep as-is)
    existing_redock: dict[str, dict] = {}
    if comp_csv.exists():
        with open(comp_csv) as f:
            for row in csv.DictReader(f):
                slug = row["ligand"]
                existing_redock[slug] = {
                    k: v for k, v in row.items()
                    if k.startswith("redock_")
                }

    # Collect all slugs
    slugs = sorted(set(
        s for src_map in all_locals.values() for s in src_map
    ) | set(existing_redock.keys()))

    fields = (
        ["ligand"]
        + [f"local_{src}" for src in SOURCES]
        + [f"redock_{src}" for src in SOURCES]
    )
    comp_rows = []
    for slug in slugs:
        row = {"ligand": slug}
        for src in SOURCES:
            row[f"local_{src}"] = all_locals.get(src, {}).get(slug)
        for src in SOURCES:
            row[f"redock_{src}"] = existing_redock.get(slug, {}).get(f"redock_{src}")
        comp_rows.append(row)

    with open(comp_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(comp_rows)
    print(f"\nUpdated comparison → {comp_csv}")


def main():
    VINA_RESULTS.mkdir(parents=True, exist_ok=True)
    all_locals: dict[str, dict] = {}

    for source_name in SOURCES:
        print(f"\n{'='*50}")
        print(f"  {source_name}")
        print(f"{'='*50}")
        rows = run_source(source_name)
        if not rows:
            continue
        write_local_csv(source_name, rows)
        all_locals[source_name] = {r["ligand"]: r["vina_local_kcal_mol"] for r in rows}

    if all_locals:
        update_comparison_csv(all_locals)
        print("\nDone. Run gen_figures.py + build_ppt.py to regenerate outputs.")
    else:
        print("\nNo results — check that PDBQT inputs exist in analysis/03_vina/inputs/")


if __name__ == "__main__":
    main()
