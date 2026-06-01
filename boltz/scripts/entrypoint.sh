#!/usr/bin/env bash
# Container entrypoint — runs Boltz-2 for one ligand and uploads results to S3.
# Called by AWS Batch; AWS_BATCH_JOB_ARRAY_INDEX selects the ligand (0-indexed).
set -euo pipefail

LIGAND_INDEX=${AWS_BATCH_JOB_ARRAY_INDEX:-0}
S3_BUCKET=${S3_BUCKET:?'S3_BUCKET env var required'}
S3_PREFIX=${S3_PREFIX:-boltz}

mkdir -p /data /workspace/input /workspace/output

# Resolve ligand filename from the manifest (1-indexed for sed)
aws s3 cp "s3://${S3_BUCKET}/${S3_PREFIX}/inputs/manifest.txt" /tmp/manifest.txt
YAML_FILE=$(sed -n "$((LIGAND_INDEX + 1))p" /tmp/manifest.txt)

if [[ -z "$YAML_FILE" ]]; then
    echo "ERROR: no entry at index ${LIGAND_INDEX} in manifest" >&2
    exit 1
fi

echo "=== Ligand index ${LIGAND_INDEX}: ${YAML_FILE} ==="

# Download inputs from S3
aws s3 cp "s3://${S3_BUCKET}/${S3_PREFIX}/inputs/${YAML_FILE}" /workspace/input/input.yaml
aws s3 cp "s3://${S3_BUCKET}/${S3_PREFIX}/msa.a3m"             /data/msa.a3m

# Run Boltz-2
boltz predict /workspace/input/input.yaml \
    --out_dir /workspace/output \
    --accelerator gpu \
    --devices 1

# Upload results
SLUG="${YAML_FILE%.yaml}"
aws s3 cp /workspace/output/ \
    "s3://${S3_BUCKET}/${S3_PREFIX}/results/${SLUG}/" \
    --recursive

echo "=== Done: ${SLUG} ==="
