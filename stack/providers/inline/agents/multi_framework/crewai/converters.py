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

from llama_stack.apis.agents import (
    AgentTurnResponseStreamChunk,
    AgentTurnResponseEvent,
    AgentTurnResponseStepProgressPayload,
    AgentTurnResponseTurnStartPayload,
    AgentTurnResponseTurnCompletePayload,
    AgentTurnResponseStepStartPayload,
    AgentTurnResponseStepCompletePayload,
    StepType,
    Turn,
    ToolExecutionStep,
    ToolCall,
    ToolResponse,
)
from typing import List
from llama_stack.apis.inference import UserMessage, CompletionMessage
from llama_stack.apis.common.content_types import (
    TextDelta,
)
from llama_models.datatypes import (
    StopReason,
)

import logging
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from datetime import datetime
import asyncio
import uuid
from pydantic import BaseModel
import ast

log = logging.getLogger(__name__)


class EventProcessor:
    """Processes events streamed from the crew and converts
    them in the format used by llama stack"""

    def __init__(self):
        self.event_queue = asyncio.Queue()  # Async queue to store events
        self.started = False
        self.turn_start_time = datetime.now()
        self.tool_start_times = {}
        self.handlers = {
            "AgentAction": self.action_handler,
            "AgentFinish": self.finish_handler,
            "ToolResult": self.tool_result_handler,
        }
        self.finished = asyncio.Event()  # Event to signal processing completion
        self.turn_id = str(uuid.uuid4())
        self.session_id = ""
        self.input_messages = []

    def set_session_id(self, session_id):
        self.session_id = session_id

    async def enqueue_event(self, step):
        """Asynchronously enqueue events for processing."""
        print(f"enqueing step {step}")
        await self.event_queue.put(step)

    # Wrapper function to call the enqueue_event
    # since the crew.kickoff expects a sync callback function
    def enqueue_event_wrapper(self, event):
        try:
            # Try to get the existing event loop
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # If no loop exists, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the coroutine on the event loop
        loop.run_until_complete(self.enqueue_event(event))

    async def process_events(self):
        """Process events concurrently from the queue."""
        while not self.finished.is_set() or not self.event_queue.empty():
            print("waiting on queue")
            try:
                step = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                print("got stuff from queue")

                # emit the start turn event
                if not self.started:
                    self.started = True
                    yield AgentTurnResponseStreamChunk(
                        event=AgentTurnResponseEvent(
                            payload=AgentTurnResponseTurnStartPayload(
                                turn_id=self.turn_id,
                            )
                        )
                    )
                handler_type = type(step).__name__
                handler = self.handlers.get(handler_type)
                if handler:
                    completed, events = handler(step)
                    for event in events:
                        yield event
                    if completed == True:
                        self.finished.set()
                self.event_queue.task_done()
            except asyncio.TimeoutError:
                # Continue looping to check finished condition
                pass

    def parse_action(self, text):
        lines = text.strip().split("\n")
        thought = action = action_input = observation = ""

        for line in lines:
            if line.startswith("Thought:"):
                thought = line
            elif line.startswith("Action:"):
                action = line.replace("Action: ", "").strip()
            elif line.startswith("Action Input:"):
                action_input = line.replace("Action Input: ", "").strip()
            elif line.startswith("Observation:"):
                observation = line.replace("Observation: ", "").strip()

        return ActionData(
            thought=thought,
            action=action,
            action_input=action_input,
            observation=observation,
        )

    def action_handler(self, step) -> bool | List[AgentTurnResponseStreamChunk]:
        """generates events for the agent action
        crewai is not so great with generating events. Thought,
        tool call and result of the tool call all all generated together
        so we have to emite multiple events at the same time"""
        action_data = self.parse_action(step.text)
        step_id = str(uuid.uuid4)
        events = []
        events = events + [
            AgentTurnResponseStreamChunk(
                event=AgentTurnResponseEvent(
                    payload=AgentTurnResponseStepProgressPayload(
                        step_type=StepType.inference.value,
                        step_id=step_id,
                        delta=TextDelta(text=f"{action_data.thought}\n"),
                    )
                )
            )
        ]
        events = events + [
            AgentTurnResponseStreamChunk(
                event=AgentTurnResponseEvent(
                    payload=AgentTurnResponseStepStartPayload(
                        step_type=StepType.tool_execution.value,
                        step_id=step_id,
                    )
                )
            )
        ]
        events = events + [
            self.generate_tool_completed_event(
                step_id,
                action_data.action,
                action_data.action_input,
                action_data.observation,
            )
        ]
        return False, events

    def finish_handler(self, step) -> bool | List[AgentTurnResponseStreamChunk]:
        step_id = str(uuid.uuid4)
        events = []
        events = events + [
            AgentTurnResponseStreamChunk(
                event=AgentTurnResponseEvent(
                    payload=AgentTurnResponseStepProgressPayload(
                        step_type=StepType.inference.value,
                        step_id=step_id,
                        delta=TextDelta(text=f"{step.output}\n"),
                    )
                )
            )
        ]
        events = events + [
            AgentTurnResponseStreamChunk(
                event=AgentTurnResponseEvent(
                    payload=AgentTurnResponseTurnCompletePayload(
                        turn=Turn(
                            turn_id=self.turn_id,
                            session_id=self.session_id,
                            input_messages=self.input_messages,
                            output_message=CompletionMessage(
                                content=step.output, stop_reason="end_of_turn"
                            ),
                            started_at=self.turn_start_time,
                            completed_at=datetime.now(),
                            steps=[],
                        )
                    )
                )
            )
        ]
        return True, events

    # this is not used as this event is already included in AgentAction
    def tool_result_handler(self, step):
        return False, []

    def generate_tool_completed_event(
        self, step_id, tool_name, tool_input, tool_output
    ):
        tool_call_id = str(uuid.uuid4)

        tool_call = ToolCall(
            call_id=tool_call_id,
            tool_name=tool_name,
            arguments=ast.literal_eval(tool_input),
        )
        tool_execution_step = ToolExecutionStep(
            step_id=step_id,
            turn_id=self.turn_id,
            tool_calls=[tool_call],
            tool_responses=[
                ToolResponse(
                    call_id=tool_call_id,
                    tool_name=tool_name,
                    content=tool_output,
                )
            ],
            # crewAI does not give any info about when a tool starts!!
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        return AgentTurnResponseStreamChunk(
            event=AgentTurnResponseEvent(
                payload=AgentTurnResponseStepCompletePayload(
                    step_type=StepType.tool_execution.value,
                    step_id=step_id,
                    step_details=tool_execution_step,
                )
            )
        )


class ActionData(BaseModel):
    thought: str
    action: str
    action_input: str
    observation: str


def convert_messages(ls_messages: List[UserMessage]) -> List[str]:
    """
    Converts messages from the format used in lllama-stack to the format used in crewai.

    Parameters:
        ls_messages (List[UserMessage]): A list of user messages in llama-stack format.

    Returns:
        List[HumanMessage]: A list of human messages in langgraph format.
    """

    if not ls_messages:
        return []

    return [{"prompt": message.content} for message in ls_messages]
