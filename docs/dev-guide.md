# Developer's Guide

## Kagenti UI Development

### Running locally

To run the UI locally, ensure you have Python version 3.12 or above installed. 
If Kagenti is not already running, execute the installer to set up Kagenti first. 
Follow these steps to run the UI:

1. Navigate to the kagenti/ui directory:

    ```shell
    cd kagenti/ui
    ```

2. Launch the UI using the following Streamlit command:

    ```shell
    uv run streamlit run Home.py
    ```

Access the UI in your browser at `http://localhost:8501`.

Note: Running locally allows you to explore various UI features except for connecting to an agent or tool, which requires exposing them via an HTTPRoute.

Example: Connecting to `a2a-currency-converter`

To test connectivity with the `a2a-currency-converter` agent within 
the team1 namespace, apply the following HTTPRoute configuration:

```shell
kubectl apply -n team1 -f - <<EOF
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: a2a-currency-converter
  labels:
    app: a2a-currency-converter
spec:
  parentRefs:
    - name: http
      namespace: kagenti-system
  hostnames:
    - "a2a-currency-converter.localtest.me"
  rules:
    - backendRefs:
        - name: a2a-currency-converter 
          port: 8000 
EOF
```

### Running Your Image in Kubernetes

Before proceeding, ensure there is an existing Kagenti instance 
running. To test your build on Kubernetes, execute the following script:

```shell
scripts/ui-dev-build.sh
```

Script Details:

- Builds the image locally.
- The image is loaded into Kind.
- The script replaces the image in the kagenti-ui pod with the newly built image.

Once complete, access the UI at http://kagenti-ui.localtest.me:8080.

