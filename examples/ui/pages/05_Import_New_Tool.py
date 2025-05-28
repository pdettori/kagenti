import streamlit as st

# Content for the Import New Tool page
st.header("Import New Tool")
st.write("This page allows you to import new tool definitions. You can paste JSON or Python code here.")
st.text_area(
    "Tool Definition (JSON/Python)",
    height=250,
    placeholder="Paste your tool's JSON or Python code definition here...",
    key="tool_config_input"
)
st.button("Submit Tool Definition", key="submit_tool_btn")
st.markdown("---")
