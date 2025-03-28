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

import asyncio
from typing import AsyncGenerator
import asyncio
import logging
import redis.asyncio as redis
from llama_stack.apis.agents import (
    AgentTurnResponseStreamChunk,
    AgentTurnResponseEventType
)

EventType = AgentTurnResponseEventType

log = logging.getLogger(__name__)

class RedisSubscriber:
    def __init__(self, channel_name):
        self.channel_name = channel_name
        self.redis = None
        self.pubsub = None
        self.end_turn = False

    async def connect(self):
        self.redis = await redis.from_url("redis://localhost")
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(self.channel_name)
        log.info(f"Subscribed to {self.channel_name}")

    async def wait_for_events(self) -> AsyncGenerator:
        if not self.pubsub:
            raise RuntimeError("You must call connect() before iterating")

        while True:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1
                )
                if message and message["type"] == "message":
                    try:
                        json_event = message["data"].decode("utf-8")
                    except UnicodeDecodeError:
                        log.error("Failed to decode message data")

                    chunk = AgentTurnResponseStreamChunk.model_validate_json(json_event)

                    # closing the SSE connection after the last event requires return without data
                    # this will cause the server to send a content length of 0 and no data after that
                    # normally there will be a content lenght line followed by a content line
                    # e.g.,
                    # ac <-content length in hex
                    # data: {"event":{"payload":{"event_type":"step_progress","step_type":"inference",
                    # "step_id":"b5d7edca-44a3-4dc7-9426-1b82e05c2b6c",
                    # "delta":{"type":"text","text":" more"}}}} <- data
                    if (
                        chunk is not None
                        and chunk.event.payload.event_type
                        == EventType.turn_complete.value
                    ):
                        yield chunk
                        return
                    else:
                        yield chunk
            except asyncio.CancelledError as e:
                raise e
            except Exception as e:
                log.exception("Unexpected error: %s", e)
                raise e

    async def disconnect(self):
        if self.pubsub:
            await self.pubsub.unsubscribe(self.channel_name)
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()

class RedisPublisher:
    def __init__(self):
        self.redis = None

    async def connect(self):
        self.redis = await redis.from_url("redis://localhost")

    async def publish(self, channel, event: AgentTurnResponseStreamChunk):
        if not self.redis:
            raise Exception("Not connected to Redis. Call connect() first.")

        await self.redis.publish(
            channel, AgentTurnResponseStreamChunk.model_dump_json(event)
        )

    async def disconnect(self):
        if self.pubsub:
            await self.pubsub.unsubscribe(self.channel_name)
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
