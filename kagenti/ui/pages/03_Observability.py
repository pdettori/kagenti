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

"""
User interface for Observability page.
"""

import os
import streamlit as st
from lib.common_ui import check_auth
from lib import constants  # For URLs

# --- Page Configuration (Optional) ---
# st.set_page_config(page_title="Observability", layout="wide")

check_auth()

traces_dashboard_url = os.environ.get(
    "TRACES_DASHBOARD_URL", constants.TRACES_DASHBOARD_URL
)
network_traffic_dashboard_url = os.environ.get(
    "NETWORK_TRAFFIC_DASHBOARD_URL", constants.NETWORK_TRAFFIC_DASHBOARD_URL
)

# --- Main Page Content ---
st.header("🔭 Observability Dashboard")
st.write(
    "Access various dashboards to monitor the health, performance, traces, "
    "and network traffic of your deployed agents and tools."
)
st.markdown("---")

st.subheader("Tracing & Performance Monitoring")
st.link_button(
    "Go to Traces Dashboard (Phoenix/OpenTelemetry)",
    url=traces_dashboard_url,
    help="Click to open the application traces dashboard in a new tab. Useful for debugging and performance analysis.",
    use_container_width=True,
)
st.caption(f"Access detailed trace data at: `{traces_dashboard_url}`")

st.markdown("---")

st.subheader("Network Traffic & Service Mesh")
st.link_button(
    "Go to Network Traffic Dashboard (Kiali/Istio)",
    url=network_traffic_dashboard_url,
    help="Click to open the network traffic and service mesh visualization dashboard in a new tab.",
    use_container_width=True,
)
st.caption(f"Visualize service interactions at: `{network_traffic_dashboard_url}`")

st.markdown("---")
st.info(
    "**Note:** Ensure that the observability tools (like Phoenix for traces and Kiali for service mesh) "
    "are properly configured and accessible from your environment."
)
