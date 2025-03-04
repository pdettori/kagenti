# Setting up env

assumptions: conda must be installed and a venv was created and activated:

```shell
conda create -n stack python=3.10
conda activate stack
```

Install llama-stack tagged release with:

```shell
uv pip install git+https://github.com/meta-llama/llama-stack.git@v0.1.5.1
```

Update the agent registry with:

```shell
stack/scripts/update-registry.sh
```

Build the ollama template with the command:

```shell
PYTHONPATH=$(pwd) llama stack build --config stack/templates/ollama/build.yaml
```