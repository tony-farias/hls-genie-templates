---
name: health-cloud-benefits
description: End-to-end skill for the Salesforce Health Cloud Benefits Verification data model on Databricks. Scaffolds a Lakeflow Connect managed ingestion pipeline for the 10 core and supporting objects, applies Unity Catalog table/column comments, creates governed metric views, then creates a Genie space with starter questions. Use when a user asks to "create health cloud benefits genie template" or "create a benefits verification genie space", to set up Health Cloud benefit ingestion, to ingest member plans / coverage benefits / care benefit verify requests via Salesforce Lakeflow Connect, or to query insurance coverage limits, copays, deductibles, out-of-pocket maximums, and benefit verification data.
---

# Salesforce Health Cloud Benefits Verification — End-to-End

Steps 1–5 stand up ingestion; steps 6–10 build the semantic layer and the Genie space.
Column-level definitions are in the **Column reference** section below — use them when
writing comments or filling in metric view expressions.

Each layer carries a different kind of knowledge. Keep them separate:

| Layer | Carries | Built from |
|---|---|---|
| UC table/column comments | what each table and column means | Column reference below |
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
`PrimaryCareCopay`) — the pipeline does not snake_case them. The Column reference definitions
below are semantic, so map them to the real names before writing any SQL:

```sql
DESCRIBE TABLE <catalog>.<schema>.coverage_benefit
```

Use the actual names in steps 7 and 8. If a metric view references a column that
`DESCRIBE` didn't return, `CREATE VIEW` fails with "cannot resolve column". Build a
`DESCRIBE` inventory for every table before applying comments — do not assume the semantic
names in the Column reference exist as-is on the landed table.

## Step 7 — Apply Unity Catalog comments

UC comments are what Genie and Catalog Explorer read, and they measurably improve Genie's SQL
accuracy. Take the text from the Column reference below and run one statement at a time,
**only for columns that `DESCRIBE` confirmed exist**. Skip missing columns and report them —
a single bad `ALTER COLUMN` should not abort the rest:

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

**Join rule:** star joins (direct FK from `source`) may be siblings. Multi-hop joins must be
**nested** under their parent — sibling joins that reference another join by name (e.g.
`on: member_plan.plan_id = purchaser_plan.id` at the top level) are rejected. Nest like a
snowflake schema.

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
      joins:
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
      joins:
        - name: coverage_benefit
          source: <catalog>.<schema>.coverage_benefit
          on: coverage_benefit_item.coverage_benefit_id = coverage_benefit.id
          joins:
            - name: member_plan
              source: <catalog>.<schema>.member_plan
              on: coverage_benefit.member_plan_id = member_plan.id
              joins:
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

If a rename / description / agent-configuration update fails with a transient network error
(e.g. `Failed to update agent configuration`), retry that call. Do not rewind earlier steps —
starter questions and example SQL can succeed even when the rename fails.

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

---

## Column reference

Semantic column definitions for the 10 ingested tables. Salesforce lands the **physical**
columns in API casing (`Id`, `Name`, `PrimaryCareCopay`), so reconcile names with
`DESCRIBE TABLE` before writing SQL (step 6). Use these descriptions as the text for the
`COMMENT ON TABLE` / `ALTER COLUMN ... COMMENT` statements in step 7.

