import streamlit as st

TRACES_DASHBOARD_URL = "http://phoenix.localtest.me:8080" 
NETWORK_TRAFFIC_DASHBOARD_URL = "http://kiali.localtest.me:8080" 

st.header("Observability Dashboard")
st.write("Welcome to the Observability Dashboard. Click on the buttons below to access the Traces or Network Traffic Dashboards.")
st.markdown("---")

st.link_button(
    "Go to Traces Dashboard",
    url=TRACES_DASHBOARD_URL,
    help="Click to open the traces dashboard in a new tab."
)

st.markdown("---")

st.link_button(
    "Go to Network Traffic Dashboard",
    url=NETWORK_TRAFFIC_DASHBOARD_URL,
    help="Click to open the network traffic dashboard in a new tab."
)

st.markdown("---")
