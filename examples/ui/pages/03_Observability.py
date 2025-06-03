# Copyright 2025 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