### 1. member_plan
Represents details about the insurance coverage for a member or subscriber.
- `id` (STRING): Unique ID of the Member Plan record (Primary Key).
- `name` (STRING): The name by which the member knows this plan.
- `member_id` (STRING): The ID of the member's record (person account).
- `member_number` (STRING): The member's reference number for this plan.
- `subscriber_id` (STRING): The ID of the primary subscriber's record.
- `relationship_to_subscriber` (STRING): Picklist value mapping the relationship to the subscriber (e.g., 'Self', 'Spouse', 'Child', 'Unknown', 'Other Relationship').
- `plan_id` (STRING): Foreign key lookup pointing to `purchaser_plan.id`.
- `payer_id` (STRING): Foreign key lookup pointing to the payer's Account object record (`account.id`).
- `payer_network_id` (STRING): Foreign key pointing to a healthcare payer network table.
- `group_number` (STRING): The group number or policy number of the primary member.
- `issuer_number` (STRING): Reference number for the issuer of the plan.
- `effective_from` (DATE): The date from which this member plan is effective.
- `effective_to` (DATE): The date on which this member plan ceases to be effective.
- `status` (STRING): Indicates whether the plan is active.
- `verification_status` (STRING): Status of the plan's verification (e.g., 'Active - Verified', 'Rejected', 'Not Checked', 'Unknown', 'Inactive').
- `last_verification` (DATE): The date on which this plan was last verified.
- `primary_secondary_tertiary` (STRING): Picklist string indicating whether this plan is the primary, secondary, or tertiary plan.
- `primary_care_physician` (STRING): The name of the physician providing primary care under this plan.
- `affiliation` (STRING): An affiliation to a government service, such as the army or navy.
- `external_identifier` (STRING): The identifier used to identify the record outside the Salesforce org.
- `notes` (STRING): Notes about this member plan.
- `owner_id` (STRING): The ID of the user who owns this record.
- `source_system` (STRING): The name of the system this plan record came from.
- `source_system_identifier` (STRING): The ID of this plan record on its source system.
- `source_system_modified` (TIMESTAMP): The date/time on which this plan record was last changed on the source system.

### 2. purchaser_plan
Represents the payer plan that a purchaser makes available to its members and members' dependents.
- `id` (STRING): Unique ID of the Purchaser Plan.
- `name` (STRING): The name of this plan.
- `plan_number` (STRING): The plan's reference number.
- `payer` (STRING): Foreign key lookup pointing to the payer's Account object record (`account.id`).
- `plan_status` (STRING): Picklist indicating whether the plan is active.
- `plan_type` (STRING): The type of plan (e.g., 'PPO', 'HMO', 'Medicare', 'Medicaid', 'Workers Comp').
- `line_of_business` (STRING): Category of insurance policy that the plan belongs to (e.g., group health insurance, individual health insurance).
- `sponsor_type` (STRING): The type of sponsor for the plan (e.g., self-sponsored, government-sponsored, company-sponsored).
- `service_type` (STRING): The description of the service type offered by this plan.
- `effective_from` (DATE): The date from which this purchaser plan is effective.
- `effective_to` (DATE): The date on which this purchaser plan ceases to be effective.
- `is_verifiable` (BOOLEAN): Indicates whether a benefits verification can be performed on this plan.
- `notes` (STRING): Notes about this payer.
- `source_system` (STRING): The name of the system this plan record came from.
- `source_system_identifier` (STRING): The ID of this plan record on its source system.
- `source_system_modified` (TIMESTAMP): The date/time on which this plan record was last changed on the source system.

