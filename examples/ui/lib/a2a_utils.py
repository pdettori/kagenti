import asyncio
import httpx
from a2a.client import A2ACardResolver
from a2a.types import AgentCard, AgentCapabilities, AgentSkill, AgentProvider

async def get_and_print_agent_card(st, base_url):
    """
    Retrieves the agent card using the A2A client SDK and prints its data structure.
    """
    #base_url = "http://a2a-currency-agent.localtest.me:8080" 
    agent_card_path = "/.well-known/agent.json" 

    async with httpx.AsyncClient() as httpx_client:
        try:
            # Initialize the A2ACardResolver to fetch the agent card
            # The resolver requires an async HTTP client instance and the base URL
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=base_url,
                agent_card_path=agent_card_path
            )

            print(f"Attempting to fetch agent card from: {base_url}{agent_card_path}\n")

            agent_card: AgentCard = await resolver.get_agent_card()

            print("Successfully retrieved Agent Card. Details:\n")

            st.markdown(f"  **Name**: {agent_card.name}")
            st.markdown(f"  **Version**: {agent_card.version}")
            st.markdown(f"  **URL**: {agent_card.url}")
            st.markdown(f"  **Description**: {agent_card.description}")

            if agent_card.documentationUrl:
                st.markdown(f"  **Documentation URL**: {agent_card.documentationUrl}")

            if agent_card.capabilities:
                st.markdown("\n  **Capabilities**:")
                caps: AgentCapabilities = agent_card.capabilities
                if caps.streaming is not None:
                    st.markdown(f"    - Streaming Supported: {caps.streaming}")
                if caps.pushNotifications is not None:
                    st.markdown(f"    - Push Notifications Supported: {caps.pushNotifications}")
                if caps.stateTransitionHistory is not None:
                    st.markdown(f"    - State Transition History Supported: {caps.stateTransitionHistory}")
            else:
                st.markdown("\n  **Capabilities**: None specified")

            if agent_card.defaultInputModes:
                st.markdown(f"\n  **Default Input Modes**: {', '.join(agent_card.defaultInputModes)}")
            if agent_card.defaultOutputModes:
                st.markdown(f"  **Default Output Modes**: {', '.join(agent_card.defaultOutputModes)}")

            if agent_card.skills:
                st.markdown("\n  **Skills**:")
                for skill in agent_card.skills:
                    skill_obj: AgentSkill = skill
                    st.markdown(f"    - ID: {skill_obj.id}")
                    st.markdown(f"      Name: {skill_obj.name}")
                    st.markdown(f"      Description: {skill_obj.description}")
                    if skill_obj.tags:
                        st.markdown(f"      Tags: {', '.join(skill_obj.tags)}")
                    if skill_obj.examples:
                        st.markdown(f"      Examples: {', '.join(skill_obj.examples)}")
                    if skill_obj.inputModes:
                        st.markdown(f"      Input Modes: {', '.join(skill_obj.inputModes)}")
                    if skill_obj.outputModes:
                        st.markdown(f"      Output Modes: {', '.join(skill_obj.outputModes)}")
            else:
                st.markdown("\n  **Skills**: None specified [11, 14]")

            if agent_card.provider:
                provider_obj: AgentProvider = agent_card.provider
                st.markdown("\n  **Provider Information**:")
                st.markdown(f"    - Organization: {provider_obj.organization}")
                st.markdown(f"    - URL: {provider_obj.url} [16, 20]")

            if agent_card.security:
                st.markdown(f"\n  **Security Requirements**: {agent_card.security}")
            if agent_card.securitySchemes:
                st.markdown(f"  **Security Scheme Details**: {agent_card.securitySchemes}")

            st.markdown(f"\n  **Supports Authenticated Extended Card**: {agent_card.supportsAuthenticatedExtendedCard}")

        except httpx.HTTPStatusError as e:
            st.markdown(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            st.markdown(f"Failed to fetch agent card from {e.request.url}")
        except httpx.RequestError as e:
            st.markdown(f"Network Error: Could not connect to {base_url}. Error: {e}")
        except Exception as e:
            # Catches other potential errors, such as JSON decoding issues or validation errors 
            st.markdown(f"An unexpected error occurred: {e}")

# if __name__ == "__main__":
#     asyncio.run(get_and_print_agent_card())