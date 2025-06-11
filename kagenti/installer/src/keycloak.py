from keycloak import KeycloakAdmin, KeycloakPostError

class KeycloakSetup:
    def __init__(self, server_url, admin_username, admin_password, realm_name):
        self.server_url = server_url
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.realm_name = realm_name
        self.client_id = ""
        self.keycloak_admin = KeycloakAdmin(
            server_url=self.server_url,
            username=self.admin_username,
            password=self.admin_password,
            realm_name=self.realm_name,
            user_realm_name='master'
        )

    def create_realm(self):
        try:
            self.keycloak_admin.create_realm(
                payload={
                    "realm": self.realm_name,
                    "enabled": True
                },
                skip_exists=True
            )
            print(f'Created realm "{self.realm_name}"')
        except KeycloakPostError:
            print(f'Realm "{self.realm_name}" already exists')

    def create_user(self, username):
        try:
            self.keycloak_admin.create_user({
                "username": username,
                "firstName": username,
                "lastName": username,
                "email": f"{username}@test.com",
                "emailVerified": True,
                "enabled": True,
                "credentials": [{"value": "test-password", "type": "password"}]
            })
            print(f'Created user "{username}"')
        except KeycloakPostError:
            print(f'User "{username}" already exists')

    def create_client(self, client_name):
        try:
            self.client_id = self.keycloak_admin.create_client({
                "clientId": client_name,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "fullScopeAllowed": True,
                "enabled": False
            })
            print(f'Created client "{client_name}"')
        except KeycloakPostError:
            # A KeycloakPostError with a 409 Conflict status indicates the client already exists.
            print(f'Client "{client_name}" already exists. Retrieving its ID.')
            # Use get_client_id to fetch the internal ID of the existing client.
            self.client_id = self.keycloak_admin.get_client_id(client_id=client_name)
            print(f'Successfully retrieved ID for existing client "{client_name}".')


    def get_client_secret(self):
        return self.keycloak_admin.get_client_secrets(self.client_id)["value"]

# TODO - get values from env / config file
def setup_keycloak() -> str:
    """Setup keycloak and return client secret """
    base_url = "http://keycloak.localtest.me:8080"
    admin_username = "admin"
    admin_password = "admin"
    demo_realm_name = "demo"

    setup = KeycloakSetup(base_url, admin_username, admin_password, demo_realm_name)
    setup.create_realm()
    
    test_user_name = "test-user"
    setup.create_user(test_user_name)

    external_tool_client_name = "weather-agent"
    setup.create_client(external_tool_client_name)

    return setup.get_client_secret()