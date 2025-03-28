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
from typing import Optional
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    # methods will go here

    async def connect_to_server(self, url: str):
        """Connect to an MCP server

        Args:
            url: MCP server URL
        """

        transport = await self.exit_stack.enter_async_context(
            sse_client(url, headers={"Authorization": "Bearer my_token"})
        )
        self.stdio, self.write = transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]
        print(
            "tool details:",
            [[tool.name, tool.description, tool.inputSchema] for tool in tools],
        )

    async def call_tool(self, tool_name, tool_args):
        return await self.session.call_tool(tool_name, tool_args)

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <url>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        params = {
            "url": "https://raw.githubusercontent.com/kubestellar/kubeflex/refs/heads/main/docs/contributors.md"
        }
        response = await client.call_tool("fetch", params)
        print(response)
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())
