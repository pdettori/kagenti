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

def display_tags(st, tags_dict):
    """
    Displays the word "Tags:" and a dictionary of tags in a single row
    with gray backgrounds.

    Args:
        tags_dict (dict): A dictionary where keys are tag categories
                        and values are tag values.
                        Example: {"framework": "LangGraph", "language": "Python"}
    """
    full_string = "**Tags:** "

    tag_strings = []
    for category, value in tags_dict.items():
        tag_strings.append(f":gray-background[{category}: {value}]")

    full_string += "&nbsp;".join(tag_strings)
    st.markdown(full_string)

def extract_tags(labels)->dict:
    """
    Extract tags from kubernetes labels

    Args:
        labels (dict): a dictionary of labels
    """
    tags = {}
    for key, value in labels.items():
        if key.startswith("kagenti.io/"):
            tag_name = key.replace("kagenti.io/", "")
            tags[tag_name] = value
    return tags

def sanitize_agent_name(agent_name: str) -> str:
    """Sanitizes agent names for use in Python variables and Streamlit keys."""
    return agent_name.replace('-', '_') 