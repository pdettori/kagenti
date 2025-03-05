# Setting up env

assumptions: conda must be installed and a venv was created and activated:

```shell
conda create -n stack python=3.10
conda activate stack
```

Install llama-stack tagged release with:

```shell
pip install uv
uv pip install llama-stack==v0.1.4
```

Update the agent registry with:

```shell
stack/scripts/update-registry.sh
```

Build the ollama template with the command:

```shell
PYTHONPATH=$(pwd) llama stack build --config stack/templates/ollama/build.yaml
```

Run the server with:

```shell
export INFERENCE_MODEL="meta-llama/Llama-3.2-3B-Instruct"
llama stack run stack/templates/ollama/run.yaml 
```

## Testing

On new terminal, activate env first with `conda activate stack`, them:

### Llama Stack Agent

```shell
python -m examples.clients.llama_stack.simple_rag localhost 8321
```

### LangGraph Agent

```shell
python -m examples.clients.langgraph.call_math_agent localhost 8321
```