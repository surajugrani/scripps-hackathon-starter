#!/bin/bash
# Runs directly on the EC2 instance (no Docker).
# Downloads inputs from S3, runs Boltz-2 via pip install, uploads results, self-terminates.
exec >> /var/log/boltz-run.log 2>&1

S3_BUCKET="scripps-hackathon-boltz-127696279288"
S3_PREFIX="boltz"
REGION="us-west-2"

echo "=== Boltz-2 direct run started at $(date) ==="

# Install Boltz-2
echo "--- Installing Boltz-2 ---"
pip install -q 'boltz[cuda]'

# Download inputs
echo "--- Downloading inputs from S3 ---"
aws s3 sync "s3://${S3_BUCKET}/${S3_PREFIX}/inputs/" /tmp/boltz_inputs/
mkdir -p /data
aws s3 cp "s3://${S3_BUCKET}/${S3_PREFIX}/msa.a3m" /data/msa.a3m

echo "--- Starting predictions ---"
while IFS= read -r yaml_file; do
    slug="${yaml_file%.yaml}"
    echo "=== ${slug} started at $(date) ==="
    boltz predict "/tmp/boltz_inputs/${yaml_file}" \
        --out_dir "/tmp/boltz_results/${slug}" \
        --accelerator gpu \
        --devices 1
    aws s3 cp "/tmp/boltz_results/${slug}/" \
        "s3://${S3_BUCKET}/${S3_PREFIX}/results/${slug}/" \
        --recursive
    echo "=== ${slug} done at $(date) ==="
done < /tmp/boltz_inputs/manifest.txt

echo "=== All predictions complete at $(date) ==="

# Self-terminate
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
aws ec2 terminate-instances --region "${REGION}" --instance-ids "${INSTANCE_ID}"
