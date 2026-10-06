"""Explicit development and production configuration."""

import os
import secrets


def secret_key(*, development: bool = False) -> str:
    configured = os.environ.get("SECRET_KEY")
    if configured:
        return configured
    if development or os.environ.get("APP_ENV") == "development":
        return secrets.token_hex(32)
    raise RuntimeError(
        "SECRET_KEY must be configured in production. "
        "For local development, run python main.py or set APP_ENV=development."
    )
