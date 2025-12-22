DEPRECATION NOTICE: `kagenti-installer`
=====================================

The legacy `kagenti-installer` (the uv-based installer located under `kagenti/installer`) is deprecated.

Why
- The Ansible-based Helm installer (`deployments/ansible/run-install.sh`) provides a more flexible, reproducible, and CI-friendly installation path for both local (Kind) and OpenShift environments.

What this means
- New users: use the Ansible-based installer as the default.
- Existing users: migrate to the Ansible-based installer at your convenience; the legacy installer will continue to work for a limited transition period but will be removed in a future release.

Quick migration steps
1. Copy and configure secret values:

```bash
cp deployments/envs/secret_values.yaml.example deployments/envs/.secret_values.yaml
# Edit deployments/envs/.secret_values.yaml with your values
```

2. Run the Ansible-based installer (example for dev environment):

```bash
deployments/ansible/run-install.sh --env dev
```

3. For local Kind clusters: the Ansible installer supports Kind as a target; see `deployments/ansible/README.md` for Rancher Desktop / Kind-specific notes.

If you need to keep using the legacy `kagenti-installer` temporarily:

```bash
# legacy (deprecated):
cd kagenti/installer
uv run kagenti-installer
```

Questions or concerns
- Open an issue or discussion in the repository and tag `area/installer` so the team can help with migration paths or address blockers.

Timeline
- Deprecation begins now; users should migrate as soon as practical. Removal will be announced at least one release in advance.
