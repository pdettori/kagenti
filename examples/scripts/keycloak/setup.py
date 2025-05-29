base_url = "http://keycloak.localtest.me:8080"
admin_username = "admin"
admin_password = "admin"
demo_realm_name = "demo"

from keycloak import KeycloakAdmin, KeycloakPostError

keycloak_admin = KeycloakAdmin(
            server_url=base_url,
            username=admin_username,
            password=admin_password,
            realm_name=demo_realm_name,
            user_realm_name='master')

# Create the demo realm
try:
    keycloak_admin.create_realm(
        payload={
            "realm": demo_realm_name,
            "enabled": True
        },
        skip_exists=True
    )

    print(f'Created realm "{demo_realm_name}"')
except KeycloakPostError as e:
    print(f'Realm "{demo_realm_name}" already exists')

test_user_name = "test-user"

# Add test user
try:
    keycloak_admin.create_user({
        "username": test_user_name,
        "firstName": test_user_name,
        "lastName": test_user_name,
        "email": "test@test.com",
        "emailVerified": True,
        "enabled": True,
        "credentials": [{"value": "test-password", "type": "password",}]
    })

    print(f'Created user "{test_user_name}"')
except KeycloakPostError as e:
    print(f'User "{test_user_name}" already exists')

# Create llama-stack client
external_tool_client_name = "weather-agent"
try:
    keycloak_admin.create_client({
        "clientId": external_tool_client_name,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": True,
        "fullScopeAllowed": True,
        "enabled": False,
    })

    print(f'Created client "{external_tool_client_name}"')
except KeycloakPostError as e:
    print(f'Client "{external_tool_client_name}" already exists')