# Propify v1 Implementation Board (P0 Tickets)

Purpose: convert all `[P0]` launch blockers into implementation-ready tickets.

How to use:
- Status: `[ ]` Not started, `[-]` In progress, `[x]` Done.
- Effort scale: `S` (0.5-1 day), `M` (1-3 days), `L` (3-5 days), `XL` (5+ days).
- Fill `Owner` and `Target Sprint Week` before execution.

## Sprint Week 0: Product Scope and Pricing

### T-001: Define ICP and v1 use case
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `0`
- Task: Decide primary customer segment and top 3 workflows Propify will optimize in v1.
- Deliverables:
  - `docs/product/v1_scope.md`
- Acceptance Criteria:
  - ICP is explicit (for example: landlords with 5-50 units).
  - Top 3 workflows are listed with measurable outcomes.
  - Scope doc approved by founder.

### T-002: Freeze v1 feature scope
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `0`
- Task: Create a frozen in-scope/out-of-scope table to avoid launch delays.
- Deliverables:
  - `docs/product/v1_scope.md`
- Acceptance Criteria:
  - In-scope features map to current code capabilities.
  - Out-of-scope list exists and is enforced for the next 4 weeks.

### T-003: Define pricing hypothesis and trial limits
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `0`
- Task: Specify initial plan names, limits, and trial duration for Stripe setup.
- Deliverables:
  - `docs/product/pricing_hypothesis.md`
- Acceptance Criteria:
  - At least 2 plans + 1 trial model are defined.
  - Each plan includes enforceable entitlements (unit/user limits).

## Sprint Week 1: Security and Reliability

### T-004: Implement backend authentication for protected APIs
- Status: `[ ]`
- Priority: `P0`
- Effort: `L`
- Owner: `TBD`
- Target Sprint Week: `1`
- Task: Add token/session auth in FastAPI and apply dependency checks to protected routers.
- File Targets:
  - `api/main.py`
  - `rental_core/routers/*.py`
  - `rental_core/services/owner_service.py`
  - `rental_core/schemas/owner.py`
  - `requirements.txt` (if auth libs added)
- Acceptance Criteria:
  - Unauthenticated requests to protected endpoints return `401`.
  - Authenticated requests with valid token succeed.
  - Login/logout/session expiration behavior is documented in `docs/security/auth.md`.

### T-005: Implement role-based authorization (RBAC)
- Status: `[ ]`
- Priority: `P0`
- Effort: `M`
- Owner: `TBD`
- Target Sprint Week: `1`
- Task: Enforce route-level role checks for `owner`, `manager`, `tenant`, `contractor`.
- File Targets:
  - `rental_core/routers/*.py`
  - `rental_core/services/*.py`
  - `rental_core/models/owner.py` (role fields if required)
- Acceptance Criteria:
  - Unauthorized role gets `403`.
  - At least one automated test per role-sensitive endpoint category.
  - RBAC matrix documented in `docs/security/rbac_matrix.md`.

### T-006: Add tenant isolation guarantees in data layer
- Status: `[ ]`
- Priority: `P0`
- Effort: `L`
- Owner: `TBD`
- Target Sprint Week: `1`
- Task: Enforce organization/owner scoping for all read/write queries.
- File Targets:
  - `rental_core/services/*.py`
  - `rental_core/models/*.py` (tenant/owner linkage if missing)
  - `migrations/versions/*.py` (if schema changes needed)
- Acceptance Criteria:
  - Cross-tenant access attempts return empty/`403`.
  - Data access helper enforces scope consistently.
  - Security regression tests cover property/unit/lease/payment/maintenance paths.

### T-007: Remove plaintext secrets and adopt environment/secret manager pattern
- Status: `[ ]`
- Priority: `P0`
- Effort: `M`
- Owner: `TBD`
- Target Sprint Week: `1`
- Task: Remove hardcoded credentials from scripts/docs and standardize secret loading.
- File Targets:
  - `scripts/migrate_sqlite_to_snowflake.py`
  - `.env.example`
  - `Makefile`
  - `SNOWFLAKE_DEPLOYMENT_CHECKLIST.md`
- Acceptance Criteria:
  - No credentials present in tracked files.
  - Runtime fails fast with clear error when required secret missing.
  - Secrets handling documented in `docs/security/secrets.md`.

### T-008: Automated backup workflow with encryption and retention
- Status: `[ ]`
- Priority: `P0`
- Effort: `M`
- Owner: `TBD`
- Target Sprint Week: `1`
- Task: Add scheduled backup job and retention policy with encrypted storage target.
- File Targets:
  - `infra/` (backup scripts/config)
  - `Makefile` (backup/restore commands)
  - `docs/ops/backups.md`
- Acceptance Criteria:
  - Daily backup job documented and runnable.
  - Retention policy (for example 30 days) is explicit.
  - Backup artifacts are encrypted at rest.

