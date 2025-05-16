
![Kagenti](banner.png)

**Kagenti** is a Cloud-native middleware providing a *framework-neutral*, *scalable* and *secure* platform for deploying and orchestrating AI agents through a standardized REST API. It includes key services such as:

- Trusted identity
- Deployment
- Configuration
- Scaling
- Fault-tolerance
- Checkpointing
- Discovery of agents and tools
- Persistence

## Value Proposition

Despite the extensive variety of frameworks available for developing agent-based applications, there is a distinct lack of standardized methods for deploying and operating agent code in production environments, as well as for exposing it through a standardized API. Agents are adept at reasoning, planning, and interacting with various tools, but their full potential can be limited by these deployment challenges. **Kagenti** addresses this gap by enhancing existing agent frameworks with the following key components:

-  **Kubernetes Platform Operator**: Facilitates the deployment and configuration of agents along with infrastructure dependencies on Kubernetes. It enables scaling and updating configurations seamlessly.

-  **Agent and Tool Authorization Pattern**: This pattern replaces static credentials with dynamic SPIRE-managed identities, enforcing least privilege and continuous authentication. Secure token exchanges ensure end-to-end security principles enforcement across agentic workflows.

## Multi-Framework Agents

In the open-source community, several frameworks are emerging for developing agent-based applications. These include **LangGraph**, **CrewAI**, **AG2**, **Llama Stack**, and **BeeAI**. The selection of a specific framework is often driven by the use case requirements. For scenarios requiring complex orchestration with a high degree of control over the agent workflow, frameworks like LangGraph are usually a better fit. They allow explicit graph creation where nodes perform LLM model inference and tool calls, with routing that can be either predefined or dynamically influenced by LLM decisions. On the other hand, frameworks such as CrewAI are designed to assign roles and tasks to agents, enabling them to autonomously work towards achieving predefined goals. Llama Stack agents are primarily pre-built state machines focused on ReAct-style patterns. Users configure the system’s prompts, tools, models, and then simply input data and prompts, allowing the agent to execute without the need for backend code development.

**Kagenti** provides a unified platform to deploy, scale, configure, and orchestrate agents created across these various frameworks by supporting APIs based on emerging standards such as [ACP](https://agentcommunicationprotocol.dev) and [A2A](https://google.github.io/A2A/#/documentation).

## Kubernetes Operator

Deploying agents in production involves addressing typical challenges associated with managing complex microservices-based applications, including managing infrastructure services such as key-value store databases, caches, queuing systems and deployment, configuration management and scaling of API servers, and workers. The Kubernetes operator facilitates the deployment of new framework instances, supports the registration and scaling of multi-framework agents, and assists in setting up and configuring identity management and agents' authorizations.


## Agent and Tool Authorization Pattern

The Agent and Tool Authorization Pattern for the Agentic Platform ensures that both human and machine identities are continuously authenticated and authorized, minimizing implicit trust at every stage of interaction. Traditional static credentials, such as API keys or client secrets, risk privilege escalation and credential leaks, and therefore are replaced with dynamic, short-lived identity-based tokens, managed through SPIRE and integrated with Keycloak for access control.

This approach enforces least privilege access by ensuring that identities — whether users, tools, or external services — only receive the minimum permissions necessary. The authentication and authorization flow follows a structured token exchange mechanism, where a user's identity propagates securely through the system, from initial authentication to tool interactions and external service access. By leveraging SPIFFE/SPIRE for workload identity and OAuth2 transaction tokens for controlled delegation, the platform prevents credential misuse, reduces attack surfaces, and ensures real-time policy enforcement.

In practice, the Authorization Pattern within the Agentic Platform enables:

- Machine Identity Management – replacing static credentials with SPIRE-issued JWTs.
- Secure Delegation – enforcing token exchange to propagate identity across services without excessive permissions.
- Continuous Verification – ensuring authentication and authorization at each step, preventing privilege escalation.

This end-to-end approach aligns agentic workflows with security best practice principles, making them secure, scalable, and eventually production-ready.

## Components

To achieve the objectives outlined above, we are developing this technology through a series of demoes, each targeting specific aspects of our goals. Our aim is to refine these demos into an initial Minimum Viable Product (MVP) architecture.

The demoes are based on the following set of technologies:

- [Llama Stack](https://llama-stack.readthedocs.io), a versatile software stack tailored for building applications that utilize Large Language Models (LLMs), 
- Agent communication protocols such as [A2A](https://google.github.io/A2A) and [ACP](https://agentcommunicationprotocol.dev/introduction/welcome)
- Tools protocols such as [MCP](https://modelcontextprotocol.io)
- [Kagenti Operator](https://github.com/kagenti/kagenti-operator/blob/main/beeai/INSTALL.md) - an operator to build and deploy agents and tools from source and manage lifecycle of agents, tools and platform components.
Cloud Native technologies such as [Kubernetes Gateway API](https://gateway-api.sigs.k8s.io), [Istio Ambient Service Mesh](https://istio.io/latest/docs/ambient/).

### Demos

- [Llama Stack Demos Installation](./docs/demos.md#installation)
- [Llama Stack API Key Propagation](./docs/demos.md#api-key-propagation-from-ls-client-to-mcp-tool-server)
- [Llama Stack Agent as MCP Tool](./docs/demos.md#agent-as-tool)
- [Cloud Native Agent Platform with A2A and ACP multi-framework agents](./docs/cn-demos.md)


