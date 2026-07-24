---
name: health-cloud-benefits
description: End-to-end skill for the Salesforce Health Cloud Benefits Verification data model on Databricks. Scaffolds a Lakeflow Connect managed ingestion pipeline for the 10 core + supporting objects, applies table/column comments, creates governed metric views, then creates a Genie space over the tables and metric views with starter questions. Read this skill when the user asks to "create a benefits verification genie space", set up Health Cloud benefit ingestion, ingest member plans / coverage benefits / care benefit verify requests via Salesforce Lakeflow Connect, or query insurance coverage limits and benefit verification data.
---

# Salesforce Health Cloud Benefits Verification — End-to-End

When triggered, follow these steps to scaffold the full Health Cloud Benefits
ingestion pipeline, governed metric views, and a Genie space for business users.
Steps 1–4 stand up ingestion; steps 5–9 build the semantic layer and Genie space.

The [reference sections](#object-reference) at the bottom (object list, table
schemas, join graph, SQL examples) are the domain knowledge these steps draw on —
consult them when filling in objects, joins, and measures.

## Step 1 — Gather required inputs

If any of the following are not already in context, ask the user:
- **Connection name**: the Salesforce connection to use (call `connectionList` to show available options if needed)
- **Pipeline name**: default to `health_cloud_benefits` if not specified
- **Destination catalog**
- **Destination schema**

## Step 2 — Verify permissions

Check that the user has `CreateTable` permission on the destination schema:
- `checkPermissions(actionName="CreateTable", securableType="SCHEMA", securableFullName="<catalog>.<schema>")`

## Step 3 — Propose the pipeline spec

Call `setPendingPipelineSpec` with the complete YAML below, substituting the user's
values for all `<placeholders>`.

- For Salesforce, `source_schema` is always `objects` and `source_table` is the
  Salesforce object **API name** (PascalCase).
- `destination_table` is set explicitly to a **snake_case** name so the landed
  tables match the schema, join graph, and metric views in this skill. (Without an
  explicit name, Salesforce objects land lowercased and concatenated, e.g.
  `coveragebenefit`.)

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

## Step 4 — Save and validate

1. After the user confirms, call `editIngestionPipeline` to persist the spec.
2. Call `startPipelineDryRun` to validate without ingesting data.

Note: the metric views and Genie space below become fully functional once the
pipeline has run and populated the destination tables. You can create them before
data lands, but validation queries will return no rows until ingestion completes.

## Step 5 — Verify landed schema and apply comments

Salesforce lands **column** names in Salesforce API casing (e.g. `Id`, `Name`,
`CreatedDate`, `PrimaryCareCopay`) — these are not renamed by the pipeline. Before
building metric views, confirm the actual column names and add comments so Genie
has rich metadata.

1. Inspect real column names (repeat per table as needed):
   ```sql
   -- via executeCode(language="sql")
   DESCRIBE TABLE <catalog>.<schema>.coverage_benefit
   ```