### T-009: Run restore drill and document RTO/RPO
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `1`
- Task: Restore latest backup to staging and measure recovery targets.
- Deliverables:
  - `docs/ops/restore_drill_YYYYMMDD.md`
- Acceptance Criteria:
  - Restore succeeds end-to-end.
  - Actual RTO and RPO values recorded.
  - Gaps and remediation steps listed.

### T-010: Migration policy and rollback playbook
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `1`
- Task: Formalize migration process for staging/prod and rollback decisions.
- File Targets:
  - `docs/ops/migration_playbook.md`
  - `Makefile` (safe migration targets)
- Acceptance Criteria:
  - Playbook includes pre-checks, backup step, migration, verification, rollback path.
  - Team can execute with only the document.

## Sprint Week 2: Billing and Deployment

### T-011: Integrate Stripe products/prices/customer portal
- Status: `[ ]`
- Priority: `P0`
- Effort: `L`
- Owner: `TBD`
- Target Sprint Week: `2`
- Task: Add Stripe integration with plan catalog and billing portal links.
- File Targets:
  - `rental_core/routers/` (new `billing.py`)
  - `rental_core/services/` (new `billing_service.py`)
  - `rental_core/schemas/` (billing payload schemas)
  - `requirements.txt` (`stripe`)
- Acceptance Criteria:
  - User can start trial/subscription via API flow.
  - Billing portal URL is generated for active customer.
  - Stripe keys are env-driven only.

### T-012: Implement subscription lifecycle state model
- Status: `[ ]`
- Priority: `P0`
- Effort: `M`
- Owner: `TBD`
- Target Sprint Week: `2`
- Task: Persist and manage statuses: `trial`, `active`, `past_due`, `canceled`.
- File Targets:
  - `rental_core/models/` (subscription model)
  - `rental_core/services/billing_service.py`
  - `migrations/versions/*.py` (new migration)
- Acceptance Criteria:
  - State transitions match Stripe webhook events.
  - Invalid transitions are rejected and logged.
  - Subscription status is visible to owner profile endpoint.

### T-013: Add secure, idempotent Stripe webhook handling
- Status: `[ ]`
- Priority: `P0`
- Effort: `M`
- Owner: `TBD`
- Target Sprint Week: `2`
- Task: Validate webhook signatures and de-duplicate event processing.
- File Targets:
  - `rental_core/routers/billing.py`
  - `rental_core/services/billing_service.py`
  - `rental_core/models/` (webhook event store)
- Acceptance Criteria:
  - Invalid signatures return `400` and do not mutate state.
  - Replayed event does not cause duplicate state changes.
  - Failed processing is retry-safe.

### T-014: Enforce plan entitlements in backend
- Status: `[ ]`
- Priority: `P0`
- Effort: `M`
- Owner: `TBD`
- Target Sprint Week: `2`
- Task: Enforce plan limits (units, users, features) in API service layer.
- File Targets:
  - `rental_core/services/*.py`
  - `rental_core/routers/*.py`
  - `docs/product/pricing_hypothesis.md`
- Acceptance Criteria:
  - Requests exceeding limits return deterministic `402` or `403` with reason.
  - Entitlement checks are covered by tests.
  - UI receives machine-readable error codes.

### T-015: Decide runtime architecture and document it
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `2`
- Task: Select cloud/runtime and deployment topology for v1.
- Deliverables:
  - `docs/architecture/v1_runtime.md`
- Acceptance Criteria:
  - Architecture diagram + component list exists.
  - Includes network boundaries, secrets source, and backup location.

### T-016: Configure production domains and routing
- Status: `[ ]`
- Priority: `P0`
- Effort: `M`
- Owner: `TBD`
- Target Sprint Week: `2`
- Task: Route `app.propify.ai` to UI and `api.propify.ai` to API.
- File Targets:
  - `infra/` (DNS/ingress config)
  - `docs/ops/deploy.md`
- Acceptance Criteria:
  - Both domains resolve and serve expected app/API.
  - CORS is configured to allow only trusted app origins.

### T-017: Enforce HTTPS/TLS and secure HTTP headers
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `2`
- Task: Redirect HTTP to HTTPS and enforce secure headers.
- File Targets:
  - `api/main.py` (middleware)
  - `infra/` (TLS termination config)
  - `docs/security/http_headers.md`
