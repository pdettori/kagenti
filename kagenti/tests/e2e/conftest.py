"""
E2E-specific pytest fixtures.

Config-driven fixtures that adapt tests based on installer configuration.
"""

import os
import pathlib

import pytest
import yaml


@pytest.fixture(scope="session")
def kagenti_config():
    """
    Load Kagenti installer configuration from YAML file.

    Reads from KAGENTI_CONFIG_FILE environment variable.
    If not set, returns None (tests will use defaults or skip).
    """
    config_file = os.getenv("KAGENTI_CONFIG_FILE")
    if not config_file:
        return None

    config_path = pathlib.Path(config_file)
    if not config_path.is_absolute():
        # Resolve relative to repo root
        repo_root = pathlib.Path(__file__).parent.parent.parent.parent
        config_path = repo_root / config_file

    if not config_path.exists():
        pytest.fail(f"Config file not found: {config_path}")

    with open(config_path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def operator_mode(kagenti_config):
    """
    Determine which operator is active: 'platform_operator' or 'kagenti_operator'.

    Returns None if config not available.
    """
    if not kagenti_config:
        return None

    charts = kagenti_config.get("charts", {})
    kagenti_chart = charts.get("kagenti", {})
    components = kagenti_chart.get("values", {}).get("components", {})

    platform_enabled = components.get("platformOperator", {}).get("enabled", False)
    kagenti_enabled = components.get("kagentiOperator", {}).get("enabled", False)

    if kagenti_enabled:
        return "kagenti_operator"
    elif platform_enabled:
        return "platform_operator"
    else:
        return None


@pytest.fixture(scope="session")
def enabled_features(kagenti_config):
    """
    Extract enabled feature flags from config.

    Returns dict like: {'keycloak': True, 'spire': True, ...}
    """
    if not kagenti_config:
        return {}

    features = {}

    # Check charts.kagenti-deps.values.components
    charts = kagenti_config.get("charts", {})
    deps_chart = charts.get("kagenti-deps", {})
    deps_components = deps_chart.get("values", {}).get("components", {})

    features["keycloak"] = deps_components.get("keycloak", {}).get("enabled", False)
    features["otel"] = deps_components.get("otel", {}).get("enabled", False)
    features["toolhive"] = deps_components.get("toolhive", {}).get("enabled", False)

    # Check spire
    features["spire"] = charts.get("spire", {}).get("enabled", False)

    return features
