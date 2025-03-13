# Proof-Of-Concepts

## Installation

### Prereqs**: 

- Make sure you have Python 3.11+ installed
- Install a [conda-forge](https://conda-forge.org/download/) distribution for your environment 
- Install [ollama](https://ollama.com/download)and ollama must be installed:


###  Setup

Clone this project:

```shell
git clone git@github.ibm.com:aiplatform/k8gentai.git
cd k8gentai
```

On one terminal, run:

```shell
ollama run llama3.2:3b-instruct-fp16 --keepalive 60m
```

On another terminal, run:

```shell
conda create -n stack python=3.10
conda activate stack
```

Install llama-stack tagged release with:

```shell
pip install uv
uv pip install llama-stack==v0.1.6
```

Update the registry with:

```shell
stack/scripts/update-registry.sh
```

Build the ollama template with the command:

```shell
PYTHONPATH=$(pwd) llama stack build --config stack/templates/ollama/build.yaml
```

You are now ready to run the PoCs.

## Multi-Framework Agent Provider

Running this PoC shows how to run Llama Stack and LangGraph Agents fronted by the Llama Stack API.

Run the server with:

```shell
export INFERENCE_MODEL="meta-llama/Llama-3.2-3B-Instruct"
llama stack run stack/templates/ollama/run.yaml 
```

On new terminal, activate env first with `conda activate stack`, then:

### Run Llama Stack Agent

```shell
python -m examples.clients.llama_stack.simple_rag localhost 8321
```

### Run LangGraph Agent

```shell
python -m examples.clients.langgraph.call_math_agent localhost 8321
```

### Run CrewAI Agent

```shell
python -m examples.clients.crewai.call_math_agent localhost 8321
```

## API Key Propagation from LS client to MCP Tool Server

This PoC uses `provider_data` to send data to the MCP
tool_runtime. Details on design and implementation
are described in [this section.](./tech-details.md#api-key-propagation-to-mcp-tool)

Run llama stack server as above. On a new terminal, 
activate env first with `conda activate stack`, then:

Start example MCP server with `web-fetch` tool:

```shell
cd examples/mcp 
uv run sse_server.py
```

On a new terminal, activate env first with `conda activate stack`, 
then run the following command to register the tool group first:

```shell
python -m examples.clients.mcp.tool-util --host localhost --port 8321 --register_toolgroup
```

invoke the tool with:

```shell
python -m examples.clients.mcp.tool-util --host localhost --port 8321
```

verify the log for the MCP server, it should contain a printout like the following:

```console
[03/12/25 21:09:19] INFO     Processing request of type CallToolRequest                                    server.py:534
api_key=some-api-key
```

verify that this is the `api_key` provided in the client looking at the client code:

```shell
cat examples/clients/mcp/tool-util.py 
```


