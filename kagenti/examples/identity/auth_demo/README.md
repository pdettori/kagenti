# Demo set up

Set up Python environment

```sh
cd kagenti/examples/identity/auth_demo
python -m venv venv
```

Install Python modules

```sh
pip install -r requirements.txt
```

Run Python script

```sh
KEYCLOAK_URL="http://keycloak.localtest.me:8080"
KEYCLOAK_REALM=master
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin
python set_up_demo.py
```