#!/usr/bin/env bash
# Launch a g5.xlarge EC2 instance that runs all 14 Boltz-2 jobs sequentially,
# uploads results to S3, and self-terminates.
# Run from the project root.
set -euo pipefail

AWS="/mnt/c/Program Files/Amazon/AWSCLIV2/aws.exe"
PROFILE="sugrani-scripps"
REGION="us-west-2"
ACCOUNT="127696279288"

AMI_ID="ami-04f5eedff2f0772a5"       # Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04) 20260529
INSTANCE_TYPE="g5.xlarge"
SUBNET_ID="subnet-0096ffc9c05bebab3"  # aws-controltower-PrivateSubnet1A
SECURITY_GROUP="sg-09d5ef7889a26f56a" # hackathon-eice-instance
IAM_PROFILE="hackathon-ec2-profile"
USERDATA_FILE="boltz/ec2/userdata.sh"

echo "=== Launching ${INSTANCE_TYPE} for Boltz-2 run ==="

INSTANCE_ID=$("$AWS" --profile "$PROFILE" --region "$REGION" \
    ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --subnet-id "$SUBNET_ID" \
    --security-group-ids "$SECURITY_GROUP" \
    --iam-instance-profile Name="$IAM_PROFILE" \
    --user-data "file://${USERDATA_FILE}" \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":200,"VolumeType":"gp3"}}]' \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=boltz2-run},{Key=Project,Value=hackathon-boltz2}]' \
    --no-associate-public-ip-address \
    --query 'Instances[0].InstanceId' \
    --output text)

echo ""
echo "=== Instance launched ==="
echo "Instance ID : ${INSTANCE_ID}"
echo "Region      : ${REGION}"
echo ""
echo "The instance will run all 14 ligands, upload results to S3, then self-terminate."
echo "You do NOT need to keep your laptop on."
echo ""
echo "Check instance state:"
echo "  \"$AWS\" --profile $PROFILE --region $REGION ec2 describe-instances --instance-ids ${INSTANCE_ID} --query 'Reservations[0].Instances[0].{state:State.Name}'"
echo ""
echo "View logs (via EICE — no SSH key needed):"
echo "  \"$AWS\" --profile $PROFILE --region $REGION ec2-instance-connect open-tunnel --instance-id ${INSTANCE_ID}"
echo "  Then: sudo tail -f /var/log/boltz-run.log"
echo ""
echo "Results will appear at:"
echo "  s3://scripps-hackathon-boltz-${ACCOUNT}/boltz/results/"
