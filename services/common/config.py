"""Configuration settings for Sutra platform services.
Traceability: REQ-1.1 - REQ-6.6
"""

import os
import tempfile
from typing import Literal
from pydantic import BaseModel, Field


def _default_db_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    if "OneDrive" in os.getcwd():
        # Avoid Windows OneDrive sync file locking during local dev/tests
        temp_db = os.path.join(tempfile.gettempdir(), "sutra.db").replace("\\", "/")
        return f"sqlite:///{temp_db}"
    return "sqlite:///sutra.db"


def _default_sync_db_url() -> str:
    env_sync = os.getenv("SYNC_DATABASE_URL")
    if env_sync:
        return env_sync.replace("+asyncpg", "").replace("+aiosqlite", "")
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    if "OneDrive" in os.getcwd():
        temp_db = os.path.join(tempfile.gettempdir(), "sutra.db").replace("\\", "/")
        return f"sqlite:///{temp_db}"
    return "sqlite:///sutra.db"


class Settings(BaseModel):
    # Environment & Service Identification
    ENV: str = Field(default_factory=lambda: os.getenv("ENV", "development"))
    DEBUG: bool = Field(default_factory=lambda: os.getenv("DEBUG", "true").lower() == "true")
    
    # Database
    DATABASE_URL: str = Field(default_factory=_default_db_url)
    SYNC_DATABASE_URL: str = Field(default_factory=_default_sync_db_url)

    # JWT & Auth
    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY", "sutra_insecure_development_secret_key_change_in_prod_123")
    )
    JWT_ALGORITHM: str = Field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    )

    # Service Ports & URLs
    API_PORT: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    API_URL: str = Field(default_factory=lambda: os.getenv("API_URL", "http://localhost:8000"))

    GATEWAY_PORT: int = Field(default_factory=lambda: int(os.getenv("GATEWAY_PORT", "8001")))
    GATEWAY_URL: str = Field(default_factory=lambda: os.getenv("GATEWAY_URL", "http://localhost:8001"))

    AUDIT_PORT: int = Field(default_factory=lambda: int(os.getenv("AUDIT_PORT", "8002")))
    AUDIT_URL: str = Field(default_factory=lambda: os.getenv("AUDIT_URL", "http://localhost:8002"))
    AUDIT_SERVICE_TOKEN: str = Field(
        default_factory=lambda: os.getenv("AUDIT_SERVICE_TOKEN", "sutra_audit_internal_service_token_xyz")
    )
    AUDIT_STORE_REDACTED_TEXT: bool = Field(
        default_factory=lambda: os.getenv("AUDIT_STORE_REDACTED_TEXT", "false").lower() == "true"
    )

    RAG_PORT: int = Field(default_factory=lambda: int(os.getenv("RAG_PORT", "8003")))
    RAG_URL: str = Field(default_factory=lambda: os.getenv("RAG_URL", "http://localhost:8003"))

    ML_PORT: int = Field(default_factory=lambda: int(os.getenv("ML_PORT", "8004")))
    ML_URL: str = Field(default_factory=lambda: os.getenv("ML_URL", "http://localhost:8004"))

    # Vector Store & Storage
    EMBEDDING_PROVIDER: Literal["local", "sentence_transformers"] = Field(
        default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "local")  # type: ignore
    )
    VECTOR_STORE: Literal["chroma", "qdrant"] = Field(
        default_factory=lambda: os.getenv("VECTOR_STORE", "chroma")  # type: ignore
    )
    CHROMA_PERSIST_DIRECTORY: str = Field(
        default_factory=lambda: os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
    )
    MINIO_ENDPOINT: str = Field(default_factory=lambda: os.getenv("MINIO_ENDPOINT", "localhost:9000"))
    MINIO_ACCESS_KEY: str = Field(default_factory=lambda: os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
    MINIO_SECRET_KEY: str = Field(default_factory=lambda: os.getenv("MINIO_SECRET_KEY", "minioadmin"))
    MINIO_BUCKET: str = Field(default_factory=lambda: os.getenv("MINIO_BUCKET", "sutra-corpus"))
    LOCAL_STORAGE_DIR: str = Field(
        default_factory=lambda: os.getenv("LOCAL_STORAGE_DIR", "./data/storage")
    )

    # ML & Providers
    INJECTION_BACKEND: Literal["transformer", "fallback"] = Field(
        default_factory=lambda: os.getenv("INJECTION_BACKEND", "fallback")  # type: ignore
    )
    UPSTREAM_PROVIDER: str = Field(
        default_factory=lambda: os.getenv("UPSTREAM_PROVIDER", "mock")
    )
    UPSTREAM_BASE_URL: str = Field(
        default_factory=lambda: os.getenv("UPSTREAM_BASE_URL", "http://localhost:8000/v1/mock")
    )
    UPSTREAM_API_KEY: str = Field(
        default_factory=lambda: os.getenv("UPSTREAM_API_KEY", "mock-upstream-key")
    )


settings = Settings()
