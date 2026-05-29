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

<!-- Add notes here -->

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
