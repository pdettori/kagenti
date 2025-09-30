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
    keycloak_admin: KeycloakAdmin,
    client_name: str,
    client_id: str,
    namespace: str,
) -> str:
    """
    Ensure a Keycloak client exists.
    Returns the internal client ID.
    """
    internal_client_id = keycloak_admin.get_client_id(f"{client_id}")
    if internal_client_id:
        print(f'Client "{client_id}" already exists with ID: {internal_client_id}')
        return internal_client_id

    try:
        client_representation = {
            "name": client_name,
            "clientId": client_id,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": True,
            "fullScopeAllowed": False,
            "publicClient": False,  # Enable client authentication
        }
        internal_client_id = keycloak_admin.create_client(client_representation)
        print(f'Created Keycloak client "{client_id}": {internal_client_id}')
        return internal_client_id
    except KeycloakPostError as e:
        print(f'Could not create client "{client_id}": {e}')
        raise


def get_secret(
    keycloak_admin: KeycloakAdmin,
    internal_client_id: str,
    client_name: str,
    secret_file: str = "secret.txt",
) -> None:
    """
    Retrieve the secret for a Keycloak client and write it to a file.
    """
    try:
        secret = keycloak_admin.get_client_secrets(internal_client_id)["value"]
        print(f'Successfully retrieved secret for client "{client_name}".')
    except KeycloakPostError as e:
        print(f"Could not retrieve secret for client '{client_name}': {e}")
        return

    try:
        with open(secret_file, "w") as f:
            f.write(secret)
        print(f'Secret written to file: "{secret_file}"')
    except OSError as ioe:
        print(f"Error writing secret to file: {ioe}")


keycloak_admin = KeycloakAdmin(
    server_url=get_env_var("KEYCLOAK_URL"),
    username=get_env_var("KEYCLOAK_ADMIN_USERNAME"),
    password=get_env_var("KEYCLOAK_ADMIN_PASSWORD"),
    realm_name=get_env_var("KEYCLOAK_REALM"),
    user_realm_name="master",
)

client_name = get_env_var("CLIENT_NAME")
client_id = get_env_var("CLIENT_ID")
namespace = get_env_var("NAMESPACE")

internal_client_id = register_client(keycloak_admin, client_name, client_id, namespace)
print(f'Client id: "{internal_client_id}"')
get_secret(keycloak_admin, internal_client_id, client_name, secret_file="/shared/secret.txt")