### 3. care_benefit_verify_request
Request for verification of benefits.
- `id` (STRING): Unique ID of the care benefit verification request.
- `name` (STRING): Autonumber identifier name of the request.
- `status` (STRING): Status of the verification request (e.g., 'Acknowledged', 'Completed', 'Error', 'Partial', 'Pending', 'Rejected', 'TimedOut', 'Verified', 'Pending Confirmation', 'Received Confirmation', 'Ready for Verification').
- `status_reason` (STRING): The reason for the specified status of the care benefit verification request.
- `verification_mode` (STRING): Mode of verification used (e.g., 'Electronic', 'Manual').
- `request_date` (TIMESTAMP): Date and time of verification request.
- `requested_by_id` (STRING): Person or organization requesting verification, mapping to a User record.
- `requester_id` (STRING): Polymorphic reference pointing to Account or HealthcareProvider.
- `member_plan_id` (STRING): Mandatory foreign key identifying the member plan that includes the benefit item being verified.
- `coverage_benefit_id` (STRING): Foreign key identifying the set of services covered by the insurance plan.
- `case_id` (STRING): Identifies the associated CRM support Case (`care_case.id`).
- `provider_id` (STRING): Polymorphic key mapping to the provider of the request (Account or HealthcareProvider).
- `payer_id` (STRING): The payer associated with the care benefit verify request (maps to Account).
- `plan_id` (STRING): The purchaser plan from the member plan associated with the care program enrollee.
- `prescriber_id` (STRING): The prescriber associated with the request (maps to HealthcareProvider).
- `authorized_prescription_id` (STRING): Maps to the related MedicationRequest.
- `original_prescription_id` (STRING): Maps to the original MedicationRequest before variations.
- `prescription_medication_id` (STRING): Maps to CodeSetBundle or Medication.
- `benefit_category_code_id` (STRING): Maps to a specific CodeSet for benefit category.
- `priority_code_id` (STRING): Maps to CodeSet for priority status.
- `care_program_id` (STRING): The associated care program.
- `care_program_enrollee_id` (STRING): The associated care program enrollee.
- `related_care_bnft_verify_request_id` (STRING): The original request from which this request was cloned.
- `billable_prd_start_date_time` (TIMESTAMP): The date and time when billable period started.
- `billable_prd_end_date_time` (TIMESTAMP): The date and time when billable period ended.
- `initial_fill_duration` (DOUBLE): The initial fill duration of the authorized prescription.
- `initial_fill_quantity` (DOUBLE): The initial fill quantity of the authorized prescription.
- `request` (STRING): The JSON request body sent to an external system for care benefit verification.
- `response_body` (STRING): Full JSON response or base64 payload from the external system.
- `response_content_type` (STRING): Content type of the response payload (e.g., 'application/json', 'application/pdf').
- `response_length` (INT): The length of the response from the external system.
- `response_name` (STRING): The name of the response from the external system.
- `assigned_to_id` (STRING): The user assigned to the request.

