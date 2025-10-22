# Centralised Logging Stack

Vector tails application logs from `/opt/lunia_core/logs` and forwards them to both Elasticsearch/Kibana for real-time analytics and S3 for immutable retention. The stack is optional and should be launched only when `INFRA_PROD_ENABLED=true`.

```bash
INFRA_PROD_ENABLED=true docker compose -f lunia_core/infra/logging/docker-compose.logging.yml up -d
```

Vector uses tenant metadata (if available) and enforces TLS verification for the Elasticsearch sink. Archived payloads are gzipped JSON objects stored in the `LOG_ARCHIVE_BUCKET` bucket.
