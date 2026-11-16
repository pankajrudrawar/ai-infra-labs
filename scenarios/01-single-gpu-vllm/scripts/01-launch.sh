#!/usr/bin/env bash
# Launches one g6.xlarge with the Deep Learning Base AMI. THIS COSTS MONEY (~$0.80/hour).
set -euo pipefail
source "$(dirname "$0")/config.sh"
# Verify this parameter name against the current DLAMI release notes.
AMI=$(aws ssm get-parameter --region "$AWS_REGION" \
  --name /aws/service/deeplearning/ami/x86_64/base-oss-nvidia-driver-gpu-ubuntu-22.04/latest/ami-id \
  --query Parameter.Value --output text)
read -rp "Launch $INSTANCE_TYPE in $AWS_REGION from $AMI? Billing starts now. [y/N] " ok
[[ "$ok" == "y" ]] || exit 1
aws ec2 run-instances --region "$AWS_REGION" --image-id "$AMI" --instance-type "$INSTANCE_TYPE" \
  --iam-instance-profile Name="$INSTANCE_PROFILE" \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
  --tag-specifications "$TAGS" \
  --query 'Instances[0].InstanceId' --output text
echo "Connect with: aws ssm start-session --region $AWS_REGION --target <instance-id>"
