import streamlit as st

# Content for the Tool Catalog page should be directly in the file, not in a function.
st.header("Tool Catalog")
st.write("Welcome to the Tool Catalog page. Here you can view and manage your tools.")
st.markdown("---")
st.subheader("Available Tools")
st.write("- **Tool X**: A web search tool capable of fetching real-time information.")
st.write("- **Tool Y**: A code execution tool for running Python scripts in a sandboxed environment.")
st.write("- **Tool Z**: An image generation tool that creates visuals based on text prompts.")
st.markdown("---")
st.info("You can import new tools via the 'Import New Tool' page (accessible from 'Settings' on the Home page).")
