---
name: health-cloud-benefits
description: End-to-end skill for the Salesforce Health Cloud Benefits Verification data model on Databricks. Scaffolds a Lakeflow Connect managed ingestion pipeline for the 10 core and supporting objects, applies Unity Catalog table/column comments, creates governed metric views, then creates a Genie space with starter questions. Use when a user asks to "create health cloud benefits genie template" or "create a benefits verification genie space", to set up Health Cloud benefit ingestion, to ingest member plans / coverage benefits / care benefit verify requests via Salesforce Lakeflow Connect, or to query insurance coverage limits, copays, deductibles, out-of-pocket maximums, and benefit verification data.
---

# Salesforce Health Cloud Benefits Verification — End-to-End

Steps 1–5 stand up ingestion; steps 6–10 build the semantic layer and the Genie space.
Column-level definitions live in [schema-reference.md](schema-reference.md) — read it when
writing comments or filling in metric view expressions.

Each layer carries a different kind of knowledge. Keep them separate:

| Layer | Carries | Built from |
|---|---|---|
| UC table/column comments | what each table and column means | [schema-reference.md](schema-reference.md) |
| Metric view metadata | governed dimensions, measures, formulas, formats | step 8 |
| Example queries | join paths and expected query shapes | step 10 + the examples below |
| Genie instructions | company-wide business context only | supplied by the user, never invented |

## Step 1 — Gather required inputs

Ask the user for anything not already in context:
- **Connection name** — the Salesforce connection to use
- **Pipeline name** — default `health_cloud_benefits`
- **Destination catalog**
- **Destination schema**

Discover connections rather than guessing. Call `connectionList` if available; otherwise use
the CLI:

```bash
databricks connections list
databricks connections get <connection_name>
```

**Never state that a connection exists until a lookup returns it.** If the lookup returns
nothing, say so and offer to create one — note that Salesforce auth is OAuth U2M only, so the
connection must be created in Catalog Explorer through a browser; CLI and bundles cannot
bootstrap it.

## Step 2 — Verify permissions and source objects

1. Confirm write access to the destination:
   `checkPermissions(actionName="CreateTable", securableType="SCHEMA", securableFullName="<catalog>.<schema>")`
2. Create the schema first if it does not exist.
3. Confirm the 10 source objects are actually visible through the connection before saving a
   spec. `CareLimitType` is exposed through the Tooling API in some orgs and may not be
   ingestible — if the dry run in step 4 rejects it, report that plainly and continue with the
   remaining 9 rather than silently dropping it.

## Step 3 — Propose the pipeline spec

Call `setPendingPipelineSpec` with the YAML below, substituting the user's values.

- For Salesforce, `source_schema` is always `objects` and `source_table` is the Salesforce
  object **API name** (PascalCase).
- `destination_table` is set explicitly to **snake_case** so landed tables match the schema
  reference, join graph, and metric views. Without it, Salesforce objects land lowercased and
  concatenated (e.g. `coveragebenefit`).
- `Account` is ingested **once**. Salesforce stores members (person accounts) and payers
  (business accounts) in the same object; separate them downstream on `IsPersonAccount`, never
  by ingesting `Account` twice into the same schema (duplicate destination names are rejected).

```yaml
name: <pipeline_name>
catalog: <destination_catalog>
schema: <destination_schema>
ingestion_definition:
  connection_name: <connection_name>
  objects:
    # ── Core benefit verification objects (6) ──────────────────────
    - table:
        source_schema: objects
        source_table: MemberPlan
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: member_plan
    - table:
        source_schema: objects
        source_table: PurchaserPlan
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: purchaser_plan
    - table:
        source_schema: objects
        source_table: CareBenefitVerifyRequest
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: care_benefit_verify_request
    - table:
        source_schema: objects
        source_table: CoverageBenefit
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: coverage_benefit
    - table:
        source_schema: objects
        source_table: CoverageBenefitItem
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: coverage_benefit_item
    - table:
        source_schema: objects
        source_table: CoverageBenefitItemLimit
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: coverage_benefit_item_limit
    # ── Supporting reference objects (4) ───────────────────────────
    - table:
        source_schema: objects
        source_table: Account
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: account
    - table:
        source_schema: objects
        source_table: CareLimitType
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: care_limit_type
    - table:
        source_schema: objects
        source_table: CodeSet
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: code_set
    - table:
        source_schema: objects
        source_table: Case
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: care_case
```

If the user asks for the pipeline via YAML or Genie Code, author it here — do not redirect them
to the ingestion UI wizard.

## Step 4 — Save and dry-run

