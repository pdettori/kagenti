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
from llama_stack_client.types.agents.turn_create_params import Document
from termcolor import colored


def run_main(host: str, port: int, disable_safety: bool = False):
    urls = [
        "README.md",
    ]

    attachments = [
        Document(
            content=f"https://raw.githubusercontent.com/ibm-granite/granite-code-models/refs/heads/main/{url}",
            mime_type="text/plain",
        )
        for i, url in enumerate(urls)
    ]

    client = LlamaStackClient(
        base_url=f"http://{host}:{port}",
    )

    available_shields = [shield.identifier for shield in client.shields.list()]
    if not available_shields:
        print(colored("No available shields. Disabling safety.", "yellow"))
    else:
        print(f"Available shields found: {available_shields}")

    available_models = [
        model.identifier for model in client.models.list() if model.model_type == "llm"
    ]
    if not available_models:
        print(colored("No available models. Exiting.", "red"))
        return

    selected_model = available_models[0]
    print(f"Using model: {selected_model}")

    agent_config = AgentConfig(
        model=selected_model,
        instructions="You are a helpful assistant. Always respond based on the document provided. If you do not know the answer, just say so.",
        sampling_params={
            "strategy": {"type": "top_p", "temperature": 1.0, "top_p": 0.9},
        },
        toolgroups=["builtin::rag"],
        tool_choice="auto",
        input_shields=available_shields if available_shields else [],
        output_shields=available_shields if available_shields else [],
        enable_session_persistence=True,
    )

    agent = Agent(client, agent_config)
    session_id = agent.create_session("test-session")
    print(f"Created session_id={session_id} for Agent({agent.agent_id})")

    user_prompts = [
        (
            "What is Granite? Give a very short summary.",
            attachments,
        ),
    ]

    for prompt in user_prompts:
        response = agent.create_turn(
            messages=[
                {
                    "role": "user",
                    "content": prompt[0],
                }
            ],
            documents=prompt[1],
            session_id=session_id,
        )

        for log in EventLogger().log(response):
            log.print()


def main(host: str, port: int):
    run_main(host, port)


if __name__ == "__main__":
    fire.Fire(main)
