import streamlit as st

KEYCLOAK_CONSOLE_URL = "http://keycloak.localtest.me:8080/admin/master/console/" 

st.header("Authorization and Authentication")
st.write("Welcome to the Authorization and Authentication page. Click on the button below to access the  Identity Management Console.")
st.markdown("---")

st.link_button(
    "Go to Identity Management Console",
    url=KEYCLOAK_CONSOLE_URL,
    help="Click to open the Identity Management in a new tab."
)

st.markdown("---")

