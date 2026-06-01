# Hackathon Notes — Sugrani

Scripps Research 2026 CBB Hackathon · May 29 – June 1

---

## How to use this file

Add an entry under the current date. Capture what you did, why, any commands or code worth remembering, and what's next. Write enough that you (or a teammate) can pick up where you left off.

---

## 2026-05-29 — Day 0: Setup

### AWS
- Installed `uv`/`uvx` in WSL
- Added three awslabs MCP servers to Claude Code: `s3`, `aws-docs`, `aws-pricing`
- Confirmed AWS credentials work: profile `sugrani-scripps`, account `127696279288`
- Infrastructure already provisioned: VPC, private/public subnets, NAT gateway, EICE endpoint, IAM instance profile `hackathon-ec2-profile`
- AWS CLI is the Windows binary at `C:\Program Files\Amazon\AWSCLIV2\aws.exe` — use full path in WSL or run via `! aws ...`

### HPC (Garibaldi)
- Confirmed `garibaldi.scripps.edu` is reachable from WSL
- SSH host key accepted
- **To do:** generate an SSH key and copy it to Garibaldi for passwordless login:
  ```bash
  ssh-keygen -t ed25519 -f ~/.ssh/garibaldi -N ""
  ssh-copy-id -i ~/.ssh/garibaldi.pub sugrani@garibaldi.scripps.edu
  ```

---

## 2026-05-30 — Day 1

### Project goal
- **Target:** Siglec-6 protein (`raw/Siglex_Vtyp_C2typ1_C2typ2.fasta`)
- **Ligand library:** 14 compounds with SMILES in `raw/Hackathon Siglec-6 In Silico Library JLH.csv`
- **Task:** Protein–ligand cofolding — predict binding structures for all 14 ligands in parallel
- **Pre-computed MSA:** `raw/colabfold_msa.a3m` (can be fed directly to Boltz-2, saves compute time)

### Tool decision: Boltz-2 (not AlphaFold3)
- Chose **Boltz-2** over AF3 because it is fully open-source — no form/approval needed
- AF3 remains an option later but requires requesting model weights from DeepMind
- Boltz-2 supports protein–ligand cofolding with SMILES input natively

### Compute decision: Docker on AWS EC2
- Running all 14 ligands **in parallel on AWS EC2**
- Using **Docker container** so the full environment (Boltz-2 version, dependencies, run commands) is captured in a Dockerfile — easy to reproduce and audit later
- Will not use Garibaldi HPC for this run

### Compute: EC2 instance type
- Chose **`g5.xlarge`** — 1x A10G GPU, ~$1.01/hr, good balance of speed and cost for a one-shot 14-ligand run
- Will run 14 containers in parallel (one per ligand) via **AWS Batch**
- AWS Batch manages instance provisioning, spot interruption, and cleanup automatically
- Existing VPC/subnet infrastructure will be reused (`hackathon-ec2-profile` IAM profile)

### Pipeline files created
| File | Purpose |
|---|---|
| `boltz/Dockerfile` | Builds image: CUDA 12.8 + Boltz-2 + AWS CLI |
| `boltz/scripts/prepare_inputs.py` | Reads FASTA + CSV → 14 YAML files + `manifest.txt` |
| `boltz/scripts/entrypoint.sh` | Container entry: downloads inputs, runs boltz, uploads to S3 |
| `boltz/batch/setup_batch.sh` | One-time: creates ECR repo, S3 bucket, Batch env/queue/job-def |
| `boltz/batch/submit_jobs.sh` | Uploads inputs to S3, submits Batch array job (size=14) |

### Ligand library
- 13 analogs (cpd 1–13) + sialic acid (`sa`) as natural positive control
- All SMILES are in `raw/Hackathon Siglec-6 In Silico Library JLH.csv`

