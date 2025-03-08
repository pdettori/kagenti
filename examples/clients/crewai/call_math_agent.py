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

import fire
from llama_stack_client import LlamaStackClient
from llama_stack_client.lib.agents.agent import Agent
from llama_stack_client.lib.agents.event_logger import EventLogger
from llama_stack_client.types.agent_create_params import AgentConfig
from llama_stack_client.types.tool_def_param import ToolDefParam
#from termcolor import colored


def run_main(host: str, port: int, disable_safety: bool = False):

    client = LlamaStackClient(
        base_url=f"http://{host}:{port}",
    )

    agent_config = AgentConfig(
        model="ollama/llama3.2:3b-instruct-fp16",
        instructions="You are a helpful assistant",
        client_tools=[
            ToolDefParam(
                name="AgentMetadata",
                metadata={
                    "name": "math_agent",
                    "description": "does math",
                    "framework": "crewai",
                    "impl_class": "examples.agents.crewai.math_agent.MathAgent.getCrew",
                },
            )
        ],
        toolgroups=[],
    )

    agent = Agent(client, agent_config)
    session_id = agent.create_session("test-session")
    print(f"Created session_id={session_id} for Agent({agent.agent_id})")

    user_prompts = [
        ("What is the sum of 10 and 20? Take the sum and multiply it by 3, whst is the final result?"),
        ("What is the product of 3 and 4?")
    ]

    for prompt in user_prompts:
        response = agent.create_turn(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            session_id=session_id,
        )

        for log in EventLogger().log(response):
            log.print()


def main(host: str, port: int):
    run_main(host, port)


if __name__ == "__main__":
    fire.Fire(main)
