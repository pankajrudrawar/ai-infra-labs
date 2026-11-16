#!/usr/bin/env bash
# Asks AWS to raise "Running On-Demand G and VT instances" to 8 vCPUs. Free, but can take a day.
set -euo pipefail
AWS_REGION="${AWS_REGION:-us-east-1}"
aws service-quotas get-service-quota --service-code ec2 --quota-code L-DB2E81BA \
  --region "$AWS_REGION" --query 'Quota.Value'
aws service-quotas request-service-quota-increase --service-code ec2 --quota-code L-DB2E81BA \
  --desired-value 8 --region "$AWS_REGION"