### Next steps
- [x] Pick EC2 instance type → `g5.xlarge`
- [x] Write Dockerfile
- [x] Write input prep script
- [x] Write container entrypoint
- [x] Write Batch setup + submit scripts
- [x] **AWS resource IDs looked up and hardcoded** into `boltz/batch/setup_batch.sh`
- [x] Docker Engine 29.5.2 installed in WSL2 (not Docker Desktop — free, no GUI)
- [x] Run `python3 boltz/scripts/prepare_inputs.py` → 14 YAML files in `boltz/inputs/` (cpd_1–13 + sa)
- [x] Run `bash boltz/batch/setup_batch.sh` — all succeeded:
  - Docker image pushed to ECR: `127696279288.dkr.ecr.us-west-2.amazonaws.com/boltz2-cofolding:latest`
  - Batch compute environment `boltz2-gpu-spot` → VALID
  - Job queue `boltz2-queue` created
  - Job definition `boltz2-cofolding:1` registered
  - S3 bucket: `s3://scripps-hackathon-boltz-127696279288`
- [x] Run `bash boltz/batch/submit_jobs.sh` — 14 jobs submitted
  - Job ID: `5956edff-6e71-406a-833c-b36c28222ba8`
  - Inputs + MSA uploaded to `s3://scripps-hackathon-boltz-127696279288/boltz/`
  - Results will land at `s3://scripps-hackathon-boltz-127696279288/boltz/results/`
### Batch issue — switched to direct EC2
- Batch jobs stuck in RUNNABLE: `AWSServiceRoleForBatch` service-linked role missing/broken in hackathon account (no permission to create Auto Scaling Groups)
- Cancelled Batch array job `5956edff-6e71-406a-833c-b36c28222ba8`
- **Fix:** bypass Batch, launch a single g5.xlarge directly (`boltz/ec2/launch_instance.sh`)
- Instance runs all 14 ligands sequentially, self-terminates, uploads results to S3
- Boltz-2 cache mounted at `/tmp/boltz_cache` so model weights are downloaded only once
- AMI: `ami-04f5eedff2f0772a5` (Deep Learning Base OSS Nvidia Driver GPU AMI, Ubuntu 22.04, 2026-05-29)

- [x] Launched g5.xlarge EC2 instance: `i-02f289d601cc31935` (us-west-2)
  - Runs all 14 ligands sequentially, self-terminates, results → S3
  - Expected runtime: ~2-3 hours

- [ ] Download results from S3 and analyze

### Analysis plan
Scripts in `analysis/` — run after downloading Boltz-2 results from S3.

**Step 1 — Confidence ranking** (`analysis/01_confidence/`)
- Parse `confidence_model_0.json` per ligand
- Key metric: `iptm` (interface confidence between protein and ligand) → rank all 14
- Also report mean `plddt` and `ptm`

**Step 2 — Residue interactions** (`analysis/02_interactions/`)
- ProLIF: compute interaction fingerprints (H-bonds, hydrophobic, pi-stacking, etc.)
- Identify which protein residues are contacted by multiple ligands (hot spots)

**Step 3 — AutoDock Vina** (`analysis/03_vina/`)
- a) Score-only: feed Boltz-2 poses to Vina as-is → kcal/mol ranking
- b) Redock top 5 ligands into Boltz-2 pocket → RMSD vs Boltz-2 pose
- Convergent ranking (Boltz-2 iptm + Vina score agree) = high confidence hits

**Suggested order:** rank by iptm → ProLIF hot-spot map → Vina score-only all 14 → Vina redock top 5

---

## 2026-05-31 — Day 2

<!-- Add notes here -->

---

## 2026-06-01 — Day 3 (final)

<!-- Add notes here -->

---

## Resources

- [AWS setup guide](AWS_SETUP.md)
- [HPC setup guide](HPC_SETUP.md)
- [Hackathon account](https://d-9267e96a16.awsapps.com/start) — profile: `sugrani-scripps`
- Garibaldi login: `ssh sugrani@garibaldi.scripps.edu`
- HPC help: `hpc@scripps.edu`
