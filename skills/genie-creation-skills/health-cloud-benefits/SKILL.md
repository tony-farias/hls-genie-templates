---
name: health-cloud-benefits
description: Schema definitions, Unity Catalog column comments, metric view definitions, and example join queries for the Salesforce Health Cloud Benefits Verification data model, and the end-to-end workflow for grounding a Databricks Genie space over it. Use when a user asks to "create health cloud benefits genie template" (or to create, build, or generate a Health Cloud benefits Genie template, space, or room), and whenever a user asks about member plans, purchaser plans, insurance coverage limits, copays, deductibles, out-of-pocket maximums, or care benefit verification requests.
---

# Salesforce Health Cloud Benefits Verification Skill

This skill provides the production-ready schema structures, accurate column data types, core
relationship mappings, and governed metric definitions required for Databricks Genie to query
patient benefit and insurance verification data ingested via Lakeflow Connect.

## Genie template workflow

When asked to create the Health Cloud Benefits Genie template, work through the steps below
in order. Each layer carries a different kind of knowledge — keep them separate.

| Layer | Carries | Built from |
|---|---|---|
| UC table/column comments | what each table and column means | the schema section below |
| Metric view metadata | governed dimensions, measures, formulas, synonyms, formats | the metric views below |
| Example queries | join paths and expected query shapes | the example queries below |
| Genie instructions | company-wide business context only | supplied by the user, never invented |

1. **Persist metadata to Unity Catalog** — table and column comments (step 1).
2. **Create the metric views** — the governed KPI layer (step 2).
3. **Create the Genie space** — metric views first, detail tables only where needed (step 3).
4. **Add example queries** — where join paths belong, as working SQL (step 4).
5. **Add instructions only for company-wide context the user supplies** (step 5).

For the space-creation API calls and for wiring the space into the app's "Ask Genie" button,
use the `create-genie-space` skill.

## Step 1 — Persist metadata to Unity Catalog

The schema section below is the source of truth, but UC comments are what Genie and Catalog
Explorer actually read. Write them before creating the space, for every table the space
exposes.

```sql
COMMENT ON TABLE <catalog>.<schema>.member_plan IS
  'Insurance coverage for a member or subscriber (Salesforce Health Cloud MemberPlan).';

ALTER TABLE <catalog>.<schema>.member_plan ALTER COLUMN verification_status
  COMMENT 'Status of the plan''s verification: Active - Verified, Rejected, Not Checked, Unknown, Inactive.';
```

Escape single quotes inside a comment by doubling them (`''`). Verify with
`DESCRIBE TABLE EXTENDED <catalog>.<schema>.member_plan`.

## Table Schemas & Complete Column Metadata

### 1. member_plan
Represents details about the insurance coverage for a member or subscriber.
- `id` (STRING): Unique ID of the Member Plan record (Primary Key).
- `name` (STRING): The name by which the member knows this plan.
- `member_id` (STRING): The ID of the member’s record.
- `member_number` (STRING): The member’s reference number for this plan.
- `subscriber_id` (STRING): The ID of the primary subscriber’s record.
- `relationship_to_subscriber` (STRING): Picklist value mapping the relationship to the subscriber (e.g., 'Self', 'Spouse', 'Child', 'Unknown', 'Other Relationship').
- `plan_id` (STRING): Foreign key lookup pointing to `purchaser_plan.id`.
- `payer_id` (STRING): Foreign key lookup pointing to the payer’s Account object record (`business_account.id`).
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
- `payer` (STRING): Foreign key lookup pointing to the payer's Account object record (`business_account.id`).
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

### 7. person_account
The member / patient dimension. Referenced by `member_plan.member_id` and `coverage_benefit.member_id`.
- `id` (STRING): Unique ID of the person account (Primary Key).
- `name` (STRING): The member's full name.
- `first_name` (STRING): Given name.
- `last_name` (STRING): Family name.
- `birth_date` (DATE): Date of birth.
- `gender` (STRING): Administrative gender.
- `is_deceased` (BOOLEAN): Deceased flag.
- `billing_state` (STRING): State of the member's primary address.
- `billing_postal_code` (STRING): Postal code of the member's primary address.

---

## Step 2 — Metric views

