import os
from enum import Enum
from typing import List, Literal, Optional

import boto3
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class KeyManagementMode(str, Enum):
    MOCK = "mock"
    KMS = "kms"
    NON_CUSTODIAL = "non_custodial"


class Settings(BaseSettings):
    environment: str = "development"
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost/agentpay"

    # Security
    api_key_salt: str = Field(default="change-me", env="API_KEY_SALT")
    secret_key: str = Field(default="change-me", env="SECRET_KEY")

    # Blockchain
    chain_id: int = 137  # Polygon Mainnet
    usdc_address: str = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    rpc_url: str = "https://polygon-rpc.com"
    private_key: Optional[str] = None  # For real transactions (deprecated)

    # Key Management
    key_management_mode: KeyManagementMode = KeyManagementMode.MOCK
    kms_key_id: Optional[str] = None  # AWS KMS Key ID
    kms_region: Optional[str] = "us-east-1"

    # Webhooks
    webhook_retry_attempts: int = 3
    webhook_timeout: int = 5
    webhook_signing_secret: str = Field(
        default="change-me", env="WEBHOOK_SIGNING_SECRET"
    )

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 100
    redis_url: Optional[str] = None  # e.g., redis://localhost:6379

    # Idempotency
    idempotency_key_ttl: int = 86400  # 24 hours in seconds

    # Gas
    gas_price_multiplier: float = 1.2
    max_gas_price_gwei: int = 500

    # Gas Sponsorship
    enable_gas_sponsorship: bool = Field(False, env="ENABLE_GAS_SPONSORSHIP")
    sponsor_mode: Literal["defender", "biconomy", "custom"] = "defender"
    max_sponsor_amount_usd: float = Field(10.0, env="MAX_SPONSOR_AMOUNT_USD")
    sponsor_whitelist: List[str] = []  # Agent IDs allowed for sponsorship
    # Defender Config
    defender_api_key: Optional[str] = Field(None, env="DEFENDER_API_KEY")
    defender_api_secret: Optional[str] = Field(None, env="DEFENDER_API_SECRET")
    defender_relayer_id: Optional[str] = Field(None, env="DEFENDER_RELAYER_ID")
    forwarder_address: Optional[str] = Field(None, env="FORWARDER_ADDRESS")

    # Logging
    log_level: str = "INFO"
    log_json: bool = False

    # CORS
    cors_origins: List[str] = []

    @field_validator(
        "api_key_salt", "secret_key", "webhook_signing_secret", mode="after"
    )
    def validate_secrets_not_default(cls, v, info):
        if info.data.get("environment") == "production":
            default_values = {
                "api_key_salt": "change-me",
                "secret_key": "change-me",
                "webhook_signing_secret": "change-me",
            }
            field_name = info.field_name
            if v == default_values[field_name]:
                raise ValueError(f"{field_name} must be changed in production")
        return v

    @field_validator("key_management_mode", mode="after")
    def validate_key_management_mode(cls, v, info):
        environment = info.data.get("environment", "development")
        if environment == "production":
            if v == KeyManagementMode.MOCK:
                raise ValueError("Cannot use MOCK key management mode in production")
            if v == KeyManagementMode.KMS and not info.data.get("kms_key_id"):
                raise ValueError("kms_key_id must be set when using KMS mode")
            if v == KeyManagementMode.NON_CUSTODIAL and not info.data.get(
                "private_key"
            ):
                raise ValueError(
                    "private_key must be set when using NON_CUSTODIAL mode"
                )
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_secret(secret_name: str) -> str:
    """Retrieve secret from AWS Secrets Manager"""
    region = os.environ.get("KMS_REGION", "us-east-1")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return response["SecretString"]


settings = Settings()

# Override with secrets in production
if settings.environment == "production":
    settings.secret_key = get_secret("agentpay/secret-key")
    settings.database_url = get_secret("agentpay/database-url")
    settings.api_key_salt = get_secret("agentpay/api-key-salt")
    settings.webhook_signing_secret = get_secret("agentpay/webhook-signing-secret")
