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

# --- Page Configuration ---
st.set_page_config(
    page_title="Cloud Native Agent Platform",
    layout="wide",
    initial_sidebar_state="expanded",  # Keep sidebar expanded for multi-page nav
    menu_items={
        "Get Help": "https://kagenti.github.io/.github/",
        "Report a bug": "https://github.com/kagenti/kagenti/issues",
        "About": "# Cloud Native Agent Platform\nYour one-stop solution for deployng and managing AI agents and tools.",
    },
)

# --- Custom CSS for Styling ---
st.markdown(
    """
    <style>
    /* Main container padding */
    .block-container { /* More specific selector if needed */
        padding-top: 2rem !important;
        padding-right: 2rem !important;
        padding-left: 2rem !important;
        padding-bottom: 2rem !important;
    }

    /* Example: Style for selectbox if it were used in a header */
    /* This was in the original CSS, targeting a generic div.stSelectbox.
       If a specific selectbox needs styling, give it a class or use more specific selectors.
    div.stSelectbox {
        margin-left: auto; /* Pushes selectbox to the right if in a flex container */
        margin-right: 0;
    }
    */

    /* Hide the default Streamlit pages label in sidebar if desired (original commented out) */
    /*
    .stSidebar .st-emotion-cache-1f1n4fj.e1fqkh3o1 {
        visibility: hidden;
        height: 0;
    }
    */
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Header ---
st.title("🚀 Welcome to the Cloud Native Agent Platform")
st.caption("Manage, deploy, and observe your AI agents and tools with ease.")
st.markdown("---")


# --- Home Page Content ---
st.subheader("Overview")
st.write(
    "This dashboard supports the deployment, management and observability of agents and tools on the Kagenti platform. "
    "Navigate through the sections using the sidebar to explore different functionalities."
)

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        """
        #### Key Sections:
        - **Agent Catalog**: Browse, interact with, and manage your deployed AI agents.
        - **Tool Catalog**: Discover and manage the tools available to your agents.
        - **Import New Agent**: Build and deploy new agents from source repositories.
        - **Import New Tool**: Integrate and deploy new tools for your agents.
        """
    )

with col2:
    st.markdown(
        """
        #### Monitoring & Administration:
        - **Observability**: Access dashboards to monitor the performance, traces, and network traffic of your agents and tools.
        - **Admin**: Manage identity, authorization, and other administrative settings for the platform.
        """
    )

st.markdown("---")
st.info("💡 **Tip:** Use the sidebar on the left to navigate to the desired section.")
