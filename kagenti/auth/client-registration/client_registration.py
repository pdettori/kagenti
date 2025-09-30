import os
from keycloak import KeycloakAdmin, KeycloakPostError

KEYCLOAK_URL = os.environ.get('KEYCLOAK_URL')
KEYCLOAK_REALM = os.environ.get('KEYCLOAK_REALM')
KEYCLOAK_ADMIN_USERNAME = os.environ.get('KEYCLOAK_ADMIN_USERNAME')
KEYCLOAK_ADMIN_PASSWORD = os.environ.get('KEYCLOAK_ADMIN_PASSWORD')
CLIENT_NAME = os.environ.get('CLIENT_NAME')
CLIENT_ID = os.environ.get('CLIENT_ID')
NAMESPACE = os.environ.get('NAMESPACE')

secret_file = "secret.txt"

def register_client(
    keycloak_url: str,
    keycloak_realm: str,
    keycloak_admin_username: str,
    keycloak_admin_password: str,
    client_name: str,
    client_id: str,
    namespace: str
):
    # clientId = f'{namespace}/{client_name}'

    if keycloak_url is None:
        print(f'Expected environment variable "KEYCLOAK_URL". Skipping client registration of {client_id}.')
        return
    if keycloak_realm is None:
        raise Exception('Expected environment variable "KEYCLOAK_REALM"')
    if keycloak_admin_username is None:
        raise Exception('Expected environment variable "KEYCLOAK_ADMIN_USERNAME"')
    if keycloak_admin_password is None:
        raise Exception('Expected environment variable "KEYCLOAK_ADMIN_PASSWORD"')
    if client_name is None:
        raise Exception('Expected environment variable "CLIENT_NAME"')
    if client_id is None:
        raise Exception('Expected environment variable "CLIENT_ID"')
    if namespace is None:
        raise Exception('Expected environment variable "NAMESPACE"')

    keycloak_admin = KeycloakAdmin(
        server_url=keycloak_url,
        username=keycloak_admin_username,
        password=keycloak_admin_password,
        realm_name=keycloak_realm,
        user_realm_name='master'
    )

    # Create client
    try:
        internal_client_id = keycloak_admin.create_client(
            {
                "name": client_name,
                "clientId": client_id,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "fullScopeAllowed": False,
                "publicClient": True # Disable client authentication
            }
        )

        print(f'Created Keycloak client "{client_id}": {internal_client_id}')
    except KeycloakPostError as e:
        print(f'Could not create Keycloak client "{client_id}": {e}')

    # Always try to get the secret
    try:
        info = keycloak_admin.get_server_info()
        # print(f'Server info: {info}')
        clients = keycloak_admin.get_clients()
        client_ids = [client['clientId'] for client in clients]
        print(client_ids)
        
        cl_id = keycloak_admin.get_client_id("{client_name}")
        print(f'Retrieving client_id for client "{client_name}", id: {cl_id}.')
        secret = keycloak_admin.get_client_secrets(cl_id)["value"]
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
    KEYCLOAK_URL,
    KEYCLOAK_REALM,
    KEYCLOAK_ADMIN_USERNAME,
    KEYCLOAK_ADMIN_PASSWORD,
    CLIENT_NAME,
    CLIENT_ID,
    NAMESPACE
)
