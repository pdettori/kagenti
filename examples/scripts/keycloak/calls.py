from keycloak import KeycloakOpenID
keycloak_url = "http://keycloak.localtest.me:8080"
client_id = "weather-agent"
realm_name = "demo"
client_secret = "<placeholder>"

user_username = "test-user"
user_password = "test-password"

keycloak_openid = KeycloakOpenID(server_url=keycloak_url,
                                 client_id=client_id,
                                 realm_name=realm_name,
                                 client_secret_key=client_secret)

access_token = keycloak_openid.token(
        username=user_username,
        password=user_password)

print(access_token)