1. After the user confirms, call `editIngestionPipeline` to persist the spec.
2. Call `startPipelineDryRun` to validate without ingesting data.
3. Fix any object that the dry run rejects before continuing.

## Step 5 — Run ingestion and verify the landed tables

A dry run lands no data, so the metric views and Genie space below would have nothing to read.
With the user's confirmation, run the pipeline for real, wait for it to finish, then verify.

```bash
databricks pipelines start-update <pipeline-id>
databricks pipelines get-update <pipeline-id> <update-id>   # poll until terminal
```

Confirm every expected table arrived before moving on:

```sql
SHOW TABLES IN <catalog>.<schema>
```

Expect all 10 (or 9 if `care_limit_type` was rejected in step 4). Report anything missing
instead of proceeding as though ingestion succeeded.

## Step 6 — Reconcile landed column names

Salesforce lands **column** names in Salesforce API casing (`Id`, `Name`, `CreatedDate`,
`PrimaryCareCopay`) — the pipeline does not snake_case them. The definitions in
[schema-reference.md](schema-reference.md) are semantic, so map them to the real names before
writing any SQL:

```sql
DESCRIBE TABLE <catalog>.<schema>.coverage_benefit
```

Use the actual names in steps 7 and 8. If a metric view references a column that
`DESCRIBE` didn't return, `CREATE VIEW` fails with "cannot resolve column".

## Step 7 — Apply Unity Catalog comments

UC comments are what Genie and Catalog Explorer read, and they measurably improve Genie's SQL
accuracy. Take the text from [schema-reference.md](schema-reference.md) and run one statement
at a time:

```sql
COMMENT ON TABLE <catalog>.<schema>.coverage_benefit IS
  'Core financial and structural benefits provided to a covered member by a purchaser plan.';

ALTER TABLE <catalog>.<schema>.coverage_benefit ALTER COLUMN IndividualInNetworkDeductibleRemaining
  COMMENT 'Remaining individual preferred (in-network) deductible balance.';
```

Escape single quotes by doubling them (`''`). Verify with `DESCRIBE TABLE EXTENDED`.

## Step 8 — Create metric views

Two views, not one: the financial figures live at the `coverage_benefit` grain while
utilization figures live at the `coverage_benefit_item_limit` grain. One view per grain avoids
fan-out double counting. Requires **DBR 17.2+** for YAML `version: 1.1`; the `format:` blocks
below need **17.3+** — drop them on older runtimes.

### 8a. Cost-sharing metrics

```sql
CREATE OR REPLACE VIEW <catalog>.<schema>.benefits_cost_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: Cost-sharing metrics (copays, deductibles, out-of-pocket) for Health Cloud benefit verification
  source: <catalog>.<schema>.coverage_benefit
  joins:
    - name: member_plan
      source: <catalog>.<schema>.member_plan
      on: source.member_plan_id = member_plan.id
    - name: purchaser_plan
      source: <catalog>.<schema>.purchaser_plan
      on: member_plan.plan_id = purchaser_plan.id
  dimensions:
    - name: Coverage Type
      expr: source.coverage_type
      comment: Medical, Dental, Vision, Home Health, Pharmacy
    - name: Plan Type
      expr: purchaser_plan.plan_type
      comment: PPO, HMO, Medicare, Medicaid, Workers Comp
    - name: Line of Business
      expr: purchaser_plan.line_of_business
    - name: Verification Status
      expr: member_plan.verification_status
    - name: Benefit Period Month
      expr: DATE_TRUNC('MONTH', source.benefit_period_start_date)
      comment: Month the coverage benefit period starts
    - name: Is Active Benefit
      expr: source.is_active
  measures:
    - name: Coverage Benefit Count
      expr: COUNT(1)
    - name: Member Plan Count
      expr: COUNT(DISTINCT source.member_plan_id)
    - name: Avg Primary Care Copay
      expr: AVG(source.primary_care_copay)
      format:
        type: currency
        currency_code: USD
        decimal_places: { type: exact, places: 2 }
    - name: Avg Specialist Copay
      expr: AVG(source.specialist_copay)
      format:
        type: currency
        currency_code: USD
        decimal_places: { type: exact, places: 2 }
    - name: Avg In-Network Coinsurance Pct
      expr: AVG(source.in_network_coinsurance_percentage)
      comment: Average in-network coinsurance percentage across benefits
      format:
        type: percentage
        decimal_places: { type: exact, places: 1 }
    - name: Avg Individual In-Network Deductible Remaining
      expr: AVG(source.individual_in_network_deductible_remaining)
      format:
        type: currency
        currency_code: USD
        decimal_places: { type: exact, places: 2 }
    - name: Total Individual In-Network Deductible Applied
      expr: SUM(source.individual_in_network_deductible_applied)
      format:
        type: currency
        currency_code: USD
        decimal_places: { type: exact, places: 2 }
    - name: Avg Individual In-Network OOP Remaining
      expr: AVG(source.individual_in_network_out_of_pocket_remaining)
      comment: Average remaining in-network individual out-of-pocket headroom
      format:
        type: currency
        currency_code: USD
        decimal_places: { type: exact, places: 2 }
    - name: Total Family In-Network OOP Applied
      expr: SUM(source.family_in_network_out_of_pocket_applied)
      format:
        type: currency
        currency_code: USD
        decimal_places: { type: exact, places: 2 }
$$
```

