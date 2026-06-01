# scripps-hackathon-siglec6-cofold

**Scripps Research CBB Hackathon 2026 · May 29 – June 1 · La Jolla**

Predicting where a library of 14 Siglec-6 ligands bind using multi-method protein–ligand cofolding, interaction analysis, and docking. The full pipeline — from structure prediction to experimental Kd correlation — was built and run over 4 days.

> *This README was generated entirely by [Claude](https://claude.ai/claude-code) (Anthropic).*

---

## Project overview

**Target:** Siglec-6 (Vtype + C2type1 + C2type2 domains, 333 residues)  
**Ligand library:** 14 compounds — 13 synthetic analogs (cpd\_1–13) + sialic acid as a natural positive control  
**Goal:** Rank compounds by predicted binding confidence and docking score; cross-validate against experimental Kd values (SPR, n = 13)

---

## Pipeline

### 1. Input preparation

- Protein sequence: `raw/Siglex_Vtyp_C2typ1_C2typ2.fasta`
- Ligand SMILES: `raw/Hackathon Siglec-6 In Silico Library JLH.csv`
- Pre-computed MSA: `raw/colabfold_msa.a3m` (ColabFold mmseqs2, shared across methods)

### 2. Protein–ligand cofolding (3 methods × 14 ligands = 42 structures)

| Method | Compute | MSA |
|--------|---------|-----|
| **Boltz-2** | AWS EC2 g5.xlarge (NVIDIA A10G GPU) · Docker container | ColabFold pre-computed `.a3m` |
| **AlphaFold3 — AF3-MSA** | Garibaldi HPC (Scripps Research) | AF3 built-in MSA pipeline |
| **AlphaFold3 — ColabFold-MSA** | Garibaldi HPC (Scripps Research) | Same ColabFold `.a3m` as Boltz-2 |

Boltz-2 was run as a Docker container on an AWS EC2 spot instance (`g5.xlarge`), processing all 14 ligands sequentially (~8 min/ligand). Results were uploaded to S3 and downloaded for analysis. AF3 jobs were submitted to Garibaldi HPC under two MSA conditions to assess sensitivity to MSA source.

### 3. Confidence scoring

- **Boltz-2:** iPTM, pTM, mean pLDDT, and predicted affinity value (from `affinity_*.json`)
- **AF3:** iPTM and ranking score (from `*_confidences.json`)
- All 14 ligands ranked per method; results in `analysis/01_confidence/` and `analysis/af3/`

Key finding: Boltz-2 top hits (cpd\_4, cpd\_1, cpd\_9 by iPTM) differ substantially from AF3 top hits (cpd\_10, sialic acid). AF3 also showed structural divergence of up to 77.9 Å Cα RMSD between the two MSA conditions despite near-identical confidence scores.

### 4. Residue interaction analysis

- Tool: **ProLIF** (distance-based fingerprints: H-bonds, hydrophobic, π-stacking)
- Contacts extracted from all 42 cofolded CIF structures
- Hotspot residues contacted across multiple ligands and multiple methods identified
- Consistent residues across all 3 methods: **TYR130, TYR132, GLY131, LYS124**
- Results: `analysis/af3/interactions_*.csv`, `analysis/af3/hotspot_comparison.csv`

### 5. AutoDock Vina docking

Two independent Vina modes run on all 14 ligands × 3 cofolding sources:

- **Local-only:** predicted cofolded pose locally minimized by Vina (energy relaxation within the binding box, no global search). Uses the ligand position from cofolding as starting point.
- **Redocking:** fresh 3D conformer generated from SMILES (RDKit ETKDGv3 + MMFF) docked into the predicted pocket (global search, 5 modes, 30 × 30 × 30 Å box). RMSD vs. predicted pose computed for Boltz-2.

Results: `analysis/03_vina/results/`

### 6. Correlation with experimental Kd

- Experimental Kd values from SPR binding assay (n = 13 compounds, no Kd for sialic acid)
- Pearson r and Spearman ρ computed for each computational score vs. pKd
- Best correlations: Boltz-2 redock and Boltz-2 predicted affinity
- Scatter plots in `analysis/scatter_vs_kd.png`; data in `analysis/scatter_vs_kd.csv`

---

## Repository structure

```
.
├── raw/                          # Input files (FASTA, SMILES library, MSA)
├── analysis/
│   ├── results/                  # Boltz-2 output CIFs and JSON files (per ligand)
│   ├── 01_confidence/            # Confidence ranking scripts and CSV
│   ├── 02_interactions/          # ProLIF interaction scripts
│   ├── 03_vina/                  # Vina inputs, scripts, and results
│   └── af3/                      # AF3 confidence + interaction analysis
├── AF3_outputs/
│   ├── w-MSA-search_outs/        # AF3 structures (AF3 built-in MSA)
│   └── w-colabfold-MSA_outs/     # AF3 structures (ColabFold MSA)
├── boltz/
│   ├── Dockerfile                # Boltz-2 container definition
│   ├── scripts/                  # Input prep and container entrypoint
│   ├── ec2/                      # EC2 launch script
│   └── batch/                    # AWS Batch setup (not used — switched to direct EC2)
└── ppt/
    ├── Siglec6_Hackathon.pptx    # Final 9-slide presentation
    ├── build_ppt.py              # Programmatic slide builder (python-pptx)
    ├── gen_figures.py            # Matplotlib figure generator
    └── render_structures.py      # 3D binding site overview figure (gemmi + matplotlib)
```

---

## Key results

| Compound | Kd (µM) | Boltz-2 iPTM rank | Redock best (kcal/mol) |
|----------|---------|-------------------|------------------------|
| cpd\_12  | 4.7     | 11                | −7.7 (AF3-ColabFold)   |
| cpd\_10  | 5.1     | 8                 | −6.5 (AF3-MSA)         |
| cpd\_13  | 5.7     | 7                 | −8.1 (AF3-MSA)         |
| cpd\_9   | 6.5     | 3                 | −7.6 (AF3-MSA)         |
| cpd\_5   | 8.0     | 12                | −7.1 (Boltz-2)         |
| cpd\_4   | 49.9    | 1 (Boltz-2 top)   | −6.9 (AF3-ColabFold)   |

Compounds recommended for follow-up: **cpd\_9, cpd\_12, cpd\_13** — tight experimental Kd (4.7–6.5 µM) with reasonable computational scores across methods.

---

## Compute

| Resource | Usage |
|----------|-------|
| AWS EC2 g5.xlarge (NVIDIA A10G, 24 GB VRAM) | Boltz-2 cofolding (14 ligands, ~2 h total) |
| Garibaldi HPC — Scripps Research | AF3 cofolding (28 jobs across 2 MSA conditions) |
| Local (WSL2) | All analysis, docking, and figure generation |

---

## Authors

**Suraj Ugrani** and **Julien Heberling** — Scripps Research CBB Hackathon 2026
