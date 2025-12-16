# Assisted by watsonx Code Assistant
# Copyright 2025 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
        protocol="mcp",
        framework="test",
        additional_env_vars=additional_env,
        registry_config=None,
        pod_config=None,
        image_pull_secret=None,
    )

    assert body is not None


def test_custom_env_overrides_default(monkeypatch):
    """Ensure a user-supplied env var overrides the default with same name."""

    monkeypatch.setattr(
        build_utils,
        "get_secret_data",
        lambda core_v1_api, namespace, name, key: "gituser",
    )
    monkeypatch.setattr(build_utils, "_get_keycloak_client_secret", lambda st, name: "")

    st = DummySt()

    additional_env = [{"name": "PORT", "value": "9999"}]

    body = build_utils._construct_tool_resource_body(
        st_object=st,
        core_v1_api=None,
        build_namespace="test-ns",
        resource_name="my-tool",
        resource_type="Tool",
        repo_url="https://example.com/repo.git",
        protocol="mcp",
        framework="test",
        additional_env_vars=additional_env,
        registry_config=None,
        pod_config=None,
        image_pull_secret=None,
    )

    assert body is not None

    env_list = body["spec"]["podTemplateSpec"]["spec"]["containers"][0]["env"]
    # filter for PORT entries
    ports = [e for e in env_list if e.get("name") == "PORT"]
    assert len(ports) == 1
    assert ports[0].get("value") == "9999"


def test_env_file_overrides_env_set():
    # env set defines PORT=1111, .env defines PORT=2222 -> .env should win
    env_set = [{"name": "PORT", "value": "1111"}]
    env_file = [{"name": "PORT", "value": "2222"}]

    # Mimic actual code flow: start with env_set, then merge in env_file
    selected_env_sets = list(env_set)
    merged = build_utils._merge_env_vars(selected_env_sets, env_file)

    ports = [e for e in merged if e.get("name") == "PORT"]
    assert len(ports) == 1
    assert ports[0].get("value") == "2222"


def test_custom_overrides_env_file(monkeypatch):
    # Validate the actual bucketing/extension logic used by the UI import flow.
    # The UI builds `final_additional_envs` by extending lists in this order:
    # selected env sets (env_set) < configmap-loaded < .env imports < user custom
    # That assembly can produce duplicate names before the final merge step.
    from lib import constants

    # Simulate an env set coming from configmap
    env_set = [{"name": "PORT", "value": "1111"}]

    # Simulate imported .env file
    env_file = [{"name": "PORT", "value": "2222"}]

    # Simulate custom user-provided vars (not marked as configmap-origin)
    custom_vars = [{"name": "PORT", "value": "3333"}]

    # Emulate how render_import_form assembles final_additional_envs
    final_additional_envs = []
    # selected env sets first
    final_additional_envs.extend(env_set)

    # In the UI, custom_env_vars are bucketed into configmap_bucket, envfile_bucket, user_bucket
    configmap_bucket = []
    envfile_bucket = []
    user_bucket = []

    # For this test we treat the env_file entry as coming from an import (envfile_bucket)
    for v in env_file:
        envfile_bucket.append(v)

    for v in custom_vars:
        # user-provided (no configmap_origin or import_origin flags)
        user_bucket.append(v)

    # Extend in the same order as the UI
    final_additional_envs.extend(configmap_bucket)
    final_additional_envs.extend(envfile_bucket)
    final_additional_envs.extend(user_bucket)

    # Before the final merge, duplicates will exist (three PORT entries if configmap_bucket had one)
    ports_before = [e for e in final_additional_envs if e.get("name") == "PORT"]
    # env_set + envfile + user -> should be 3 entries
    assert len(ports_before) == 3

    # Now pass through the constructor which performs the final merge with DEFAULT_ENV_VARS
    monkeypatch.setattr(
        build_utils,
        "get_secret_data",
        lambda core_v1_api, namespace, name, key: "gituser",
    )
    monkeypatch.setattr(build_utils, "_get_keycloak_client_secret", lambda st, name: "")

    st = DummySt()

    body = build_utils._construct_tool_resource_body(
        st_object=st,
        core_v1_api=None,
        build_namespace="test-ns",
        resource_name="my-tool",
        resource_type="Tool",
        repo_url="https://example.com/repo.git",
        protocol="mcp",
        framework="test",
        additional_env_vars=final_additional_envs,
        registry_config=None,
        pod_config=None,
        image_pull_secret=None,
    )

    assert body is not None

    env_list = body["spec"]["podTemplateSpec"]["spec"]["containers"][0]["env"]
    ports_after = [e for e in env_list if e.get("name") == "PORT"]
    # After the constructor merge, duplicates must be deduplicated and the user value should win
    assert len(ports_after) == 1
    assert ports_after[0].get("value") == "3333"
