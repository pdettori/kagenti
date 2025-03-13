# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.


from llama_stack_client import LlamaStackClient
from llama_stack_client.lib.agents.agent import Agent
from llama_stack_client.lib.agents.event_logger import EventLogger
from llama_stack_client.types.agent_create_params import AgentConfig
from llama_stack_client.types.agents.turn_create_params import Document
from termcolor import colored
from llama_stack_client.types.shared_params.url import URL
from rich.pretty import pprint
import argparse


def run_main(
    host: str,
    port: int,
    unregister_toolgroup: bool,
    register_toolgroup: bool,
    mcp_endpoint: str,
):

    client = LlamaStackClient(
        base_url=f"http://{host}:{port}",
        provider_data={
            "api_key": "some-api-key",
        },
    )

    # Tool Group ID
    toolgroup_id = "remote::web-fetch"

    # Unregister the MCP Tool Group based on the flag
    if unregister_toolgroup:
        try:
            client.toolgroups.unregister(toolgroup_id=toolgroup_id)
            print(f"Successfully unregistered MCP tool group: {toolgroup_id}")
        except Exception as e:
            print(f"Error unregistering tool group: {e}")
        return    

    # Register the MCP Tool Group based on the flag
    if register_toolgroup:
        try:
            client.toolgroups.register(
                toolgroup_id=toolgroup_id,
                provider_id="model-context-protocol",
                mcp_endpoint=URL(uri=mcp_endpoint),
                args={"metadata": {"key1": "value1", "key2": "value2"}},
            )
            print(f"Successfully registered MCP tool group: {toolgroup_id}")
        except Exception as e:
            print(f"Error registering tool group: {e}")
        return    

    for toolgroup in client.toolgroups.list():
        pprint(toolgroup)

    tools = client.tools.list(toolgroup_id=toolgroup_id)  # List tools in the group
    for tool in tools:
        pprint(tool)

    result = client.tool_runtime.invoke_tool(
        tool_name="fetch",
        kwargs={
            "url": "https://raw.githubusercontent.com/kubestellar/kubeflex/refs/heads/main/docs/contributors.md"
        },
    )
    print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run your script with arguments.')
    
    parser.add_argument('--host', type=str, required=True, help='Specify the host.')
    parser.add_argument('--port', type=int, required=True, help='Specify the port number.')
    parser.add_argument('--unregister_toolgroup', action='store_true', help='Flag to unregister toolgroup.')
    parser.add_argument('--register_toolgroup', action='store_true', help='Flag to register toolgroup.')
    parser.add_argument('--mcp_endpoint', type=str, required=False, default='http://localhost:8000/sse', help='Specify the MCP endpoint.')

    args = parser.parse_args()

    run_main(
        host=args.host,
        port=args.port,
        unregister_toolgroup=args.unregister_toolgroup,
        register_toolgroup=args.register_toolgroup,
        mcp_endpoint=args.mcp_endpoint
    )

