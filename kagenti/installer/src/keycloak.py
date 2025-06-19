import time
from keycloak import KeycloakAdmin, KeycloakPostError



class KeycloakSetup:
    def __init__(self, server_url, admin_username, admin_password, realm_name):
        self.server_url = server_url
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.realm_name = realm_name
        self.client_id = ""

    def connect(self, timeout=120, interval=5):
        """
        Initializes the KeycloakAdmin client and verifies the connection.

        This method will poll the Keycloak server until a connection and
        authentication are successful, or until the timeout is reached.

        Args:
            timeout (int): The maximum time in seconds to wait for a connection.
            interval (int): The time in seconds to wait between connection attempts.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        print("Attempting to connect to Keycloak...")
        start_time = time.monotonic()

        while time.monotonic() - start_time < timeout:
            try:
                # Instantiate the client on each attempt for a clean state
                self.keycloak_admin = KeycloakAdmin(
                    server_url=self.server_url,
                    username=self.admin_username,
                    password=self.admin_password,
                    realm_name='master',
                    user_realm_name='master'
                )

                # This API call triggers the actual authentication.
                # If it succeeds, the server is ready.
                self.keycloak_admin.get_server_info()

                print("✅ Successfully connected and authenticated with Keycloak.")
                return True

            except KeycloakPostError as e:
                elapsed_time = int(time.monotonic() - start_time)
                print(
                    f"⏳ Connection failed ({type(e).__name__}). "
                    f"Retrying in {interval}s... ({elapsed_time}s/{timeout}s elapsed)"
                )
                time.sleep(interval)

        print(f"❌ Failed to connect to Keycloak after {timeout} seconds.")
        self.keycloak_admin = None  # Ensure no unusable client object is stored
        return False
    

    def create_realm(self):
        try:
            self.keycloak_admin.create_realm(
                payload={
                    "realm": self.realm_name,
                    "enabled": True
                },
                skip_exists=False
            )
            print(f'Created realm "{self.realm_name}"')
        except Exception as e:
            print(f'error creating realm "{self.realm_name}" - {e}')
        

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
            print(f'Client "{client_name}" already exists. Retrieving its ID.')
            self.client_id = self.keycloak_admin.get_client_id(client_id=client_name)
            print(f'Successfully retrieved ID for existing client "{client_name}".')

    def get_client_secret(self):
        return self.keycloak_admin.get_client_secrets(self.client_id)["value"]

def setup_keycloak() -> str:
    """Setup keycloak and return client secret """
    base_url = "http://keycloak.localtest.me:8080"
    admin_username = "admin"
    admin_password = "admin"
    demo_realm_name = "demo"

    setup = KeycloakSetup(base_url, admin_username, admin_password, demo_realm_name)
    setup.connect()
    setup.create_realm()
    
    test_user_name = "test-user"
    setup.create_user(test_user_name)

    external_tool_client_name = "weather-agent"
    setup.create_client(external_tool_client_name)

    return setup.get_client_secret()
