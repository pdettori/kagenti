import streamlit as st

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
    st.title("Welcome to the Cloud Native Agent Platform")

with col2:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# --- Home Page Content ---
st.write("This is the main dashboard for managing your AI agents and tools.")
st.write("Use the sidebar on the left to navigate between the main sections:")
st.write("- **Agent Catalog**: Browse and manage your AI agents.")
st.write("- **Tool Catalog**: Explore and manage the tools available to your agents.")
st.write("- **Observability**: Monitor the performance and activities of your agents and tools.")


