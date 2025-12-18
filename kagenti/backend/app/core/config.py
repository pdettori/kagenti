# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""
Application configuration using Pydantic Settings.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application settings
    debug: bool = False
    domain_name: str = "localtest.me"

    # CORS settings
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://kagenti-ui.localtest.me:8080",
    ]

    # Kubernetes CRD settings
    crd_group: str = "agent.kagenti.dev"
    crd_version: str = "v1alpha1"
    agents_plural: str = "agents"
    agentbuilds_plural: str = "agentbuilds"

    # ToolHive CRD settings
    toolhive_crd_group: str = "toolhive.stacklok.dev"
    toolhive_crd_version: str = "v1alpha1"
    toolhive_mcp_plural: str = "mcpservers"

    # Label settings
    kagenti_label_prefix: str = "kagenti.io/"
    enabled_namespace_label_key: str = "kagenti-enabled"
    enabled_namespace_label_value: str = "true"

    # External service URLs
    traces_dashboard_url: str = ""
    network_dashboard_url: str = ""
    mcp_inspector_url: str = ""
    keycloak_url: str = ""

    # Authentication settings
    enable_auth: bool = False  # Set to True to enable Keycloak auth
    keycloak_realm: str = "master"
    keycloak_client_id: str = "kagenti-ui"

    @property
    def kagenti_type_label(self) -> str:
        return f"{self.kagenti_label_prefix}type"

    @property
    def kagenti_protocol_label(self) -> str:
        return f"{self.kagenti_label_prefix}protocol"

    @property
    def kagenti_framework_label(self) -> str:
        return f"{self.kagenti_label_prefix}framework"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
