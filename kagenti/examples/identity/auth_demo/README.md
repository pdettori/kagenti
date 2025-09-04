# Demo set up

This script performs the following steps

1) Create the `slack-partial-access` client scope
2) Assign the `slack-partial-access` realm role to the `slack-partial-access` client scope
3) Set the `slack-partial-access` client scope as the default client scope
4) Create the `slack-full-access` client scope
5) Assign the `slack-full-access` realm role to the `slack-full-access` client scope
6) Set the `slack-full-access` client scope as the default client scope
7) Add the `slack-partial-access` and `slack-full-access` client scopes to the `kagenti` client
8) Create the `slack-partial-access-user` user with a password "password"
9) Assign the `slack-partial-access` realm role to `slack-partial-access-user`
10) Create the `slack-full-access-user` user with a password "password"
11) Assign the `slack-partial-access1 and `slack-full-access` realm roles to `slack-full-access-user`
12) Enable service accounts for the `spiffe://localtest.me/sa/slack-tool` client
13) Assign `view-clients` (master realm) client role to `spiffe://localtest.me/sa/slack-tool` client
14) Set the realm access token lifespan to 10 minutes

### Instructions

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