### 4. coverage_benefit
Represents the core financial and structural benefits provided to a covered member by a purchaser's plan.
- `id` (STRING): Unique ID of the coverage benefit.
- `name` (STRING): Name of these coverage benefits.
- `member_id` (STRING): The ID of the member receiving these benefits.
- `member_plan_id` (STRING): The ID of the member plan receiving these benefits.
- `care_benefit_verify_request_id` (STRING): The lookup key to the care benefit verify request associated with this coverage benefit.
- `coverage_type` (STRING): General category of service covered (e.g., 'Medical', 'Dental', 'Vision', 'Home Health', 'Pharmacy').
- `is_active` (BOOLEAN): Specifies whether the coverage benefit is currently in force.
- `benefit_period_start_date` (DATE): First day of the coverage benefit period.
- `benefit_period_end_date` (DATE): Last day of the coverage benefit period.
- `verification_date` (TIMESTAMP): Date on which the benefit was verified.
- `primary_care_copay` (DECIMAL(18,2)): The amount the member contributes towards primary care treatment.
- `specialist_copay` (DECIMAL(18,2)): The amount the member contributes towards specialist consultations.
- `urgent_care_copay` (DECIMAL(18,2)): The amount the member contributes towards urgent care.
- `emergency_department_copay` (DECIMAL(18,2)): The amount the member contributes towards emergency treatment.
- `pharma_copay_amount` (DECIMAL(18,2)): The amount the member contributes towards pharma products.
- `in_network_coinsurance_amount` (DECIMAL(18,2)): Financial contribution for treatment within preferred networks.
- `in_network_coinsurance_percentage` (DOUBLE): Percentage of treatment cost paid for preferred providers.
- `out_of_network_coinsurance_amount` (DECIMAL(18,2)): Financial contribution for non-preferred networks.
- `out_of_network_coinsuranc_percentage` (DOUBLE): Percentage of treatment cost paid for non-preferred providers.
- `individual_in_network_deductible_limit` (DECIMAL(18,2)): Deductible ceiling for an individual inside preferred networks.
- `individual_in_network_deductible_applied` (DECIMAL(18,2)): Amount individual has already paid toward preferred deductible.
- `individual_in_network_deductible_remaining` (DECIMAL(18,2)): Remaining individual preferred deductible balance.
- `individual_out_of_network_deductible_limit` (DECIMAL(18,2)): Deductible ceiling for an individual with non-preferred providers.
- `individual_out_of_network_deductible_applied` (DECIMAL(18,2)): Amount individual paid toward non-preferred deductible.
- `individual_out_of_network_deductible_remain` (DECIMAL(18,2)): Remaining individual non-preferred deductible balance.
- `family_in_network_deductible_limit` (DECIMAL(18,2)): Deductible limit for all family members in-network.
- `family_in_network_deductible_applied` (DECIMAL(18,2)): Accumulated family spend against in-network deductible.
- `family_in_network_deductible_remaining` (DECIMAL(18,2)): Remaining family in-network deductible.
- `family_out_of_network_deductible_limit` (DECIMAL(18,2)): Deductible limit for all family members out-of-network.
- `family_out_of_network_deductible_applied` (DECIMAL(18,2)): Accumulated family spend against out-of-network deductible.
- `family_out_of_network_deductible_remaining` (DECIMAL(18,2)): Remaining family out-of-network deductible.
- `individual_in_network_out_of_pocket_limit` (DECIMAL(18,2)): Most an individual pays inside the network per year.
- `individual_in_network_out_of_pocket_applied` (DECIMAL(18,2)): In-network out-of-pocket spend consumed by the individual.
- `individual_in_network_out_of_pocket_remaining` (DECIMAL(18,2)): Remaining in-network individual out-of-pocket headroom.
- `individual_out_of_network_out_of_pocket_limit` (DECIMAL(18,2)): Most an individual pays out-of-network per year.
- `individual_out_of_network_out_of_pocket_applied` (DECIMAL(18,2)): Out-of-network out-of-pocket spend consumed by the individual.
- `individual_out_of_network_out_of_pocket_remain` (DECIMAL(18,2)): Remaining out-of-network individual out-of-pocket headroom.
- `family_in_network_out_of_pocket_limit` (DECIMAL(18,2)): Annual out-of-pocket max limit for the whole family in-network.
- `family_in_network_out_of_pocket_applied` (DECIMAL(18,2)): Total out-of-pocket spend consumed by the family in-network.
- `family_in_network_out_of_pocket_remaining` (DECIMAL(18,2)): Remaining in-network family out-of-pocket headroom.
- `family_out_of_network_out_of_pocket_limit` (DECIMAL(18,2)): Annual out-of-pocket max limit for the whole family out-of-network.
- `family_out_of_network_out_of_pocket_applied` (DECIMAL(18,2)): Total out-of-pocket spend consumed by the family out-of-network.
- `family_out_of_network_out_of_pocket_remaining` (DECIMAL(18,2)): Remaining out-of-network family out-of-pocket headroom.
- `in_network_lifetime_maximum` (DECIMAL(18,2)): In-network lifetime expense cap for the plan.
- `out_of_network_lifetime_maximum` (DECIMAL(18,2)): Out-of-network lifetime expense cap for the plan.
- `total_benefit_amount` (DECIMAL(18,2)): Total amount of the coverage benefit associated with a home healthcare visit.
- `frequency_type` (STRING): Frequency type associated with visits (e.g., Daily, Weekly, Monthly, Yearly).
- `status_code_id` (STRING): Key mapping to status metadata in CodeSet.
- `outcome_status_code_id` (STRING): Key mapping to outcome evaluation code sets.
- `final_coverage_status_code_id` (STRING): Code evaluated after constraints are calculated.
- `disclaimer` (STRING): Overall plan benefit disclaimers.
- `benefit_notes` (STRING): Additional context on available benefits.
- `copay_notes` (STRING): Custom descriptions or conditions regarding copays.
- `deductible_notes` (STRING): Detailed text concerning deductibles.
- `coinsurance_notes` (STRING): Text detailing coinsurance requirements.
- `out_of_pocket_notes` (STRING): Additional information about out-of-pocket configurations.
- `lifetime_maximum_notes` (STRING): Explicit notes detailing lifetime max thresholds.
- `source_system` (STRING): Source system tracking identity string.
- `source_system_identifier` (STRING): Unique ID in external legacy core system.
- `source_system_modified` (DATE): Modification tracker from source environment.
- `owner_id` (STRING): User or queue owning the benefit specification ledger.

