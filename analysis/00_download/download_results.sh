#!/usr/bin/env bash
# Download Boltz-2 results from S3 to analysis/results/ locally.
# Run from the project root.
set -euo pipefail

AWS="/mnt/c/Program Files/Amazon/AWSCLIV2/aws.exe"
PROFILE="sugrani-scripps"
REGION="us-west-2"
ACCOUNT="127696279288"
S3_BUCKET="scripps-hackathon-boltz-${ACCOUNT}"
S3_PREFIX="boltz"
LOCAL_DIR="analysis/results"

mkdir -p "$LOCAL_DIR"

echo "=== Downloading Boltz-2 results from S3 ==="
"$AWS" --profile "$PROFILE" --region "$REGION" \
    s3 sync "s3://${S3_BUCKET}/${S3_PREFIX}/results/" "${LOCAL_DIR}/"

echo "Done. Results in: ${LOCAL_DIR}/"
echo ""
echo "Structure:  ${LOCAL_DIR}/<ligand>/predictions/<ligand>/model_0.cif"
echo "Confidence: ${LOCAL_DIR}/<ligand>/confidence/<ligand>/confidence_model_0.json"
