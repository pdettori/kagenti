Kagenti Ansible installer
=========================

This directory contains an Ansible playbook and role to install Kagenti components
using the `kubernetes.core` Ansible collection (k8s and helm support).

Key features
- Use a single `values.yaml` to enable/disable components and provide chart values.
- Support secret values via an external `.secret_values.yaml` file or environment variables.
- Use `kubernetes.core.helm` to install/upgrade Helm releases and `kubernetes.core.k8s` to manage k8s objects.

Using uv:

```
uv run ansible-playbook -i localhost, -c local deployments/ansible/installer-playbook.yml -e '{"secret_values_file":"../envs/.secret_values.yaml","global_value_files":["../envs/dev_values.yaml"],"kind_images_preload":false}'
```

Notes on overriding variables from the CLI
- Passing extra-vars via `-e` should override values loaded from `values.yaml`. However, some shells or wrapper scripts (for example the `uv` wrapper) may alter quoting/escaping which can change how the CLI arguments are parsed.
- If an override doesn't seem to take effect, try the JSON/YAML explicit form which is unambiguous to Ansible, for example:

```
# JSON-style explicit extra-vars
uv run ansible-playbook -i localhost, -c local deployments/ansible/installer-playbook.yml -e '{"secret_values_file": ".secret_values.yaml", "kind_images_preload": false}'

# Or without the 'uv' wrapper for a quick test
ansible-playbook -i localhost, -c local deployments/ansible/installer-playbook.yml -e '{"secret_values_file": ".secret_values.yaml", "kind_images_preload": false}'
```

Also: run the playbook with the `--tags debug_vars` option (or omit tags) to show the debug output added to the role which prints resolved variable values. This helps confirm whether the extra-var was received by Ansible.

Quick start
1. Install the required collection:

   pip install ansible
   pip install PyYAML kubernetes openshift

   ansible-galaxy collection install -r collections-reqs.yml

2. Copy `secret_values.yaml.example` to `.secret_values.yaml` and update secrets. Keep it out of VCS.

3. Run the playbook locally:

   export ANSIBLE_PYTHON_INTERPRETER=$(which python)

   ansible-playbook -i localhost, -c local installer-playbook.yml -e "secret_values_file=.secret_values.yaml"

Notes
- Adjust chart paths in `values.yaml` to point to your charts (they are relative to this directory by default).
- You can override any `values.yaml` entries by passing extra-vars.
- Reccomended: install helm diff
  ```
  helm plugin install https://github.com/databus23/helm-diff
  ```


  uv run ansible-playbook -i localhost, -c local deployments/ansible/installer-playbook.yml -e '{"global_value_files":["../envs/dev_values.yaml"],"kind_images_preload":false}'