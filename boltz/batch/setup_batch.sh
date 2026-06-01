#!/usr/bin/env bash
# One-time setup: ECR repo, S3 bucket, AWS Batch compute environment, job queue, job definition.
# Run once from the project root (WSL) before submitting jobs.
#
# Prerequisites:
#   - Logged in: /mnt/c/Program\ Files/Amazon/AWSCLIV2/aws.exe sso login --profile sugrani-scripps
#   - Docker Desktop running (needed to build and push the image)
set -euo pipefail

# WSL uses the Windows AWS CLI binary
AWS="/mnt/c/Program Files/Amazon/AWSCLIV2/aws.exe"
PROFILE="sugrani-scripps"
REGION="us-west-2"
ACCOUNT="127696279288"

ECR_REPO="boltz2-cofolding"
IMAGE_TAG="latest"
IMAGE_URI="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
S3_BUCKET="scripps-hackathon-boltz-${ACCOUNT}"

# Discovered from the hackathon AWS account
SUBNETS="subnet-0096ffc9c05bebab3,subnet-071d3dbca8e9b7209,subnet-0e8c4795d00d2f2c6"
SECURITY_GROUP="sg-09d5ef7889a26f56a"   # hackathon-eice-instance
INSTANCE_PROFILE="hackathon-ec2-profile"

AWS_CMD() { "$AWS" --profile "$PROFILE" --region "$REGION" "$@"; }

echo "=== 1. Create S3 bucket (if needed) ==="
AWS_CMD s3 mb "s3://${S3_BUCKET}" 2>/dev/null || echo "  bucket already exists"

echo "=== 2. Create ECR repository (if needed) ==="
AWS_CMD ecr describe-repositories --repository-names "${ECR_REPO}" 2>/dev/null \
    || AWS_CMD ecr create-repository --repository-name "${ECR_REPO}"

echo "=== 3. Build and push Docker image ==="
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}/.."  # boltz/ directory
AWS_CMD ecr get-login-password \
    | docker login --username AWS --password-stdin "${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
docker build -t "${ECR_REPO}:${IMAGE_TAG}" .
docker tag "${ECR_REPO}:${IMAGE_TAG}" "${IMAGE_URI}"
docker push "${IMAGE_URI}"
cd -

echo "=== 4. Create Batch compute environment ==="
AWS_CMD batch create-compute-environment \
    --compute-environment-name boltz2-gpu-spot \
    --type MANAGED \
    --state ENABLED \
    --compute-resources "{
        \"type\": \"SPOT\",
        \"allocationStrategy\": \"SPOT_CAPACITY_OPTIMIZED\",
        \"minvCpus\": 0,
        \"maxvCpus\": 56,
        \"instanceTypes\": [\"g5.xlarge\"],
        \"subnets\": [\"subnet-0096ffc9c05bebab3\", \"subnet-071d3dbca8e9b7209\", \"subnet-0e8c4795d00d2f2c6\"],
        \"securityGroupIds\": [\"${SECURITY_GROUP}\"],
        \"instanceRole\": \"arn:aws:iam::${ACCOUNT}:instance-profile/${INSTANCE_PROFILE}\",
        \"bidPercentage\": 60,
        \"tags\": {\"Project\": \"hackathon-boltz2\"}
    }"

echo "  Waiting for compute environment to become VALID..."
sleep 30  # give Batch a moment before polling
AWS_CMD batch describe-compute-environments \
    --compute-environments boltz2-gpu-spot \
    --query "computeEnvironments[0].status" --output text

echo "=== 5. Create job queue ==="
AWS_CMD batch create-job-queue \
    --job-queue-name boltz2-queue \
    --state ENABLED \
    --priority 100 \
    --compute-environment-order "[{\"order\": 1, \"computeEnvironment\": \"boltz2-gpu-spot\"}]"

echo "=== 6. Register job definition ==="
AWS_CMD batch register-job-definition \
    --job-definition-name boltz2-cofolding \
    --type container \
    --container-properties "{
        \"image\": \"${IMAGE_URI}\",
        \"vcpus\": 4,
        \"memory\": 16384,
        \"resourceRequirements\": [{\"type\": \"GPU\", \"value\": \"1\"}],
        \"environment\": [
            {\"name\": \"S3_BUCKET\", \"value\": \"${S3_BUCKET}\"},
            {\"name\": \"S3_PREFIX\", \"value\": \"boltz\"}
        ]
    }"

echo ""
echo "=== Setup complete ==="
echo "S3 bucket : s3://${S3_BUCKET}"
echo "Image URI : ${IMAGE_URI}"
echo ""
echo "Next: run  bash boltz/batch/submit_jobs.sh  (from project root)"