### 5. coverage_benefit_item
Defines specific medical services or procedure lines categorized under a high-level coverage_benefit block.
- `id` (STRING): Unique ID of the benefit item.
- `name` (STRING): Name of this coverage benefit item (e.g., 'Physical Therapy Session').
- `coverage_benefit_id` (STRING): Mandatory lookup mapping item directly to parent `coverage_benefit.id`.
- `member_id` (STRING): The ID of the member receiving this benefit item.
- `benefit_category` (STRING): General sub-category string name.
- `service_type` (STRING): Detailed functional service type descriptor.
- `service_type_code` (STRING): Clinical or billing code representing the procedure item type.
- `code_set_service_type_id` (STRING): Code Set lookup identifier pointing to specific record in `code_set`.
- `coverage_level` (STRING): Descriptive definition text of current item's coverage parameters.
- `is_active` (BOOLEAN): Flag determining whether this service row item is valid and accessible.
- `is_in_plan_network` (BOOLEAN): True if item is strictly limited to in-network, False if it captures both in/out networks.
- `is_preauthorization_required` (BOOLEAN): Specifies if a prior authorization token must be granted before care.
- `does_deductible_apply` (BOOLEAN): Flag checking if user must completely satisfy deductible criteria first.
- `time_period` (STRING): Description of the time parameters covered by the item row.
- `frequency_type` (STRING): Home health tracking metric interval picklist ('Daily', 'Weekly', 'Monthly', etc.).
- `in_network_coverage` (STRING): Detailed textural layout describing preferred provider item properties.
- `out_of_network_coverage` (STRING): Textual conditions enforcing restrictions outside preferred clinics.
- `notes` (STRING): Text notes attached to the service item profile.
- `source_system` (STRING): Data source marker string.
- `source_system_identifier` (STRING): Core ID string inside system of record.
- `source_system_modified` (TIMESTAMP): Raw timestamp when tracking source altered row details.
- `owner_id` (STRING): Identity tag of record manager.

### 6. coverage_benefit_item_limit
Enforces hard metrics, exclusion conditions, and ceilings directly on a coverage_benefit_item.
- `id` (STRING): Unique record lookup key.
- `name` (STRING): Title identifying the individual ceiling metric.
- `coverage_benefit_item_id` (STRING): Reference back to the target service being throttled (`coverage_benefit_item.id`).
- `care_limit_type_id` (STRING): Relationship link out to `care_limit_type` (e.g., checks copay rules or exclusion filters).
- `coverage_level` (STRING): Defines persons eligible for item tier bounds ('Individual', 'Family', 'EmployeeSpouse').
- `network_type` (STRING): Operational zone tag ('In' [In-network], 'Out' [Out-of-network], 'NA' [Not applicable]).
- `term_type` (STRING): Renewal interval cycle tag ('Calendar Year', 'Day', 'Month', 'Year to Date').
- `allowed_limit` (STRING): Text or monetary label indicating maximum financial spend allowed for this service item.
- `allowed_quantity` (DOUBLE): Numerical ceiling value capturing max unit quantity permitted (e.g., 24.00 visits).
- `allowed_quantity_unit_id` (STRING): Measurement system key mapping to lookup table unit_of_measure.
- `applied_limit` (STRING): Specifies whether the limit rule balance has been actively claimed against.
- `applied_quantity` (DOUBLE): Actual continuous cumulative measure used or claimed by user (e.g., 5.00 visits).
- `applied_quantity_unit_id` (STRING): Consumed measurement unit mapping pointing to unit_of_measure.
- `priority_order` (DOUBLE): Numerical tracking sorting rank determining calculation sequence evaluation layers.
- `limit_notes` (STRING): Core explanatory string capturing notes or terms linked to this rule item.

