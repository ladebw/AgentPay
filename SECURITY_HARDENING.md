# Security Hardening - Final Steps

This document outlines the recommended security hardening steps for production deployment of AGENTPAY with AWS KMS.

## 1. Enable KMS Key Rotation (automatic every 365 days)

AWS KMS supports automatic key rotation for customer‑managed keys. This ensures that the cryptographic material is regularly refreshed without manual intervention.

**Steps:**
- Navigate to AWS KMS Console → Customer managed keys.
- Select the key used for AGENTPAY signing.
- Choose **Key rotation** and enable **Automatically rotate this KMS key every year**.
- Confirm the rotation period (365 days).

**CLI command:**
```bash
aws kms enable-key-rotation --key-id <KEY_ID_OR_ARN>
```

## 2. Set up CloudTrail Alerts for KMS API Anomalies

Monitor KMS API calls for unauthorized or suspicious activity using CloudTrail and Amazon EventBridge (or CloudWatch Alarms).

**Steps:**
- Ensure CloudTrail is enabled and logging KMS events (default).
- Create an EventBridge rule that matches KMS API calls with error codes (`AccessDenied`, `InvalidKeyUsage`, etc.) or unusual patterns (e.g., high frequency of `Sign` operations).
- Route alerts to an SNS topic (email/Slack) or a dedicated security channel.

**Example EventBridge pattern:**
```json
{
  "source": ["aws.kms"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "errorCode": ["AccessDenied", "InvalidKeyUsage"],
    "eventName": ["Sign", "DescribeKey", "GetPublicKey"]
  }
}
```

## 3. Implement VPC Endpoints for KMS in Production

To avoid exposing KMS traffic over the public internet, create a VPC endpoint (interface or gateway) for KMS within your VPC.

**Steps:**
- In the VPC Console, create a new **Endpoint**.
- Select **AWS service** and choose `com.amazonaws.<region>.kms`.
- Choose the VPC and subnets where your AGENTPAY services run.
- Attach a security group that restricts traffic to only the necessary ports (HTTPS).
- Update your application’s KMS client configuration to use the VPC endpoint DNS name.

**Note:** This eliminates data transfer costs and improves latency while enhancing security.

## 4. Add Key Deletion Protection

Prevent accidental deletion of the KMS key by enabling deletion protection.

**Steps:**
- In the KMS key details, under **Key policy**, enable **Enable key deletion protection**.
- This ensures the key cannot be deleted without first disabling deletion protection.

**CLI command:**
```bash
aws kms enable-key-deletion-protection --key-id <KEY_ID_OR_ARN>
```

## 5. Set up IAM Policy with MFA Enforcement

Enforce Multi‑Factor Authentication (MFA) for any IAM user or role that can modify or delete the KMS key.

**Steps:**
- Create a custom IAM policy that includes the condition `"Bool": {"aws:MultiFactorAuthPresent": "true"}` for KMS actions (e.g., `kms:DisableKey`, `kms:DeleteKey`, `kms:ScheduleKeyDeletion`).
- Attach this policy to the relevant IAM users/roles.
- Consider using IAM Conditions to require MFA for all `kms:*` actions except read‑only operations like `kms:DescribeKey`, `kms:GetPublicKey`, `kms:Sign`.

**Example policy snippet:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "RequireMFAForDestructiveKMSActions",
            "Effect": "Deny",
            "Action": [
                "kms:DisableKey",
                "kms:DeleteKey",
                "kms:ScheduleKeyDeletion",
                "kms:UpdateKeyDescription",
                "kms:TagResource",
                "kms:UntagResource"
            ],
            "Resource": "*",
            "Condition": {
                "BoolIfExists": {
                    "aws:MultiFactorAuthPresent": "false"
                }
            }
        }
    ]
}
```

## 6. Regular Security Audits

- Review KMS key policies and IAM permissions quarterly.
- Rotate IAM access keys used by the application (if any) every 90 days.
- Monitor CloudTrail logs for anomalous KMS activity using AWS Security Hub or a third‑party SIEM.

## 7. Additional Considerations

- **Encryption at Rest:** Ensure all persistent data (databases, logs) are encrypted using KMS‑managed keys.
- **Network Isolation:** Deploy AGENTPAY services within a private subnet, using NAT gateways or VPC endpoints for external dependencies.
- **Least Privilege:** Limit the KMS key policy to only the necessary principals (IAM roles) and only the required actions (`kms:Sign`, `kms:GetPublicKey`, `kms:DescribeKey`).

## References

- [AWS KMS Key Rotation](https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html)
- [CloudTrail Monitoring for KMS](https://docs.aws.amazon.com/kms/latest/developerguide/logging-using-cloudtrail.html)
- [VPC Endpoints for KMS](https://docs.aws.amazon.com/kms/latest/developerguide/kms-vpc-endpoint.html)
- [KMS Deletion Protection](https://docs.aws.amazon.com/kms/latest/developerguide/deleting-keys.html)
- [IAM Conditions for MFA](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-mfa-present)