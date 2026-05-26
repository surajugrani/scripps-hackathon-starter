---
name: scripps-garibaldi-hpc
description: Use when working with the Scripps Garibaldi HPC cluster, especially for Slurm job submission, interactive sessions, GPU jobs, array jobs, parallel jobs, job dependencies, account/login guidance, and module-based software usage.
---

# Scripps Garibaldi HPC

Use this skill when the user needs help working on the Scripps Garibaldi cluster. Focus on cluster-specific facts, local policies, local Slurm conventions, and examples that are already adapted to this environment. Do not spend much context re-explaining generic Slurm unless the user explicitly needs a tutorial.

## Cluster basics

- Scheduler: Garibaldi uses Slurm.
- Accounts: Users need a pre-existing TSRI email account and Unix credentials in AD. New HPC accounts are requested by emailing `hpc@scripps.edu`.
- Login hosts: `garibaldi.scripps.edu` and `login02.scripps.edu`.
- Rule: do not run large, long, multi-threaded, parallel, or CPU-intensive jobs on the front-end login hosts.
- Software: scientific software is typically exposed through environment modules.

## What to keep in scope

- Valid login hosts and the warning not to run heavy jobs there
- The account-request path and contact email
- Local module workflow
- Local partition and GPU examples already seen on Garibaldi
- Script templates that are already adapted to this cluster
- Practical defaults and cautions for this environment

## What to avoid by default

- Long explanations of basic Slurm commands
- Generic Slurm tutorials not tied to Garibaldi
- Large catalogs of flags or dependency types
- Stock examples that could apply to any cluster

## Default workflow

1. Confirm whether the user needs an interactive session, a CPU batch script, a GPU batch script, or a parallel run.
2. Collect only the resource choices that matter for the immediate task:
   - partition
   - wall time
   - nodes and tasks
   - CPUs per task
   - memory
   - GPU count and type if relevant
3. Put the workload on compute nodes with `srun` or `sbatch`, never on login hosts.
4. Start from `cd $SLURM_SUBMIT_DIR`.
5. Use modules when software setup matters:
   - `module purge`
   - `module load <package>`
6. Give the user the exact submit and monitoring commands they need.

## Ready-to-use patterns

### Interactive sessions

Basic shell on a compute node:

```bash
srun --pty bash
```

With X11 forwarding:

```bash
srun --x11 --pty bash
```

Heavier interactive request:

```bash
srun --nodes=1 --ntasks-per-node=16 --time=72:00:00 --mem=64000 --pty bash
```

GPU interactive session with GUI support:

```bash
srun --x11 --partition=gpu --nodes=1 --ntasks=20 --mem=500gb --gpus=1 --pty csh
```

Adjust resources to the actual workload instead of copying large requests by default.

### Basic shared-queue batch job

Template:

```bash
#!/bin/sh
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=7000
#SBATCH --time=240:00:00

cd $SLURM_SUBMIT_DIR
module load your_program
your_command_here
```

### Single-process multithreaded CPU job

Use this pattern for OpenMP, BLAS-threaded, or other shared-memory programs that run as one task with multiple CPU cores.

```bash
#!/bin/bash
#SBATCH --job-name=threads
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=24:00:00
#SBATCH --output=threads_%j.out

cd $SLURM_SUBMIT_DIR

module purge
module load your_program

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

your_threaded_program input.dat
```

### GPU batch job

Use the `gpu` partition and request the needed GPU resources explicitly.

```bash
#!/bin/bash
#SBATCH --job-name=xxx
#SBATCH --time=400:00:00
#SBATCH --mem=11gb
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:gtx1080ti:2
#SBATCH --cpus-per-task=20
#SBATCH --output=stdouterr.log
#SBATCH --partition=gpu

cd $SLURM_SUBMIT_DIR

module purge
module load namd/2.13-cuda

for i in {1..6}
do
  namd2 +p20 +idlepoll +setcpuaffinity step${i}_equilibration.inp > step${i}_equilibration.out
done
```

### Parallel job

```bash
#!/bin/bash
#SBATCH --job-name=test
#SBATCH --time=400:00:00
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=4
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=4
#SBATCH --partition=shared
#SBATCH --output=test_%j.log

cd $SLURM_SUBMIT_DIR

module purge
module load namd/2.13

mpirun `which namd2` test.inp > test.out
```

### Batch job with separate output and error logs

Use explicit log filenames when the user needs easier debugging or wants to preserve stderr separately from stdout.

```bash
#!/bin/bash
#SBATCH --job-name=logging
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

cd $SLURM_SUBMIT_DIR
mkdir -p logs

module purge
module load your_program

your_command_here
```

## Minimal local command set

Use these commands when the user needs concrete cluster operations, but do not expand them into a generic Slurm lesson unless asked.

```bash
sbatch job.slurm
srun --pty bash
squeue -u $USER
sinfo
scancel 123456
scontrol show job 123456
```

## Guidance for Codex

- Prefer cluster-specific guidance over generic scheduler theory.
- Prefer giving users a complete, runnable script instead of only explaining flags.
- Keep examples faithful to the Garibaldi environment and reuse the hostnames, partition names, and module workflow above.
- If the user mentions PBS syntax, translate only the parts needed for the Garibaldi job they are trying to run.
- If resource details are missing, make a conservative first-pass script and clearly mark the values the user may want to tune.
- When troubleshooting, usually suggest these checks first:
  - `squeue -u $USER`
  - `sinfo`
  - inspect the job's output or error log
  - verify the loaded modules
  - confirm the requested partition and resources are valid on this cluster
- Remind users that GUI and visualization workflows may need X11 forwarding.

## Output style

When helping with Garibaldi:

- state whether the solution is interactive or batch
- include the exact submit command
- include the full script when a script is involved
- call out any partition, GPU, memory, or time assumptions
- warn against running heavy work directly on login nodes
- keep generic Slurm explanation brief unless the user explicitly asks for it