### 7. account
Salesforce Account. Carries **both** roles in this model — members (person accounts) and payer
organizations (business accounts). Split on `is_person_account` rather than ingesting twice.
- `id` (STRING): Unique ID of the account (Primary Key).
- `name` (STRING): Account name — the member's full name for person accounts, the organization name for business accounts.
- `is_person_account` (BOOLEAN): True for person accounts (members/patients), false for business accounts (payers).
- `first_name` (STRING): Given name (person accounts only).
- `last_name` (STRING): Family name (person accounts only).
- `person_birthdate` (DATE): Date of birth (person accounts only).
- `gender` (STRING): Administrative gender (person accounts only).
- `type` (STRING): Account type classification (e.g., payer, provider, employer).
- `industry` (STRING): Industry classification of the organization.
- `phone` (STRING): Primary phone number.
- `billing_state` (STRING): State of the account's primary address.
- `billing_postal_code` (STRING): Postal code of the account's primary address.
- `billing_country` (STRING): Country of the account's primary address.
- `owner_id` (STRING): The ID of the user who owns this record.

### 8. care_limit_type
Reference table defining the kinds of limits that can be applied to a coverage benefit item
(e.g., copay rules, visit caps, exclusion filters). Exposed through the Tooling API in some
orgs — it may not be ingestible, in which case `coverage_benefit_item_limit.care_limit_type_id`
stays unresolved.
- `id` (STRING): Unique ID of the care limit type.
- `name` (STRING): Name of the limit type.
- `developer_name` (STRING): API/developer name of the limit type.
- `limit_category` (STRING): Category of limit (financial, quantity, exclusion).
- `description` (STRING): Description of what the limit type governs.

### 9. code_set
Reference table of clinical and administrative codes (service types, benefit categories,
priority and status codes) referenced across the benefits model.
- `id` (STRING): Unique ID of the code set record.
- `name` (STRING): Display name of the code.
- `code` (STRING): The code value itself.
- `code_set_type` (STRING): Which code family this record belongs to (e.g., service type, benefit category, priority).
- `code_system` (STRING): Terminology system the code comes from (e.g., CPT, ICD-10, HCPCS).
- `description` (STRING): Human-readable description of the code.
- `is_active` (BOOLEAN): Whether the code is currently in use.

### 10. care_case
Salesforce Case, landed as `care_case` to avoid the reserved word `case`. Represents the CRM
support case (investigation) tied to a benefit verification request.
- `id` (STRING): Unique ID of the case.
- `case_number` (STRING): Autonumber case reference.
- `subject` (STRING): Short description of the case.
- `description` (STRING): Full case detail.
- `status` (STRING): Case status (e.g., New, Working, Escalated, Closed).
- `priority` (STRING): Case priority (e.g., High, Medium, Low).
- `origin` (STRING): How the case arrived (e.g., Phone, Email, Web).
- `type` (STRING): Case type classification.
- `reason` (STRING): Reason the case was opened.
- `account_id` (STRING): The account the case relates to (`account.id`).
- `contact_id` (STRING): The contact the case relates to.
- `owner_id` (STRING): The user or queue that owns the case.
- `created_date` (TIMESTAMP): When the case was created.
- `closed_date` (TIMESTAMP): When the case was closed.

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
