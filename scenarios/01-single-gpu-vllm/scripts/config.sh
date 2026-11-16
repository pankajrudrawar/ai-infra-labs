# Shared settings for Scenario 1. Edit before running.
export AWS_REGION="${AWS_REGION:-us-east-1}"
export INSTANCE_TYPE="${INSTANCE_TYPE:-g6.xlarge}"
export INSTANCE_PROFILE="${INSTANCE_PROFILE:?Set INSTANCE_PROFILE to an IAM instance profile with AmazonSSMManagedInstanceCore}"
export TAGS="ResourceType=instance,Tags=[{Key=project,Value=ai-infra-series},{Key=scenario,Value=1}]"
