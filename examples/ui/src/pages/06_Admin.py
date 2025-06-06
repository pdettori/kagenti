# ui/pages/06_Admin.py

import streamlit as st
from lib import constants # For Keycloak URL

# --- Page Configuration (Optional here) ---
# st.set_page_config(page_title="Admin Console", layout="wide")

# --- Main Page Content ---
st.header("🔑 Administration & Identity Management")
st.write(
    "This section provides access to administrative functions, including identity and "
    "access management via the Keycloak console."
)
st.markdown("---")

st.subheader("Identity Management (Keycloak)")
st.write(
    "Manage users, roles, client configurations, and authentication policies "
    "for the Cloud Native Agent Platform."
)

st.link_button(
    "Go to Identity Management Console",
    url=constants.KEYCLOAK_CONSOLE_URL_OFF_CLUSTER,
    help=(
        "Click to open the Keycloak Admin Console in a new tab. "
        "You may need appropriate credentials to log in."
    ),
    use_container_width=True # Makes button wider
)
st.caption(f"Keycloak admin console accessible at: `{constants.KEYCLOAK_CONSOLE_URL_OFF_CLUSTER}`")

st.markdown("---")

# Placeholder for other admin functionalities
st.subheader("Platform Configuration (Placeholder)")
st.info(
    "Future administrative settings related to the platform itself "
    "(e.g., global agent settings, resource quotas) could be managed here."
)
# Example:
# if st.button("Clear Platform Cache (Admin Only)"):
#     # Add appropriate admin checks here
#     st.cache_data.clear()
#     st.cache_resource.clear()
#     st.success("Platform caches cleared.")

st.markdown("---")
st.sidebar.info("Navigate to 'Admin' to manage platform-wide settings and identity.")
