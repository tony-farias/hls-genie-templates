---
name: deploy-monday-morning-scintilla
description: Discover Walmart Scintilla Cloud Feeds in a customer Databricks workspace, assess readiness for the Monday Morning retail-intelligence application, create a deployment plan, and deploy the app with SQL, Genie, Foundation Models, and optional Lakebase persistence. Use when asked to recreate, migrate, provision, validate, or deploy the Monday Morning app against customer-licensed Scintilla data.
---

# Deploy Monday Morning on Scintilla

Recreate the Monday Morning retail-intelligence app without assuming that every customer licenses the same Cloud Feeds.

## Workflow

1. Authenticate to the customer workspace with a named Databricks CLI profile.
2. Identify the customer-provided catalog and Scintilla schema. Never guess or create them.
3. Run the read-only inventory:

   ```bash
   python3 scripts/inventory_scintilla.py \
     --profile <profile> \
     --catalog <catalog> \
     --schema <schema> \
     --warehouse-id <warehouse-id> \
     --output /tmp/scintilla-readiness.md
   ```

4. Read `references/cloud-feeds.md`. Compare present feeds with required and optional capabilities. Use column evidence, not table names alone, when a customer feed was renamed.
5. Read `references/architecture.md`. Produce a customer-specific plan covering:
   - source feeds and missing capabilities;
   - curated tables/views and transformations;
   - warehouse, app, Genie spaces, model endpoint and permissions;
   - optional Lakebase, Vector Search and multi-agent supervisor;
   - validation, cost controls and rollback.
6. Present the plan and obtain approval before creating schemas, tables, apps, Genie spaces, endpoints, grants or databases.
7. Deploy in phases:
   - Core: sales, inventory, item/store dimensions and executive dashboard.
   - Expansion: forecasting, e-commerce, OTIF, pricing and returns.
   - AI: page-scoped Genie rooms, grounded questions and optional supervisor.
   - Actions: Lakebase-backed chat/action persistence.
8. Validate row counts, date coverage, join cardinality, dashboard API responses, Genie SQL grounding, permissions and app health.

## Guardrails

- Treat Scintilla data as customer-licensed and supplier-scoped. Do not copy it across customers or metastores.
- Do not synthesize a missing licensed feed and present it as Scintilla. Mark the capability unavailable or propose a clearly labeled substitute.
- Preserve source grain. Aggregate only in curated views/tables and document the grain.
- Prefer service-principal OAuth and resource bindings. Never commit tokens, passwords or customer identifiers.
- Parameterize catalog, schema, warehouse, Genie IDs, model endpoint and Lakebase settings.
- Use least-privilege grants for the app service principal.
- Make destructive replacement or cleanup a separate approved step.

## Application source

The original source is `https://github.com/akash-jaiswal_data/retaildemo`. The known deployed implementation is React/Vite with an Express API. Treat the source as a template: remove environment-specific IDs and regenerate customer resources rather than copying IDs from another workspace.

Use the migration bundle in the source repository when available. If the upstream repository is inaccessible, reconstruct the components described in `references/architecture.md` and preserve the same API contracts.