Build the governed KPI layer before creating the space. Carry the business meaning in each
dimension's and measure's `comment` (and `synonyms` on DBR 17.3+) — that metadata is what
Genie reads, so it does not need to be repeated as instructions.

### `benefits_coverage_metrics` — plan and coverage rollups
```sql
CREATE OR REPLACE VIEW <catalog>.<schema>.benefits_coverage_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: <catalog>.<schema>.coverage_benefit
  comment: "Coverage benefit KPIs by plan, payer plan type, and coverage category."
  joins:
    - name: member_plan
      source: <catalog>.<schema>.member_plan
      on: source.member_plan_id = member_plan.id
    - name: purchaser_plan
      source: <catalog>.<schema>.purchaser_plan
      on: member_plan.plan_id = purchaser_plan.id
    - name: person_account
      source: <catalog>.<schema>.person_account
      on: source.member_id = person_account.id
  dimensions:
    - name: Coverage Type
      expr: source.coverage_type
      comment: "Service category covered: Medical, Dental, Vision, Home Health, Pharmacy."
    - name: Plan Type
      expr: purchaser_plan.plan_type
      comment: "Payer plan type: PPO, HMO, Medicare, Medicaid, Workers Comp."
    - name: Line Of Business
      expr: purchaser_plan.line_of_business
      comment: "Insurance policy category the payer plan belongs to."
    - name: Verification Status
      expr: member_plan.verification_status
      comment: "Member plan verification state, e.g. Active - Verified, Rejected, Not Checked."
    - name: Benefit Period Month
      expr: DATE_TRUNC('MONTH', source.benefit_period_start_date)
      comment: "Month in which the coverage benefit period starts."
    - name: Is Active Coverage
      expr: source.is_active
      comment: "Whether the coverage benefit is currently in force."
  measures:
    - name: Coverage Benefit Count
      expr: COUNT(1)
      comment: "Number of coverage benefit records."
    - name: Member Count
      expr: COUNT(DISTINCT source.member_id)
      comment: "Distinct members with coverage benefits."
    - name: Avg Primary Care Copay
      expr: AVG(source.primary_care_copay)
      comment: "Average member contribution for primary care treatment."
    - name: Avg Specialist Copay
      expr: AVG(source.specialist_copay)
      comment: "Average member contribution for specialist consultations."
    - name: In Network Deductible Remaining
      expr: SUM(source.individual_in_network_deductible_remaining)
      comment: "Total remaining individual in-network deductible balance."
    - name: In Network Out Of Pocket Remaining
      expr: SUM(source.individual_in_network_out_of_pocket_remaining)
      comment: "Total remaining individual in-network out-of-pocket headroom."
$$
```

### `benefit_limit_utilization_metrics` — allowed vs applied limits
```sql
CREATE OR REPLACE VIEW <catalog>.<schema>.benefit_limit_utilization_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: <catalog>.<schema>.coverage_benefit_item_limit
  comment: "Utilization of service-level benefit limits: allowed vs applied quantity."
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
  dimensions:
    - name: Service Covered
      expr: coverage_benefit_item.name
      comment: "Covered service or procedure line, e.g. Physical Therapy Session."
    - name: Benefit Category
      expr: coverage_benefit_item.benefit_category
      comment: "Sub-category of the covered service."
    - name: Coverage Level
      expr: source.coverage_level
      comment: "Who the limit applies to: Individual, Family, EmployeeSpouse."
    - name: Network Type
      expr: source.network_type
      comment: "Limit network scope: In (in-network), Out (out-of-network), NA."
    - name: Term Type
      expr: source.term_type
      comment: "Limit renewal interval: Calendar Year, Day, Month, Year to Date."
    - name: Preauthorization Required
      expr: coverage_benefit_item.is_preauthorization_required
      comment: "Whether prior authorization must be granted before care."
  measures:
    - name: Allowed Quantity
      expr: SUM(source.allowed_quantity)
      comment: "Maximum permitted units, e.g. covered visits."
    - name: Applied Quantity
      expr: SUM(source.applied_quantity)
      comment: "Units already used or claimed."
    - name: Remaining Quantity
      expr: SUM(source.allowed_quantity) - SUM(source.applied_quantity)
      comment: "Units still available under the limit."
    - name: Utilization Rate
      expr: SUM(source.applied_quantity) / NULLIF(SUM(source.allowed_quantity), 0)
      comment: "Applied quantity as a share of allowed quantity."
$$
```

