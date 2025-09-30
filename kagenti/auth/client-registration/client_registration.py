"""
client_registration.py

Registers a Keycloak client and stores its secret in a file.
Idempotent:
- Creates the client if it does not exist.
- If the client already exists, reuses it.
- Always retrieves and stores the client secret.
"""

import os
from keycloak import KeycloakAdmin, KeycloakPostError


def get_env_var(name: str) -> str:
    """Fetch an environment variable or raise ValueError if missing."""
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value

def register_client(
    keycloak_url: str,
    keycloak_realm: str,
    keycloak_admin_username: str,
    keycloak_admin_password: str,
    client_name: str,
    client_id: str,
    namespace: str,
    secret_file: str = "/shared/secret.txt",
):
    print(f"Connecting to Keycloak server: {keycloak_url} (realm={keycloak_realm})")
    keycloak_admin = KeycloakAdmin(
        server_url=keycloak_url,
        username=keycloak_admin_username,
        password=keycloak_admin_password,
        realm_name=keycloak_realm,
        user_realm_name='master'
    )

    # Ensure client exists
    internal_client_id = keycloak_admin.get_client_id(client_name)
    if internal_client_id:
        print(f'Client "{client_name}" already exists with ID: {internal_client_id}')
    else:
        try:
            internal_client_id = keycloak_admin.create_client(
                {
                    "name": client_name,
                    "clientId": client_id,
                    "standardFlowEnabled": True,
                    "directAccessGrantsEnabled": True,
                    "fullScopeAllowed": False,
                    "publicClient": False # Enable client authentication
                }
            )

            print(f'Created Keycloak client "{client_id}": {internal_client_id}')
        except KeycloakPostError as e:
            print(f'Could not create Keycloak client "{client_id}": {e}')

    # Always try to get the secret
    try:
        internal_client_id = keycloak_admin.get_client_id(f"{client_id}")
        print(f'Retrieving client_id for client "{client_id}", id: {internal_client_id}.')
        secret = keycloak_admin.get_client_secrets(internal_client_id)["value"]
        print(f'Successfully retrieved secret for client "{client_name}".')
    except KeycloakPostError as e:
        print(f"Could not retrieve secret for client '{client_name}': {e}")
        return

    # Write secret to file
    try:
        with open(secret_file, "w") as f:
            f.write(secret)
        print(f'Secret written to file: "{secret_file}"')
    except OSError as ioe:
        print(f'Error writing secret to file: {ioe}')

register_client(
    keycloak_url=get_env_var("KEYCLOAK_URL"),
    keycloak_realm=get_env_var("KEYCLOAK_REALM"),
    keycloak_admin_username=get_env_var("KEYCLOAK_ADMIN_USERNAME"),
    keycloak_admin_password=get_env_var("KEYCLOAK_ADMIN_PASSWORD"),
    client_name=get_env_var("CLIENT_NAME"),
    client_id=get_env_var("CLIENT_ID"),
    namespace=get_env_var("NAMESPACE"),
)
