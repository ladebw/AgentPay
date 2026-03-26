#!/bin/bash
# Validate all production environment variables
set -e

echo "Validating AGENTPAY production environment..."

# Check required variables
required_vars=(
    "DATABASE_URL"
    "REDIS_URL"
    "SECRET_KEY"
    "KEY_MANAGEMENT_MODE"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ ERROR: $var is not set"
        exit 1
    fi
    echo "✅ $var is set"
done

# Validate KMS configuration if in KMS mode
if [ "$KEY_MANAGEMENT_MODE" = "KMS" ]; then
    if [ -z "$KMS_KEY_ID" ] || [ -z "$KMS_REGION" ]; then
        echo "❌ ERROR: KMS mode requires KMS_KEY_ID and KMS_REGION"
        exit 1
    fi
    echo "✅ KMS configuration valid"
fi

# Test database connection
if ! psql "$DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo "❌ ERROR: Cannot connect to database"
    exit 1
fi
echo "✅ Database connection successful"

echo "✅ All environment checks passed!"