---

## Step 3 — Genie space sources

Give the space the **metric views first**. Add underlying tables only for questions the
metric views cannot answer — row-level lookups such as an individual verification request,
its response payload, or free-text notes.

- **Default set:** `benefits_coverage_metrics`, `benefit_limit_utilization_metrics`
- **Add for record-level detail:** `care_benefit_verify_request`, `member_plan`, `person_account`
- **Do not** add every underlying table alongside the metric views by default. Duplicate query
  paths over the same facts create ambiguity and let Genie aggregate inconsistently.

---

## Step 4 — Example queries

Join paths belong here, as working SQL, not in instructions. Register these as the space's
example queries / benchmarks so Genie learns the join hierarchy from queries that run.

The structural hierarchy is:
`person_account (id)` → `member_plan (member_id)` → `coverage_benefit (member_plan_id)` →
`coverage_benefit_item (coverage_benefit_id)` → `coverage_benefit_item_limit (coverage_benefit_item_id)`

Active-state filter used across the detail examples:
`WHERE member_plan.status = 'Active' AND coverage_benefit.is_active = true AND coverage_benefit_item.is_active = true`

### Example 1 — Remaining quantities left for a member's plan services
```sql
SELECT
    pa.name AS member_name,
    mp.name AS plan_name,
    cbi.name AS service_covered,
    cbil.allowed_quantity,
    cbil.applied_quantity,
    (cbil.allowed_quantity - cbil.applied_quantity) AS remaining_quantity_allowed,
    cbil.term_type
FROM member_plan mp
JOIN person_account pa ON mp.member_id = pa.id
JOIN coverage_benefit cb ON cb.member_plan_id = mp.id
JOIN coverage_benefit_item cbi ON cbi.coverage_benefit_id = cb.id
JOIN coverage_benefit_item_limit cbil ON cbil.coverage_benefit_item_id = cbi.id
WHERE mp.status = 'Active'
  AND cb.is_active = true
  AND cbi.is_active = true;
```

### Example 2 — Limit utilization by service and network (metric view)
```sql
SELECT
    `Service Covered`,
    `Network Type`,
    MEASURE(`Allowed Quantity`) AS allowed_quantity,
    MEASURE(`Applied Quantity`) AS applied_quantity,
    MEASURE(`Remaining Quantity`) AS remaining_quantity,
    MEASURE(`Utilization Rate`) AS utilization_rate
FROM <catalog>.<schema>.benefit_limit_utilization_metrics
GROUP BY ALL
ORDER BY ALL;
```

### Example 3 — Average copays by plan type and coverage type (metric view)
```sql
SELECT
    `Plan Type`,
    `Coverage Type`,
    MEASURE(`Member Count`) AS member_count,
    MEASURE(`Avg Primary Care Copay`) AS avg_primary_care_copay,
    MEASURE(`Avg Specialist Copay`) AS avg_specialist_copay
FROM <catalog>.<schema>.benefits_coverage_metrics
WHERE `Is Active Coverage` = true
GROUP BY ALL
ORDER BY ALL;
```

### Example 4 — Verification requests pending for a member
```sql
SELECT
    pa.name AS member_name,
    mp.name AS plan_name,
    cbvr.name AS request_name,
    cbvr.status,
    cbvr.status_reason,
    cbvr.verification_mode,
    cbvr.request_date
FROM care_benefit_verify_request cbvr
JOIN member_plan mp ON cbvr.member_plan_id = mp.id
JOIN person_account pa ON mp.member_id = pa.id
WHERE cbvr.status IN ('Pending', 'Ready for Verification', 'Pending Confirmation')
ORDER BY cbvr.request_date DESC;
```

---

## Step 5 — Instructions

Instructions are for **company-wide business context only** — the things no amount of schema
metadata can convey:

- official definitions (what counts as an "active member" or "verified coverage")
- fiscal or plan-year conventions
- authoritative source precedence when systems disagree
- privacy and exclusion rules
- approved terminology and reporting/rounding policy

Take these from the user. **Do not invent them, and do not put join logic, table routing, or
metric-view selection into instructions** — those belong in the metric view metadata (step 2),
the source selection (step 3), and the example queries (step 4). If the user supplies no
company-wide context, leave the instructions empty.