### 8b. Utilization metrics

```sql
CREATE OR REPLACE VIEW <catalog>.<schema>.benefit_utilization_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: Service utilization and limit metrics for Health Cloud benefit verification
  source: <catalog>.<schema>.coverage_benefit_item_limit
  joins:
    - name: coverage_benefit_item
      source: <catalog>.<schema>.coverage_benefit_item
      on: source.coverage_benefit_item_id = coverage_benefit_item.id
    - name: coverage_benefit
      source: <catalog>.<schema>.coverage_benefit
      on: coverage_benefit_item.coverage_benefit_id = coverage_benefit.id
    - name: member_plan
      source: <catalog>.<schema>.member_plan
      on: coverage_benefit.member_plan_id = member_plan.id
    - name: purchaser_plan
      source: <catalog>.<schema>.purchaser_plan
      on: member_plan.plan_id = purchaser_plan.id
  dimensions:
    - name: Coverage Type
      expr: coverage_benefit.coverage_type
    - name: Plan Type
      expr: purchaser_plan.plan_type
    - name: Service Type
      expr: coverage_benefit_item.service_type
    - name: Network Type
      expr: source.network_type
      comment: In, Out, or NA (in-network, out-of-network, not applicable)
    - name: Coverage Level
      expr: source.coverage_level
      comment: Individual, Family, EmployeeSpouse
    - name: Term Type
      expr: source.term_type
      comment: Calendar Year, Day, Month, Year to Date
  measures:
    - name: Limit Rule Count
      expr: COUNT(1)
    - name: Total Allowed Quantity
      expr: SUM(source.allowed_quantity)
    - name: Total Applied Quantity
      expr: SUM(source.applied_quantity)
    - name: Total Remaining Quantity
      expr: SUM(source.allowed_quantity - source.applied_quantity)
      comment: Allowed minus applied service quantity (headroom left)
    - name: Avg Utilization Rate
      expr: SUM(source.applied_quantity) / NULLIF(SUM(source.allowed_quantity), 0)
      comment: Applied / allowed quantity ratio
      format:
        type: percentage
        decimal_places: { type: exact, places: 1 }
$$
```

Validate each view with a query before moving on. Metric views require `MEASURE()` around
measures and do not support `SELECT *` — see example 2 below for the shape.

## Step 9 — Create the Genie space

Give the space the **two metric views plus the detail tables users actually drill into** — not
every landed table. Duplicate query paths over the same facts create ambiguity and let Genie
aggregate inconsistently. The reference tables (`care_limit_type`, `code_set`, `care_case`) are
lookup/support objects; add them only if the user asks questions that need them.

```
createAsset({
  assetType: "genie",
  name: "Health Cloud Benefits Verification",
  description: "Benefit verification analytics for member plans, coverage benefits, and utilization limits.",
  tableIdentifiers: [
    "<catalog>.<schema>.benefits_cost_metrics",
    "<catalog>.<schema>.benefit_utilization_metrics",
    "<catalog>.<schema>.member_plan",
    "<catalog>.<schema>.purchaser_plan",
    "<catalog>.<schema>.care_benefit_verify_request",
    "<catalog>.<schema>.account"
  ]
})
```

Then navigate to it with the returned `assetId`:

```
openAsset({
  assetType: "genie",
  assetId: "<genie_space_id>",
  assetName: "Health Cloud Benefits Verification",
  navigate: true,
  continueMessage: ""
})
```

**Instructions** on the space are for company-wide business context only — official definitions
(what counts as an "active member" or "verified coverage"), plan-year conventions, source
precedence, privacy rules, approved terminology. Take these from the user; do not invent them,
and keep join logic, table routing, and metric-view selection out of them. Those belong in the
metric view metadata (step 8), the source list above, and the example queries below.

## Step 10 — Add starter questions

Phrase these the way a business user would ask. Don't leak `MEASURE()` syntax or view names
into the question text — Genie resolves those from the metadata.

