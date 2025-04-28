# Design and Implementation for the PoCs

This section provides details on the implementation of the PoCs.

## API Key Propagation to MCP Tool

API Key propagation for MCP does not work out of the box. It requires modifications in the Llama Stack MCP
provider and an opinionated use of the MCP python SDK to pass the `api_key` to the tool function. The following
sequence diagram illustrates the registration flow for a MCP tool and the direct tool invocation via API.

```mermaid
sequenceDiagram
    participant Client
    participant APIRouter as API & Router
    participant TGRoutingTable as ToolGroupsRoutingTable
    participant RegistryDB as Registry DB
    participant MCPToolRuntime as ModelContextProtocolToolRuntimeImpl
    participant MCPServer as MCP Server

    Client->>+APIRouter: Register ToolGroup 
    APIRouter->>+TGRoutingTable: register_tool_group
    TGRoutingTable->>+RegistryDB: register
    deactivate TGRoutingTable
    deactivate RegistryDB
    deactivate APIRouter

    Client->>+APIRouter: Invoke tool with key in provider-data
    APIRouter->>+MCPToolRuntime: invoke_tool
    MCPToolRuntime->>+MCPToolRuntime: Extract key and set in MCP tool call metadata
    MCPToolRuntime->>+MCPServer: Call tool with key in metadata
    deactivate MCPToolRuntime
    deactivate MCPServer
    deactivate APIRouter
```

The following sequence diagram illustrates key propagation for a client starting an agent 
turn and for the agent invoking the MCP tool.  The diagram has been extracted from 
[Llama Stack Documentation](https://llama-stack.readthedocs.io/en/latest/building_applications/agent_execution_loop.html)
and modfied accordingly.


```mermaid
sequenceDiagram
    participant C as Client
    participant E as Executor
    participant M as Memory Bank
    participant L as LLM
    participant T as Tools
    participant S as Safety Shield

    Note over C,S: Agent Turn Start
    C->>S: 1. Submit Prompt with api_key in provider_data
    activate S
    S->>E: Input Safety Check
    deactivate S

    loop Inference Loop
        E->>L: 2.1 Augment with Context
        L-->>E: 2.2 Response (with/without tool calls)

        alt Has Tool Calls
            E->>S: Check Tool Input
            S->>T: 3.1 Call Tool with key in metadata
            T-->>E: 3.2 Tool Response
            E->>L: 4.1 Tool Response
            L-->>E: 4.2 Synthesized Response
        end

        opt Stop Conditions
            Note over E: Break if:
            Note over E: - No tool calls
            Note over E: - Max iterations reached
            Note over E: - Token limit exceeded
        end
    end

    E->>S: Output Safety Check
    S->>C: 5. Final Response
```

The main changes are:

1. In `providers/src/mcp_identity/model_context_protocol.py`
    - enable use of `provider-data` to extract the `api_key` (extend class from `NeedsRequestProviderData`)
    - use `get_request_provider_data()` to get `provider-data` and `api_key`
    - set the `api_key` in the metadata for the `send_request` invoking the tool
2. In the `examples/clients/mcp/tool-util.py` client
    - set the `api_key` in the `provider_data` when initializing the llama stack client.
3. In the MCP server `examples/mcp/sse_server.py`
    - use the [Context](https://github.com/modelcontextprotocol/python-sdk/blob/1691b905e22faa94f45e42ca5dfd87927362be5a/src/mcp/server/fastmcp/server.py#L553) passed to the tool to extract the metadata and the `api_key`.