2. Map the documented semantic columns in the
   [Table Schemas](#table-schemas--complete-column-metadata) reference to the
   actual landed column names, and use those actual names in Steps 6 onward.
3. Apply table and column comments (the descriptions already live in the schema
   reference — this makes Genie's SQL generation materially more accurate). Run
   via `executeCode(language="sql")`, one statement at a time:
   ```sql
   COMMENT ON TABLE <catalog>.<schema>.coverage_benefit IS
     'Core financial and structural benefits provided to a covered member by a purchaser plan.';

   ALTER TABLE <catalog>.<schema>.coverage_benefit ALTER COLUMN <IndividualInNetworkDeductibleRemaining>
     COMMENT 'Remaining individual preferred (in-network) deductible balance.';
   -- ...repeat for the columns used as dimensions/measures below
   ```

> If column names in Step 6's metric views don't match the `DESCRIBE` output,
> substitute the real names before running — otherwise `CREATE VIEW` will fail with
> "cannot resolve column".

## Step 6 — Create metric views

Create two governed metric views using `executeCode` with `language: "sql"`, run
separately. Two views (not one) because the financial figures live at the
`coverage_benefit` grain while utilization/limit figures live at the
`coverage_benefit_item_limit` grain — one view per grain avoids fan-out double
counting. Metric views require **Databricks Runtime 17.2+** for YAML `version: 1.1`.

### 6a. Benefits cost-sharing metrics

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

### 6b. Benefit utilization metrics

Sourced from the item-limit grain, joining up to plan context. Captures
allowed vs. applied vs. remaining service quantities.

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

### Validate

Metric views require the `MEASURE()` function and do **not** support `SELECT *`:

```sql
SELECT
  `Coverage Type`,
  `Plan Type`,
  MEASURE(`Avg Individual In-Network Deductible Remaining`) AS avg_deductible_remaining,
  MEASURE(`Coverage Benefit Count`) AS benefit_count
FROM <catalog>.<schema>.benefits_cost_metrics
WHERE `Is Active Benefit` = true
GROUP BY ALL
ORDER BY ALL
```

## Step 7 — Create Genie space

Create a Genie space over the two metric views **plus** the core raw tables (metric
views give governed answers; raw tables let users drill to row-level detail). Use
`createAsset` with `assetType: "genie"`:

```
createAsset({
  assetType: "genie",
  name: "Health Cloud Benefits Verification",
  description: "Benefit verification analytics for member plans, coverage benefits, and utilization limits. Prefer the metric views (benefits_cost_metrics, benefit_utilization_metrics) for aggregate questions; join through member_plan -> coverage_benefit -> coverage_benefit_item -> coverage_benefit_item_limit for row-level detail.",
  tableIdentifiers: [
    "<catalog>.<schema>.benefits_cost_metrics",
    "<catalog>.<schema>.benefit_utilization_metrics",
    "<catalog>.<schema>.member_plan",
    "<catalog>.<schema>.purchaser_plan",
    "<catalog>.<schema>.care_benefit_verify_request",
    "<catalog>.<schema>.coverage_benefit",
    "<catalog>.<schema>.coverage_benefit_item",
    "<catalog>.<schema>.coverage_benefit_item_limit",
    "<catalog>.<schema>.account",
    "<catalog>.<schema>.care_limit_type",
    "<catalog>.<schema>.code_set",
    "<catalog>.<schema>.care_case"
  ]
})
```

## Step 8 — Navigate to Genie space

```
openAsset({
  assetType: "genie",
  assetId: "<genie_space_id>",
  assetName: "Health Cloud Benefits Verification",
  navigate: true,
  continueMessage: ""
})
```

Use the `assetId` returned by `createAsset`.

## Step 9 — Add starter questions

Add starter questions that reference the metric views so business users have
accurate, one-click entry points:

```
addStarterQuestions({
  questions: [
    { questionText: "What is the MEASURE(Avg Individual In-Network Deductible Remaining) by Plan Type from benefits_cost_metrics?", isDeepResearch: true },
    { questionText: "Compare MEASURE(Avg Specialist Copay) across Plan Type from benefits_cost_metrics", isDeepResearch: true },
    { questionText: "Show MEASURE(Coverage Benefit Count) grouped by Verification Status from benefits_cost_metrics", isDeepResearch: true },
    { questionText: "What is the MEASURE(Total Remaining Quantity) by Coverage Type for active benefits from benefit_utilization_metrics?", isDeepResearch: true },
    { questionText: "Which Service Types have the highest MEASURE(Avg Utilization Rate) from benefit_utilization_metrics?", isDeepResearch: true }
  ]
})
```

---

## Object reference

**Core benefit verification objects (6)** — Salesforce API name → landed table:
`MemberPlan` → `member_plan`, `PurchaserPlan` → `purchaser_plan`,
`CareBenefitVerifyRequest` → `care_benefit_verify_request`,
`CoverageBenefit` → `coverage_benefit`, `CoverageBenefitItem` → `coverage_benefit_item`,
`CoverageBenefitItemLimit` → `coverage_benefit_item_limit`

**Supporting reference objects (4)**:
`Account` → `account`, `CareLimitType` → `care_limit_type`, `CodeSet` → `code_set`,
`Case` → `care_case` (renamed to avoid the reserved word `case`)

---

## Table Schemas & Complete Column Metadata

> These are the **semantic** column definitions for the data model. Salesforce lands
> the physical columns in API casing — reconcile names via `DESCRIBE TABLE`
> (Step 5) before use.

### 1. member_plan
Represents details about the insurance coverage for a member or subscriber.
- `id` (STRING): Unique ID of the Member Plan record (Primary Key).
- `name` (STRING): The name by which the member knows this plan.
- `member_id` (STRING): The ID of the member’s record.
- `member_number` (STRING): The member’s reference number for this plan.
- `subscriber_id` (STRING): The ID of the primary subscriber’s record.
- `relationship_to_subscriber` (STRING): Picklist value mapping the relationship to the subscriber (e.g., 'Self', 'Spouse', 'Child', 'Unknown', 'Other Relationship').
- `plan_id` (STRING): Foreign key lookup pointing to `purchaser_plan.id`.
- `payer_id` (STRING): Foreign key lookup pointing to the payer’s Account object record (`account.id`).
- `payer_network_id` (STRING): Foreign key pointing to a healthcare payer network table.
- `group_number` (STRING): The group number or policy number of the primary member.
- `issuer_number` (STRING): Reference number for the issuer of the plan.
- `effective_from` (DATE): The date from which this member plan is effective.
- `effective_to` (DATE): The date on which this member plan ceases to be effective.
- `status` (STRING): Indicates whether the plan is active.
- `verification_status` (STRING): Status of the plan’s verification (e.g., 'Active - Verified', 'Rejected', 'Not Checked', 'Unknown', 'Inactive').
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
Represents the payer plan that a purchaser makes available to its members and members’ dependents.
- `id` (STRING): Unique ID of the Purchaser Plan.
- `name` (STRING): The name of this plan.
- `plan_number` (STRING): The plan’s reference number.
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
- `case_id` (STRING): Identifies the associated CRM support Case.
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
Represents the core financial and structural benefits provided to a covered member by a purchaser’s plan.
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
- `care_limit_type_id` (STRING): Relationship link out to care_limit_type (e.g., checks copay rules or exclusion filters).
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

---

## Join Guidance

Join through the structural hierarchy:
`account (id)` → `member_plan (payer_id / member context)` → `coverage_benefit (member_plan_id)` → `coverage_benefit_item (coverage_benefit_id)` → `coverage_benefit_item_limit (coverage_benefit_item_id)`.

Verification requests link in via `care_benefit_verify_request.member_plan_id` and
`.coverage_benefit_id`. Purchaser plan context comes from `member_plan.plan_id → purchaser_plan.id`.

**Filter guardrails:** for active-rule questions, use
`WHERE member_plan.status = 'Active' AND coverage_benefit.is_active = true AND coverage_benefit_item.is_active = true`.

---

## SQL Examples

### Calculate remaining service quantities for a member's plan

```sql
SELECT
    a.name AS member_name,
    mp.name AS plan_name,
    cbi.name AS service_covered,
    cbil.allowed_quantity,
    cbil.applied_quantity,
    (cbil.allowed_quantity - cbil.applied_quantity) AS remaining_quantity_allowed,
    cbil.term_type
FROM member_plan mp
JOIN account a ON mp.payer_id = a.id
JOIN coverage_benefit cb ON cb.member_plan_id = mp.id
JOIN coverage_benefit_item cbi ON cbi.coverage_benefit_id = cb.id
JOIN coverage_benefit_item_limit cbil ON cbil.coverage_benefit_item_id = cbi.id
WHERE mp.status = 'Active'
  AND cb.is_active = true;
```