```
addStarterQuestions({
  questions: [
    { questionText: "What is the average remaining in-network deductible by plan type?", isDeepResearch: true },
    { questionText: "How do average specialist copays compare across plan types?", isDeepResearch: true },
    { questionText: "How many coverage benefits are there by verification status?", isDeepResearch: true },
    { questionText: "What service quantity is still remaining by coverage type for active benefits?", isDeepResearch: true },
    { questionText: "Which service types have the highest utilization rate?", isDeepResearch: true }
  ]
})
```

Register the example queries below as the space's example queries / benchmarks so Genie learns
the join paths from SQL that runs.

---

## Object reference — 10 ingested objects

**Core benefit verification objects (6)** — Salesforce API name → landed table:
`MemberPlan` → `member_plan`, `PurchaserPlan` → `purchaser_plan`,
`CareBenefitVerifyRequest` → `care_benefit_verify_request`, `CoverageBenefit` → `coverage_benefit`,
`CoverageBenefitItem` → `coverage_benefit_item`, `CoverageBenefitItemLimit` → `coverage_benefit_item_limit`

**Supporting reference objects (4)**:
`Account` → `account`, `CareLimitType` → `care_limit_type`, `CodeSet` → `code_set`,
`Case` → `care_case` (renamed to avoid the reserved word `case`)

That's 10 ingested tables covering 11 logical entities, because `account` carries both the
member (person account) and payer (business account) roles.

Column-level definitions: [schema-reference.md](schema-reference.md).

---

## Join paths

`account` is joined twice, under different aliases, for two different roles:

- **member**: `member_plan.member_id = account.id` (where `account.is_person_account = true`)
- **payer**: `member_plan.payer_id = account.id` (the payer organization)

Benefit hierarchy:
`member_plan (id)` → `coverage_benefit (member_plan_id)` → `coverage_benefit_item (coverage_benefit_id)`
→ `coverage_benefit_item_limit (coverage_benefit_item_id)`

Verification requests attach via `care_benefit_verify_request.member_plan_id` and
`.coverage_benefit_id`; plan context via `member_plan.plan_id → purchaser_plan.id`. Lookups:
`coverage_benefit_item_limit.care_limit_type_id → care_limit_type.id`,
`coverage_benefit_item.code_set_service_type_id → code_set.id`,
`care_benefit_verify_request.case_id → care_case.id`.

Active-state filter for detail queries:
`WHERE member_plan.status = 'Active' AND coverage_benefit.is_active = true AND coverage_benefit_item.is_active = true`

---

## Example queries

### Example 1 — Remaining service quantities for a member's plan
```sql
SELECT
    m.name AS member_name,
    payer.name AS payer_name,
    mp.name AS plan_name,
    cbi.name AS service_covered,
    cbil.allowed_quantity,
    cbil.applied_quantity,
    (cbil.allowed_quantity - cbil.applied_quantity) AS remaining_quantity_allowed,
    cbil.term_type
FROM member_plan mp
JOIN account m ON mp.member_id = m.id
LEFT JOIN account payer ON mp.payer_id = payer.id
JOIN coverage_benefit cb ON cb.member_plan_id = mp.id
JOIN coverage_benefit_item cbi ON cbi.coverage_benefit_id = cb.id
JOIN coverage_benefit_item_limit cbil ON cbil.coverage_benefit_item_id = cbi.id
WHERE mp.status = 'Active'
  AND cb.is_active = true
  AND cbi.is_active = true;
```

### Example 2 — Utilization by service and network (metric view)
```sql
SELECT
    `Service Type`,
    `Network Type`,
    MEASURE(`Total Allowed Quantity`) AS allowed_quantity,
    MEASURE(`Total Applied Quantity`) AS applied_quantity,
    MEASURE(`Total Remaining Quantity`) AS remaining_quantity,
    MEASURE(`Avg Utilization Rate`) AS utilization_rate
FROM <catalog>.<schema>.benefit_utilization_metrics
GROUP BY ALL
ORDER BY ALL;
```

### Example 3 — Verification requests pending for a member
```sql
SELECT
    m.name AS member_name,
    mp.name AS plan_name,
    cbvr.name AS request_name,
    cbvr.status,
    cbvr.status_reason,
    cbvr.verification_mode,
    cbvr.request_date
FROM care_benefit_verify_request cbvr
JOIN member_plan mp ON cbvr.member_plan_id = mp.id
JOIN account m ON mp.member_id = m.id
WHERE cbvr.status IN ('Pending', 'Ready for Verification', 'Pending Confirmation')
ORDER BY cbvr.request_date DESC;
```