- Acceptance Criteria:
  - HTTP requests redirect to HTTPS.
  - Headers present: `HSTS`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`.

### T-018: CI/CD pipeline with quality and deploy gates
- Status: `[ ]`
- Priority: `P0`
- Effort: `M`
- Owner: `TBD`
- Target Sprint Week: `2`
- Task: Add CI for lint/tests/build and gated deployment flow.
- File Targets:
  - `.github/workflows/ci.yml`
  - `.github/workflows/deploy.yml`
  - `Makefile`
- Acceptance Criteria:
  - Pull requests fail on lint/test failure.
  - Deploy requires green CI and manual approval for prod.
  - Rollback command documented.

## Sprint Week 3: Legal and Support

### T-019: Publish Terms and Privacy pages
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `3`
- Task: Publish legal pages and link from app/login/footer.
- File Targets:
  - `ui_admin/app.py` (links)
  - `docs/legal/terms.md`
  - `docs/legal/privacy.md`
  - website repo/page (if separate)
- Acceptance Criteria:
  - Public URLs for Terms and Privacy are live.
  - Links appear in login and footer areas.

### T-020: Data retention/deletion policy + account deletion workflow
- Status: `[ ]`
- Priority: `P0`
- Effort: `M`
- Owner: `TBD`
- Target Sprint Week: `3`
- Task: Implement documented deletion process for customer data and account closure.
- File Targets:
  - `rental_core/routers/owner.py`
  - `rental_core/services/owner_service.py`
  - `docs/legal/data_retention_deletion.md`
- Acceptance Criteria:
  - Owner can request account deletion through authenticated flow.
  - Deletion/retention windows documented and enforced.
  - Action is audit logged.

### T-021: Set support channel and SLA
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `3`
- Task: Set customer support contact and define response time by severity.
- Deliverables:
  - `docs/support/sla.md`
  - `docs/support/intake_process.md`
- Acceptance Criteria:
  - Support email/form is published.
  - SLA table includes P1/P2/P3 response targets.

### T-022: Create onboarding checklist for new customers
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `3`
- Task: Standardize first 7-day onboarding journey.
- Deliverables:
  - `docs/support/customer_onboarding_checklist.md`
- Acceptance Criteria:
  - Checklist covers setup, data import, first property/unit/tenant/lease flow.
  - Can be executed by non-engineering operator.

## Sprint Week 4: GTM and Pilot Launch

### T-023: Publish marketing page with value proposition + pricing CTA
- Status: `[ ]`
- Priority: `P0`
- Effort: `M`
- Owner: `TBD`
- Target Sprint Week: `4`
- Task: Launch simple public page for lead capture and demos.
- Deliverables:
  - `docs/gtm/landing_page_copy.md`
  - site implementation (repo/path depends on hosting setup)
- Acceptance Criteria:
  - Live page with clear ICP-specific messaging and pricing CTA.
  - Contact/demo form sends to monitored inbox or CRM.

### T-024: Prepare 10-minute demo script and demo environment
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `4`
- Task: Create repeatable demo flow using realistic sample data.
- Deliverables:
  - `docs/gtm/demo_script_10min.md`
- Acceptance Criteria:
  - Demo can be run end-to-end in under 10 minutes.
  - Covers maintenance + payments + lease workflows.

### T-025: Recruit and onboard 3-5 pilot customers
- Status: `[ ]`
- Priority: `P0`
- Effort: `M`
- Owner: `TBD`
- Target Sprint Week: `4`
- Task: Run outreach and onboarding calls with target ICP.
- Deliverables:
  - `docs/gtm/pilot_pipeline.md`
- Acceptance Criteria:
  - At least 3 pilots actively using product with real data.
  - Pilot feedback captured weekly.

### T-026: Track pilot KPI dashboard weekly
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `4`
- Task: Define and track KPI dashboard for pilot cohort.
- Deliverables:
  - `docs/gtm/pilot_kpi_dashboard.md`
- Acceptance Criteria:
  - Dashboard includes activation, WAU, maintenance completion time, payment collection rate.
  - KPI review cadence set weekly with owners.

## Cross-Cut Release Gate Tickets (Derived from Launch Gate)

### T-027: Run launch readiness review
- Status: `[ ]`
- Priority: `P0`
- Effort: `S`
- Owner: `TBD`
- Target Sprint Week: `4`
- Task: Verify all launch gate criteria and record go/no-go.
- Deliverables:
  - `docs/ops/v1_launch_readiness_review.md`
- Acceptance Criteria:
  - All gate checks are `PASS` or accepted with explicit risk sign-off.
  - Go/no-go decision documented with date and approver.

## Suggested Execution Order (Dependency-Aware)

1. T-001 -> T-002 -> T-003
2. T-004 -> T-005 -> T-006 -> T-007
3. T-008 -> T-009 -> T-010
4. T-011 -> T-012 -> T-013 -> T-014
5. T-015 -> T-016 -> T-017 -> T-018
6. T-019 -> T-020 -> T-021 -> T-022
7. T-023 -> T-024 -> T-025 -> T-026 -> T-027

## Quick Start This Week

- Assign owners for T-004 through T-010.
- Start implementation with T-004 (auth), T-005 (RBAC), T-006 (tenant isolation).
- Do not begin paid pilot onboarding until T-004 through T-010 are complete.
