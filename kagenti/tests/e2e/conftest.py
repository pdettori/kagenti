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
def enabled_features(kagenti_config):
    """
    Extract enabled feature flags from config.

    Returns dict like: {'keycloak': True, 'spire': True, 'platform_operator': True, ...}
    Treats operators as features for unified handling.
    """
    if not kagenti_config:
        return {}

    features = {}
    charts = kagenti_config.get("charts", {})

    # Check charts.kagenti-deps.values.components
    deps_chart = charts.get("kagenti-deps", {})
    deps_components = deps_chart.get("values", {}).get("components", {})

    features["keycloak"] = deps_components.get("keycloak", {}).get("enabled", False)
    features["otel"] = deps_components.get("otel", {}).get("enabled", False)
    features["toolhive"] = deps_components.get("toolhive", {}).get("enabled", False)

    # Check spire
    features["spire"] = charts.get("spire", {}).get("enabled", False)

    # Check operators (treat as features)
    kagenti_chart = charts.get("kagenti", {})
    components = kagenti_chart.get("values", {}).get("components", {})

    features["platform_operator"] = components.get("platformOperator", {}).get(
        "enabled", False
    )
    features["kagenti_operator"] = components.get("kagentiOperator", {}).get(
        "enabled", False
    )

    return features


def pytest_collection_modifyitems(config, items):
    """
    Skip tests at collection time based on required features.

    This allows using decorators like @pytest.mark.requires_features(["platform_operator"])
    instead of runtime pytest.skip() calls.

    Uses positive condition: tests declare what features they REQUIRE, not what they exclude.
    """
    # Read config file at collection time (before fixtures are available)
    config_file = os.getenv("KAGENTI_CONFIG_FILE")
    if not config_file:
        # No config specified - don't skip any tests
        return

    config_path = pathlib.Path(config_file)
    if not config_path.is_absolute():
        # Resolve relative to repo root (same logic as kagenti_config fixture)
        repo_root = pathlib.Path(__file__).parent.parent.parent.parent
        config_path = repo_root / config_file

    if not config_path.exists():
        # Config file doesn't exist - don't skip any tests
        return

    try:
        with open(config_path) as f:
            kagenti_config = yaml.safe_load(f)
    except Exception:
        # Failed to load config - don't skip any tests
        return

    # Build enabled features dict (same logic as enabled_features fixture)
    enabled = {}
    charts = kagenti_config.get("charts", {})

    # deps components
    deps_chart = charts.get("kagenti-deps", {})
    deps_components = deps_chart.get("values", {}).get("components", {})
    enabled["keycloak"] = deps_components.get("keycloak", {}).get("enabled", False)
    enabled["otel"] = deps_components.get("otel", {}).get("enabled", False)
    enabled["toolhive"] = deps_components.get("toolhive", {}).get("enabled", False)

    # spire
    enabled["spire"] = charts.get("spire", {}).get("enabled", False)

    # operators
    kagenti_chart = charts.get("kagenti", {})
    components = kagenti_chart.get("values", {}).get("components", {})
    enabled["platform_operator"] = components.get("platformOperator", {}).get(
        "enabled", False
    )
    enabled["kagenti_operator"] = components.get("kagentiOperator", {}).get(
        "enabled", False
    )

    # Process each test item
    for item in items:
        # Check for @pytest.mark.requires_features(["feature1", "feature2"]) marker
        marker = item.get_closest_marker("requires_features")
        if marker:
            # Extract required features from marker (positive condition: what IS required)
            required_features = marker.args[0] if marker.args else []

            # Normalize to list if single string
            if isinstance(required_features, str):
                required_features = [required_features]

            # Check if all required features are enabled
            missing_features = [
                feature
                for feature in required_features
                if not enabled.get(feature, False)
            ]

            # Skip if any required feature is missing
            if missing_features:
                skip_reason = (
                    f"Test requires features: {required_features} "
                    f"(missing: {missing_features})"
                )
                item.add_marker(pytest.mark.skip(reason=skip_reason))
