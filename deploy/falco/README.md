# Falco Runtime Protection

This directory ships the runtime security assets required to deploy Falco or any eBPF-based equivalent without interrupting the running Lunia services.

## Files

- `falco-values.yaml` – Helm values enabling eBPF mode, runtime filtering, and minimal resource impact.
- `falco-rules.yaml` – Additional Falco rules tuned for Python workloads and encrypted swap activity.
- `fallback_branch/legacy-rules.yaml` – The previous rule-set kept for emergency rollbacks.

## Deployment

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm upgrade --install falco falcosecurity/falco \
  --namespace falco --create-namespace \
  -f deploy/falco/falco-values.yaml \
  --set-json extraRules="$(cat deploy/falco/falco-rules.yaml)"
```

The chart automatically loads the AppArmor profile bundled with the container image. No restarts of existing services are required.

## Rollback

To roll back to the legacy behaviour simply replace `falco-rules.yaml` with the content from `fallback_branch/legacy-rules.yaml` and re-run the Helm upgrade command above.
