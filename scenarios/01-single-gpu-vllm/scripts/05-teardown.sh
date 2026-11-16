#!/usr/bin/env bash
# Terminates every instance tagged for this series and checks nothing is left billing.
set -euo pipefail
AWS_REGION="${AWS_REGION:-us-east-1}"
IDS=$(aws ec2 describe-instances --region "$AWS_REGION" \
  --filters Name=tag:project,Values=ai-infra-series Name=instance-state-name,Values=pending,running,stopped \
  --query 'Reservations[].Instances[].InstanceId' --output text)
if [[ -n "$IDS" ]]; then
  aws ec2 terminate-instances --region "$AWS_REGION" --instance-ids $IDS
  aws ec2 wait instance-terminated --region "$AWS_REGION" --instance-ids $IDS
fi
echo "Unattached volumes (should be empty):"
aws ec2 describe-volumes --region "$AWS_REGION" --filters Name=status,Values=available \
  --query 'Volumes[].[VolumeId,Size]' --output table
