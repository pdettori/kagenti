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

from bullmq import Queue
import asyncio
from llama_stack.distribution.request_headers import NeedsRequestProviderData
from llama_stack.apis.agents import (
    AgentTurnCreateRequest,
    AgentTurnResponseEventType,
)
from typing import AsyncGenerator, List, Optional, Union
import asyncio
import uuid
import logging
import redis.asyncio as redis
from pydantic import BaseModel, ValidationError
from datetime import datetime
from typing import List
import json
from .redis import RedisSubscriber

EventType = AgentTurnResponseEventType

log = logging.getLogger(__name__)

TURNS_JOB_QUEUE = "turns"  # this might come from env or config


def gen_turn_job_id_list_key(agent_id, session_id) -> str:
    """Generates a key used to persist a list of turn_job_ids associated with a specific session"""
    return f"turn_job_list:{agent_id}:{session_id}"


# Dispatches jobs for agent turns using a Queue-Worker Pattern
class JobProducer(NeedsRequestProviderData):

    def __init__(self, persistence_store):
        self.persistence_store = persistence_store
        self.jobs_queue = Queue(TURNS_JOB_QUEUE)

    async def enqueue(self, request: AgentTurnCreateRequest) -> AsyncGenerator:
        log.info(f"enqueue(): {request.agent_id} and session {request.session_id}")

        turn_job_id = self.gen_turn_job_id(request.agent_id)
        await self.persist_turn_job_id_by_session_and_agent_id(
            request.agent_id, request.session_id, turn_job_id
        )
        await self.persist_turn_job_data(turn_job_id, request)

        await self.add_job_to_queue(turn_job_id)

        # wait for events from redis pub-sub
        subscriber = RedisSubscriber(channel_name=turn_job_id)
        await subscriber.connect()
        log.info(f"waiting for events on channel {turn_job_id}")
        async for event in subscriber.wait_for_events():
            yield event

    async def persist_turn_job_data(self, turn_job_id, request) -> str:
        turn_job_data = request.model_dump_json()
        await self.persistence_store.set(turn_job_id, turn_job_data)

    def gen_turn_job_id(self, agent_id) -> str:
        return f"turn_job:{agent_id}:{str(uuid.uuid4())}"

    async def add_job_to_queue(self, turn_job_id):
        job = await self.jobs_queue.add(turn_job_id, {"turn_job_id": turn_job_id})
        log.info(f"Job for turn_job_id {turn_job_id} added with ID: {job.id}")

    async def persist_turn_job_id_by_session_and_agent_id(
        self, agent_id, session_id, turn_job_id
    ):
        """Stores the list of turn_job_id associated with a session"""
        key = gen_turn_job_id_list_key(agent_id, session_id)

        list_raw = await self.persistence_store.get(key)
        try:
            if list_raw:
                list_json = json.loads(list_raw)
                turn_jobs_list = TurnJobsList.model_validate_json(list_json)
            else:
                turn_jobs_list = TurnJobsList()
        except ValidationError as e:
            log.error(f"Failed to validate JSON due to: {e}")
            turn_jobs_list = TurnJobsList()

        item = TurnJobItem.create(turn_job_id=turn_job_id)
        turn_jobs_list.append_item(item)

        updated_json = turn_jobs_list.model_dump_json()
        await self.persistence_store.set(key, updated_json)


class TurnJobItem(BaseModel):
    """TurnJobItem represents info required to associate a list of turns with an agent and session ids"""

    turn_job_id: str
    creation_time: datetime

    def __post_init__(self):
        log.info(f"Creating an TurnJobItem object with id: {self.turn_job_id}")

    @classmethod
    def create(cls, turn_job_id: str, creation_time: datetime = None):
        """Convenience method to initialize with default time."""
        if not creation_time:
            creation_time = datetime.now()
        return cls(turn_job_id=turn_job_id, creation_time=creation_time)


class TurnJobsList(BaseModel):
    items: List[TurnJobItem] = []

    def append_item(self, item: TurnJobItem) -> None:
        """Append an item to the list."""
        self.items.append(item)

    def get_last_item(self) -> Optional[TurnJobItem]:
        """Retrieve the last item appended to the list."""
        if self.items:
            return self.items[-1]
        return None


