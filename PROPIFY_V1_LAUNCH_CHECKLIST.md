# Propify v1 Launch Checklist

Goal: launch a paid private beta safely within 4 weeks.

How to use:
- Priority tags: `[P0]` blocker for paid launch, `[P1]` important for quality/trust, `[P2]` improve after first customers.
- Status tags: `[ ]` not started, `[-]` in progress, `[x]` done.
- Track one owner per task and add date completed.

## 1) Product Scope Freeze (Week 0)

- [ ] `[P0]` Define v1 ICP and use case (small landlords vs property managers).
- [ ] `[P0]` Freeze v1 feature set (no new features unless revenue critical).
- [ ] `[P0]` Define pricing hypothesis (trial length, monthly tiers, limits).
- [ ] `[P1]` Define success metrics: activation rate, week-4 retention, trial->paid conversion.

Definition of done:
- A one-page v1 scope doc exists in repo and is approved.

## 2) Security and Access (Week 1)

- [ ] `[P0]` Replace UI-only guard with backend auth (JWT/session) for all protected routes.
- [ ] `[P0]` Implement role-based authorization (owner, manager, tenant, contractor).
- [ ] `[P0]` Add tenant isolation checks to all data queries (no cross-tenant access).
- [ ] `[P0]` Store secrets only in environment/secret manager; remove plaintext credentials from scripts/docs.
- [ ] `[P1]` Add password policy and reset flow (token expiry, one-time use).
- [ ] `[P1]` Add account lockout/rate limit for login endpoints.
- [ ] `[P1]` Add upload malware/extension/content-type validation and strict file size caps everywhere.
- [ ] `[P1]` Add structured audit logging for auth events and privileged actions.

Definition of done:
- Security test checklist passes on staging.
- No route that mutates sensitive data is accessible without auth + role checks.

## 3) Reliability and Data Safety (Week 1)

- [ ] `[P0]` Create automated backups with retention policy and encrypted storage.
- [ ] `[P0]` Run one restore drill and document RTO/RPO.
- [ ] `[P0]` Add idempotent migrations policy and migration rollback playbook.
- [ ] `[P1]` Add health checks for API/UI and DB dependency readiness.
- [ ] `[P1]` Add monitoring + alerts (error rate, latency, 5xx, failed jobs).
- [ ] `[P1]` Add centralized logs with correlation IDs.

Definition of done:
- Backup + restore tested successfully.
- Alerting triggers on forced API failure.

## 4) Billing and Monetization (Week 2)

- [ ] `[P0]` Integrate Stripe products/prices and customer portal.
- [ ] `[P0]` Implement subscription lifecycle: trial, active, past_due, canceled.
- [ ] `[P0]` Add webhook processing with signature validation and retry-safe handling.
- [ ] `[P0]` Enforce plan entitlements in backend (not UI only).
- [ ] `[P1]` Add invoices/receipts visibility in owner billing page.
- [ ] `[P1]` Add dunning flow (email reminders before and after payment failure).

Definition of done:
- Test cards cover: new subscription, renewal, failed payment, cancellation.

## 5) Deployment and Operations (Week 2)

- [ ] `[P0]` Choose primary runtime (single cloud + managed DB) and document architecture.
- [ ] `[P0]` Set up production domains: `app.propify.ai`, `api.propify.ai`.
- [ ] `[P0]` Enforce HTTPS/TLS and secure headers.
- [ ] `[P0]` Add CI/CD pipeline (lint, tests, build, deploy gates).
- [ ] `[P1]` Add environment separation (`dev`, `staging`, `prod`) with isolated data.
- [ ] `[P1]` Add release versioning and rollback command.
- [ ] `[P1]` Add synthetic uptime checks for critical flows.

Definition of done:
- A production deploy can be rolled out and rolled back with documented commands.

## 6) Legal and Compliance (Week 3)

- [ ] `[P0]` Publish Terms of Service and Privacy Policy on `propify.ai`.
- [ ] `[P0]` Define data retention/deletion policy and implement account deletion workflow.
- [ ] `[P1]` Create DPA template for business customers.
- [ ] `[P1]` Add consent text and privacy notice in signup flow.
- [ ] `[P1]` Define incident response process with named owners.

Definition of done:
- Legal docs are public and linked in app footer/login.

## 7) Support and Customer Ops (Week 3)

- [ ] `[P0]` Set support channel + SLA (email/helpdesk and response targets).
- [ ] `[P0]` Create onboarding checklist for new customer setup.
- [ ] `[P1]` Create in-app contact/support entry point.
- [ ] `[P1]` Build help center for top 15 workflows.
- [ ] `[P1]` Define bug triage severity and escalation rules.

Definition of done:
- Support can handle first 5 pilot customers without ad hoc process.

## 8) GTM and Pilot Launch (Week 4)

- [ ] `[P0]` Publish simple marketing page with value proposition and pricing CTA.
- [ ] `[P0]` Prepare 10-minute demo script and environment.
- [ ] `[P0]` Recruit 3-5 pilot customers and run onboarding calls.
- [ ] `[P0]` Track pilot KPI dashboard weekly.
- [ ] `[P1]` Capture churn objections and feed top 3 into sprint planning.

Definition of done:
- First paying customer live or at least 3 active pilots using real data.

## 9) Engineering Backlog Seed (Post-v1)

- [ ] `[P2]` OpenAPI/client SDK generation and external API docs.
- [ ] `[P2]` SSO (Google/Microsoft) for owners/managers.
- [ ] `[P2]` Mobile-first tenant portal UX optimization.
- [ ] `[P2]` Advanced analytics dashboard and owner benchmarking.
- [ ] `[P2]` Enterprise self-hosted package offering and licensing model.

## 10) Weekly Execution Cadence

Week 1 (Security + Reliability):
- Close all `[P0]` in sections 2 and 3.
- Exit criteria: staging security checklist green.

Week 2 (Billing + Deploy):
- Close all `[P0]` in sections 4 and 5.
- Exit criteria: trial subscription to paid path validated end-to-end.

Week 3 (Legal + Support):
- Close all `[P0]` in sections 6 and 7.
- Exit criteria: public legal pages + support SLA live.

Week 4 (Pilot Launch):
- Close `[P0]` in section 8.
- Exit criteria: active pilot customers with weekly KPI review.

## 11) Launch Readiness Gate (Must be true)

- [ ] `[P0]` Auth + RBAC + tenant isolation validated.
- [ ] `[P0]` Backups and restore test documented.
- [ ] `[P0]` Billing lifecycle tested with Stripe webhooks.
- [ ] `[P0]` Monitoring/alerts configured and tested.
- [ ] `[P0]` Terms + Privacy published.
- [ ] `[P0]` Incident response and support workflow active.

---
Owner note:
- If any `[P0]` item is open, do not launch paid plans yet.
