# Snowflake Deployment Checklist (Snowpark Container Services)

## 1. Preflight
- Ensure code is at a tagged release commit.
- Confirm Alembic head is current: `alembic current`.
- Back up production DB before cutover.
- Set production env vars and secrets (do not hardcode in files).

## 2. Local one-command run (sanity)
- Copy env template: `cp .env.example .env`
- Start services: `docker compose up --build -d`
- Verify API: `http://127.0.0.1:8000/docs`
- Verify UI: `http://127.0.0.1:8501`

## 3. Snowflake infrastructure
Create warehouse/database/schema/role/user (example):
```sql
CREATE WAREHOUSE IF NOT EXISTS PROPIFY_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

CREATE DATABASE IF NOT EXISTS PROPIFY_DB;
CREATE SCHEMA IF NOT EXISTS PROPIFY_DB.APP;

CREATE ROLE IF NOT EXISTS PROPIFY_APP_ROLE;
GRANT USAGE ON WAREHOUSE PROPIFY_WH TO ROLE PROPIFY_APP_ROLE;
GRANT USAGE ON DATABASE PROPIFY_DB TO ROLE PROPIFY_APP_ROLE;
GRANT USAGE, CREATE TABLE, CREATE VIEW, CREATE STAGE ON SCHEMA PROPIFY_DB.APP TO ROLE PROPIFY_APP_ROLE;
```

## 4. Configure application DB URL
Set `PROPIFY_DATABASE_URL` for runtime and migrations:
```bash
export PROPIFY_DATABASE_URL='snowflake://<user>:<password>@<account>/<database>/<schema>?warehouse=<warehouse>&role=<role>'
```

## 5. Apply migrations on Snowflake
```bash
alembic upgrade head
alembic current
```

## 6. Optional data migration from SQLite
```bash
export SQLITE_URL='sqlite:///./rental.db'
export SNOWFLAKE_URL="$PROPIFY_DATABASE_URL"
python scripts/migrate_sqlite_to_snowflake.py
```

## 7. Build images
```bash
docker build -f Dockerfile.api -t propify-api:release .
docker build -f Dockerfile.streamlit -t propify-ui:release .
```

## 8. Snowpark Container Services rollout (high-level)
- Push images to Snowflake image registry.
- Create/choose a compute pool.
- Create API service with env var `PROPIFY_DATABASE_URL`.
- Create UI service with env var `PROPIFY_API_URL` pointing to API service endpoint.
- Configure ingress and TLS.

## 9. Post-deploy validation
- API health and OpenAPI reachable.
- Owner login/setup flow works.
- CRUD for properties/units/tenants/leases/payments works.
- File uploads/downloads work.
- Maintenance pending approval flow works.

## 10. Operational guardrails
- Enable monitoring/alerting on service failures and latency.
- Rotate credentials and move secrets to Snowflake-managed secret storage.
- Keep rollback plan: prior image tags + DB backup + migration rollback plan.
