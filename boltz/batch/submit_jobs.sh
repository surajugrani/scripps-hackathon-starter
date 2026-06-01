#!/usr/bin/env bash
# Upload inputs to S3 and submit a Batch array job (one job per ligand).
# Run from the project root after:
#   1. python boltz/scripts/prepare_inputs.py
#   2. bash boltz/batch/setup_batch.sh
set -euo pipefail

AWS="/mnt/c/Program Files/Amazon/AWSCLIV2/aws.exe"
PROFILE="sugrani-scripps"
REGION="us-west-2"
ACCOUNT="127696279288"
S3_BUCKET="scripps-hackathon-boltz-${ACCOUNT}"
S3_PREFIX="boltz"

AWS_CMD() { "$AWS" --profile "$PROFILE" --region "$REGION" "$@"; }

INPUTS_DIR="boltz/inputs"
MANIFEST="${INPUTS_DIR}/manifest.txt"

if [[ ! -f "$MANIFEST" ]]; then
    echo "ERROR: manifest not found — run 'python boltz/scripts/prepare_inputs.py' first" >&2
    exit 1
fi

NUM_LIGANDS=$(grep -c . "$MANIFEST")
echo "=== Uploading ${NUM_LIGANDS} input YAMLs + MSA to S3 ==="
AWS_CMD s3 sync "${INPUTS_DIR}/" "s3://${S3_BUCKET}/${S3_PREFIX}/inputs/"
AWS_CMD s3 cp raw/colabfold_msa.a3m "s3://${S3_BUCKET}/${S3_PREFIX}/msa.a3m"

echo "=== Submitting Batch array job (${NUM_LIGANDS} tasks) ==="
JOB_ID=$(AWS_CMD batch submit-job \
    --job-name "boltz2-cofolding-$(date +%Y%m%d-%H%M%S)" \
    --job-queue boltz2-queue \
    --job-definition boltz2-cofolding \
    --array-properties "size=${NUM_LIGANDS}" \
    --query jobId --output text)

echo ""
echo "=== Submitted! ==="
echo "Job ID  : ${JOB_ID}"
echo "Monitor : https://us-west-2.console.aws.amazon.com/batch/home?region=us-west-2#jobs"
echo "Results : s3://${S3_BUCKET}/${S3_PREFIX}/results/"
echo ""
echo "Watch status:"
echo "  \"$AWS\" --profile $PROFILE --region $REGION batch describe-jobs --jobs ${JOB_ID} --query 'jobs[0].{status:status,array:arrayProperties}'"
