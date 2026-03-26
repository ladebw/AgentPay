#!/bin/bash
# create-kms-key.sh
# Creates an AWS KMS key suitable for ECDSA signing with Ethereum.
# Requires AWS CLI installed and configured with appropriate permissions.
#
# Usage: ./create-kms-key.sh [REGION]
#   REGION: AWS region (default: us-east-1)

set -e

REGION="${1:-us-east-1}"

echo "Creating KMS key in region $REGION..."

KEY_METADATA=$(aws kms create-key \
    --key-usage SIGN_VERIFY \
    --key-spec ECC_SECG_P256K1 \
    --description "AGENTPAY Production Signing Key" \
    --tags TagKey=Environment,TagValue=Production \
    --region "$REGION")

KEY_ID=$(echo "$KEY_METADATA" | jq -r '.KeyMetadata.KeyId')

echo "✅ KMS key created successfully."
echo "Key ID: $KEY_ID"
echo "Key ARN: $(echo "$KEY_METADATA" | jq -r '.KeyMetadata.Arn')"
echo ""
echo "Next steps:"
echo "1. Ensure the key is enabled (should be by default)."
echo "2. Add appropriate key policies for your IAM roles."
echo "3. Set the following environment variables in your deployment:"
echo "   - KMS_KEY_ID=$KEY_ID"
echo "   - KMS_REGION=$REGION"
echo "4. Validate the key using the KMSKeyManager.validate_kms_key() method."