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
    from lib import constants

    env_set = [{"name": "PORT", "value": "1111"}]
    env_file = [{"name": "PORT", "value": "2222"}]

    merged1 = build_utils._merge_env_vars(constants.DEFAULT_ENV_VARS, env_set)
    merged2 = build_utils._merge_env_vars(merged1, env_file)

    ports = [e for e in merged2 if e.get("name") == "PORT"]
    assert len(ports) == 1
    assert ports[0].get("value") == "2222"


def test_custom_overrides_env_file():
    # .env defines PORT=2222, user custom defines PORT=3333 -> custom should win
    from lib import constants

    env_file = [{"name": "PORT", "value": "2222"}]
    custom = [{"name": "PORT", "value": "3333"}]

    merged1 = build_utils._merge_env_vars(constants.DEFAULT_ENV_VARS, env_file)
    merged2 = build_utils._merge_env_vars(merged1, custom)

    ports = [e for e in merged2 if e.get("name") == "PORT"]
    assert len(ports) == 1
    assert ports[0].get("value") == "3333"
