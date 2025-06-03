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

