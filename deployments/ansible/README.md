Kagenti Ansible installer
=========================

This directory contains an Ansible playbook and role to install Kagenti components
using the `kubernetes.core` Ansible collection (k8s and helm support).

Key features
- Use a single `values.yaml` to enable/disable components and provide chart values.
- Support secret values via an external `secret_values.yaml` file or environment variables.
- Use `kubernetes.core.helm` to install/upgrade Helm releases and `kubernetes.core.k8s` to manage k8s objects.

Quick start
1. Install the required collection:

   pip install ansible
   pip install PyYAML kubernetes openshift

   ansible-galaxy collection install -r collections-reqs.yml

2. Copy `secret_values.yaml.example` to `secret_values.yaml` and update secrets. Keep it out of VCS.

3. Run the playbook locally:

   export ANSIBLE_PYTHON_INTERPRETER=$(which python)
   
   ansible-playbook -i localhost, -c local installer-playbook.yml -e "secret_values_file=secret_values.yaml"

Notes
- Adjust chart paths in `values.yaml` to point to your charts (they are relative to this directory by default).
- You can override any `values.yaml` entries by passing extra-vars.
