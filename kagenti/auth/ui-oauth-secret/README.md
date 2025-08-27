# `kagenti-ui-oauth-secret`

`kagenti-ui-oauth-secret` is the image that creates a Keycloak client for Kagenti, gets the client secret, then creates a Kubernetes secret name `kagenti-ui-oauth-secret` that contains the client secret.

This `kagenti-ui-oauth-secret` secret is then read by the `kagenti-ui`, which allows the UI to talk to Keycloak.