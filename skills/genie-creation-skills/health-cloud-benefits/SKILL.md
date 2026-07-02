---
name: health-cloud-benefits
description: Comprehensive schema definitions, table relationships, and SQL join logic for querying the Salesforce Health Cloud Benefits Verification data model. Use this skill whenever a user asks about member plans, insurance coverage limits, or care benefit verification requests.
---

# Salesforce Health Cloud Benefits Verification Skill

This skill provides the final, production-ready schema structures, accurate column data types, and core relationship mappings required for Databricks Genie to perfectly query patient benefit and insurance verification data ingested via Lakeflow Connect.

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

---

## Step-by-Step Join Guidance

When executing analytics queries or building user summaries via Genie, perform table joins through the structural hierarchy sequence below:
`person_account (id)` -> `member_plan (account_id)` -> `coverage_benefit (member_plan_id)` -> `coverage_benefit_item (coverage_benefit_id)` -> `coverage_benefit_item_limit (coverage_benefit_item_id)`.

**Filter Logic Guardrails:**
- To identify if checking individual rules, confirm active states using: `WHERE member_plan.status = 'Active' AND coverage_benefit.is_active = true AND coverage_benefit_item.is_active = true`

---

## SQL Examples

### Example 1: Calculate Remaining Quantities Left for a Member's Plan Services
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
JOIN person_account pa ON mp.account_id = pa.id
JOIN coverage_benefit cb ON cb.member_plan_id = mp.id
JOIN coverage_benefit_item cbi ON cbi.coverage_benefit_id = cb.id
JOIN coverage_benefit_item_limit cbil ON cbil.coverage_benefit_item_id = cbi.id
WHERE mp.status = 'Active' 
  AND cb.is_active = true;
