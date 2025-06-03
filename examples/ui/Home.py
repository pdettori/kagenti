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
from streamlit_mermaid import st_mermaid

# --- Page Configuration ---
st.set_page_config(
    page_title="Cloud Native Agent Platform",
    layout="wide",
    initial_sidebar_state="expanded" # Keep sidebar expanded for multi-page nav
)

# --- Session State Initialization ---
# This state is used for the settings pulldown.
if 'settings_selectbox' not in st.session_state:
    st.session_state.settings_selectbox = "Select Option"

# --- Custom CSS for Styling ---
st.markdown(
    """
    <style>
    .reportview-container .main .block-container{
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
    }
    /* Hide the default Streamlit pages label in sidebar if desired */
    /* .stSidebar .st-emotion-cache-1f1n4fj.e1fqkh3o1 {
        visibility: hidden;
        height: 0;
    } */
    /* Adjust text within the selectbox */
    div.stSelectbox {
        margin-left: auto;
        margin-right: 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Header with Application Title and Settings Pulldown ---
col1, col2 = st.columns([4, 1])

with col1:
    st.title("Welcome to the Cloud Native Agent Platform Demo")

with col2:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# --- Home Page Content ---
st.write("This is the main dashboard for managing your AI agents and tools.")
st.write("Use the sidebar on the left to navigate between the main sections:")
st.write("- **Agent Catalog**: Browse and manage your AI agents.")
st.write("- **Tool Catalog**: Explore and manage the tools available to your agents.")
st.write("- **Observability**: Monitor the performance and activities of your agents and tools.")
st.write("- **Import New Agent**: Build and deploy a new agent from source.")
st.write("- **Import New Tool**: Build and deploy a new tool from source.")
st.write("- **Admin**: Manage identity and authorization for agents.")


st.write("**Demo Architecture**")

mermaid_code = """
%%{ init: {"themeVariables": { 'fontFamily': "Arial", 'primaryColor': '#1f77b4', 'edgeLabelBackground':'#ffffff'}} }%%
graph TB

  subgraph Kubernetes
    direction TB
    
    subgraph kagenti-system ["kagenti-system Namespace"]
      IngressGateway["Ingress Gateway"]
    end

    subgraph keycloak ["keycloak Namespace"]
      Keycloak["Identity Management"]
    end

    subgraph default_namespace ["default Namespace"]
      A2ACurrencyAgent(a2a-currency-agent)
      ACPWeatherService(acp-weather-service)
      
      subgraph MCPGetWeather ["MCP Get Weather"]
        direction LR
        Service[mcp-get-weather Tool]
      end

      subgraph Istio_Ambient_Mesh ["Istio Ambient Service Mesh"]
        direction BT
        ZTunnel("ZTunnel")
        Waypoint("Waypoint Egress")
        ZTunnel --> Waypoint
      end

    end
  end
  
  style Kubernetes fill:#f9f9f9,stroke:#333,stroke-width:2px;
  style kagenti-system fill:#f1f3f4,stroke:#888;
  style default_namespace fill:#f1f3f4,stroke:#888;
  style MCPGetWeather fill:#ffffff,stroke:#aaaaaa,stroke-dasharray: 5 5;

  IngressGateway -->|HTTP Routes| A2ACurrencyAgent
  IngressGateway -->|HTTP Routes| ACPWeatherService
  ACPWeatherService --> Service

  A2ACurrencyAgent -.->|Istio Mesh| ZTunnel
  ACPWeatherService -.->|Istio Mesh| ZTunnel
  Service -.->|Istio Mesh| ZTunnel
  ACPWeatherService -.-> Keycloak

  UI --> IngressGateway
"""

st_mermaid(mermaid_code)