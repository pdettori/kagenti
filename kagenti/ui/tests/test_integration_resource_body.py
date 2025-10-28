from lib import build_utils


class DummySt:
    def info(self, *_a, **_k):
        return None

    def warning(self, *_a, **_k):
        return None


def test_construct_tool_resource_body_includes_valuefrom(monkeypatch):
    """Integration test: ensure structured env entries flow into the resource body."""

    # Monkeypatch secrets fetch to avoid requiring a K8s client
    monkeypatch.setattr(
        build_utils,
        "get_secret_data",
        lambda core_v1_api, namespace, name, key: "gituser",
    )
    # Avoid Keycloak calls
    monkeypatch.setattr(build_utils, "_get_keycloak_client_secret", lambda st, name: "")

    st = DummySt()

    additional_env = [
        {
            "name": "SECRET_KEY",
            "valueFrom": {"secretKeyRef": {"name": "openai-secret", "key": "apikey"}},
        }
    ]

    body = build_utils._construct_tool_resource_body(
        st_object=st,
        core_v1_api=None,
        build_namespace="test-ns",
        resource_name="my-tool",
        resource_type="Tool",
        repo_url="https://example.com/repo.git",
        repo_branch="main",
        source_subfolder="",
        protocol="mcp",
        framework="test",
        description="desc",
        build_from_source=True,
        registry_config=None,
        additional_env_vars=additional_env,
        image_tag="latest",
        pod_config=None,
    )

    assert body is not None
    env_list = body.get("spec", {}).get("deployer", {}).get("env", [])
    assert any(
        e.get("name") == "SECRET_KEY" and "valueFrom" in e for e in env_list
    ), f"SECRET_KEY with valueFrom not found in env list: {env_list}"
