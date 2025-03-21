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

from typing import Optional
from pydantic import BaseModel
import os
import redis.asyncio as redis
from redis import Redis
from llama_stack.distribution.configure import parse_and_maybe_upgrade_config
from llama_stack.providers.utils.kvstore import kvstore_impl
from llama_stack.providers.utils.kvstore.config import (
    SqliteKVStoreConfig,
    RedisKVStoreConfig,
    PostgresKVStoreConfig,
)
from redis.asyncio.retry import Retry
from redis.exceptions import TimeoutError, ConnectionError
from redis.backoff import ExponentialBackoff

DEFAULT_AGENT_WORKER_PROVIDER = "inline::multi-framework"

async def initialize_kvstore_from_config(
    config_dict, provider_type=DEFAULT_AGENT_WORKER_PROVIDER
) -> kvstore_impl:
    config = parse_and_maybe_upgrade_config(config_dict)

    agent_providers = config.providers.get("agents", [])
    if agent_providers:
        for provider in agent_providers:
            if provider.provider_type == provider_type:
                agent_config = provider.config
                persistence_store_config = agent_config.get("persistence_store")
                break

    if persistence_store_config:
        if persistence_store_config["type"] == "sqlite":
            kvstore_config = SqliteKVStoreConfig(**persistence_store_config)
        elif persistence_store_config["type"] == "redis":
            kvstore_config = RedisKVStoreConfig(**persistence_store_config)
        elif persistence_store_config["type"] == "postgres":
            kvstore_config = PostgresKVStoreConfig(**persistence_store_config)
        else:
            raise ValueError(
                f"Unsupported KVStore type: {persistence_store_config['type']}"
            )
        kvstore = await kvstore_impl(kvstore_config)
        return kvstore
    else:
        raise ValueError("persistence_store not configured for the agent")


async def initialize_redis_store_from_config(
    config_dict, provider_type=DEFAULT_AGENT_WORKER_PROVIDER
) -> Redis:
    config = parse_and_maybe_upgrade_config(config_dict)

    agent_providers = config.providers.get("agents", [])
    if agent_providers:
        for provider in agent_providers:
            if provider.provider_type == provider_type:
                agent_config = provider.config
                redis_store_config = agent_config.get("redis_store")
                break

    if redis_store_config:
        host = redis_store_config["host"]
        port = redis_store_config["port"]
        redis_options = {
            "decode_responses": True,
            "health_check_interval": 10,
            "retry": Retry(ExponentialBackoff(cap=10, base=1), 5),
            "retry_on_error": [ConnectionError, TimeoutError, ConnectionResetError],
        }
        return await redis.from_url(f"redis://{host}:{port}", **redis_options)
    else:
        raise ValueError("redis_store not configured for the agent")


class WorkerConfig(BaseModel):
    queue_name: str
    health_check_port: int


async def get_worker_config(
    config_dict, provider_type=DEFAULT_AGENT_WORKER_PROVIDER
) -> WorkerConfig:
    config = parse_and_maybe_upgrade_config(config_dict)
    agent_providers = config.providers.get("agents", [])
    if agent_providers:
        for provider in agent_providers:
            if provider.provider_type == provider_type:
                agent_config = provider.config
                worker_config_dict = agent_config.get("worker_config")
                break

    if worker_config_dict:
        try:
            return WorkerConfig(**worker_config_dict)
        except ValueError as e:
            raise ValueError(f"redis_store not configured correctly {e}")
    else:
        raise ValueError("redis_store not configured for the agent")
