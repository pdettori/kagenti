# `kagenti-client-registration`

`kagenti-client-registration` is the image that enables Kagenti to automatically register a client (agent or tool) in Keycloak.

# Local development

### Build the image

```sh
cd kagenti/examples/identity/kagenti-client-registration
docker build -t kagenti-client-registration .
```

### Install Kagenti

```sh
cd kagenti/installer
uv run kagenti-installer
```

### Load the image into the cluster

```sh
kind load docker-image kagenti-client-registration --name agent-platform
```

### Import a new agent

Open the Agent Platform Demo Dashboard at [http://kagenti-ui.localtest.me:8080](http://kagenti-ui.localtest.me:8080).

Go to the `Import New Agent` tab on the sidebar.

Select the one of the enabled namespaces - e.g. `team1`.

Select the `a2a/weather-service`.

Select `Build Agent`.

### Verify client registration

Open Keycloak at [http://keycloak.localtest.me:8080](http://keycloak.localtest.me:8080).

The default username and password are `admin`.

Go to `Clients` tab on the sidebar.

After a while, a new client `team1/weather-service` should appear.
