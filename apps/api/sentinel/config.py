from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    environment: str = 'development'
    database_url: str
    redis_url: str
    oidc_issuer: str = 'http://localhost:8081/realms/sentinel'
    oidc_jwks_url: str = 'http://keycloak:8080/realms/sentinel/protocol/openid-connect/certs'
    oidc_audience: str = 'sentinel-api'
    s3_endpoint: str = 'objectstore:8333'
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = 'sentinel-private'
    s3_secure: bool = False
    reference_hmac_key: str = Field(min_length=32)
    reference_hmac_version: str = 'local-v1'
    clamav_host: str = 'clamav'
    clamav_port: int = 3310
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pdf_pages: int = 30
    synthetic_mode: bool = True
    decision_mfa_required: bool = False
    decision_auth_max_age_seconds: int = Field(default=300, ge=30, le=900)
    ai_assist_enabled: bool = False
    ai_base_url: str = 'http://host.docker.internal:11434'
    ai_model: str = 'qwen2.5:0.5b'
    mock_attestation_key: str = Field(default='', repr=False)
    maturity_thresholds: tuple[int, ...] = (90, 30, 7)
    sandbox_url: str = 'http://sandbox:8000'
    sandbox_api_key: str = Field(default='', repr=False)
    sandbox_signing_key: str = Field(default='', repr=False)
    smtp_host: str = 'mailpit'
    smtp_port: int = 1025


@lru_cache
def settings() -> Settings:
    config = Settings()
    if config.environment != 'development':
        raise RuntimeError('Production deployment is gated pending regulatory and operational qualification')
    return config
