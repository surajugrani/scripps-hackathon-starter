#!/bin/bash
# Runs automatically on the EC2 instance at boot.
# Installs Boltz-2 via pip (no Docker/ECR needed), downloads inputs from S3,
# runs all 14 ligands sequentially, uploads results to S3, self-terminates.
# Logs: /var/log/boltz-run.log

exec > /var/log/boltz-run.log 2>&1

REGION="us-west-2"
S3_BUCKET="scripps-hackathon-boltz-127696279288"
S3_PREFIX="boltz"

echo "=== Boltz-2 run started at $(date) ==="
echo "Running as: $(aws sts get-caller-identity --region ${REGION} 2>&1)"

# Install Boltz-2 via pip (downloads from PyPI — no ECR needed)
echo "=== Installing Boltz-2 ==="
pip install -q 'boltz[cuda]'

# Download inputs from S3
echo "=== Downloading inputs from S3 ==="
aws s3 sync "s3://${S3_BUCKET}/${S3_PREFIX}/inputs/" /tmp/boltz_inputs/ --region "${REGION}"
mkdir -p /data
aws s3 cp "s3://${S3_BUCKET}/${S3_PREFIX}/msa.a3m" /data/msa.a3m --region "${REGION}"

echo "=== Starting predictions ==="
while IFS= read -r yaml_file; do
    slug="${yaml_file%.yaml}"
    echo "--- ${slug} started at $(date) ---"
    boltz predict "/tmp/boltz_inputs/${yaml_file}" \
        --out_dir "/tmp/boltz_results/${slug}" \
        --accelerator gpu \
        --devices 1
    aws s3 cp "/tmp/boltz_results/${slug}/" \
        "s3://${S3_BUCKET}/${S3_PREFIX}/results/${slug}/" \
        --recursive --region "${REGION}"
    echo "--- ${slug} done at $(date) ---"
done < /tmp/boltz_inputs/manifest.txt

echo "=== All predictions complete at $(date) ==="

# Self-terminate
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
aws ec2 terminate-instances --region "${REGION}" --instance-ids "${INSTANCE_ID}"
