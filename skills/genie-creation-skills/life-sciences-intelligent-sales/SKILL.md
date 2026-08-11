---
name: life-sciences-intelligent-sales
description: End-to-end skill for the Salesforce Life Sciences Intelligent Sales data model on Databricks. Scaffolds a Lakeflow Connect managed ingestion pipeline for the 17 core visit, inventory, and supporting objects, applies Unity Catalog table/column comments, creates governed metric views, then creates a Genie space with starter questions. Use when a user asks to "create life sciences intelligent sales genie template" or "create an intelligent sales genie space", to set up Life Sciences visit/inventory ingestion via Salesforce Lakeflow Connect, or to query provider visits, visitors, visited parties, assessment tasks, product items, product transfers, product requests, fulfillment locations, availability projections, or serialized field inventory.
---

# Salesforce Life Sciences Intelligent Sales — End-to-End

Steps 1–5 stand up ingestion; steps 6–10 build the semantic layer and the Genie space.
Column-level definitions are in the **Column reference** section below — use them when
writing comments or filling in metric view expressions.

**Canonical docs:**
- [Intelligent Sales data model (Life Sciences)](https://developer.salesforce.com/docs/atlas.en-us.life_sciences_dev_guide.meta/life_sciences_dev_guide/hc_intelligent_sales_data_model.htm)
- [Data Model Gallery — Intelligent Sales](https://developer.salesforce.com/docs/platform/data-models/guide/intelligent-sales.html)

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
- **Pipeline name** — default `life_sciences_intelligent_sales`
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
3. Confirm the 17 source objects are actually visible through the connection before saving a
   spec. `ProductAvailabilityProjection` is auto-created by Intelligent Sales — if the feature
   is not enabled in the org the object may be missing or empty; report that plainly and
   continue with the remaining objects rather than silently dropping it.

## Step 3 — Propose the pipeline spec

Call `setPendingPipelineSpec` with the YAML below, substituting the user's values.

- For Salesforce, `source_schema` is always `objects` and `source_table` is the Salesforce
  object **API name** (PascalCase).
- `destination_table` is set explicitly to **snake_case** so landed tables match the schema
  reference, join graph, and metric views. Without it, Salesforce objects land lowercased and
  concatenated (e.g. `productavailabilityprojection`).
- `Account` is ingested **once**. Salesforce stores provider accounts (business) and person
  accounts in the same object; separate them downstream on `IsPersonAccount`, never by
  ingesting `Account` twice into the same schema.

```yaml
name: <pipeline_name>
catalog: <destination_catalog>
schema: <destination_schema>
ingestion_definition:
  connection_name: <connection_name>
  objects:
    # ── Core visit execution objects (6) ───────────────────────────
    - table:
        source_schema: objects
        source_table: Visit
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: visit
    - table:
        source_schema: objects
        source_table: Visitor
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: visitor
    - table:
        source_schema: objects
        source_table: VisitedParty
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: visited_party
    - table:
        source_schema: objects
        source_table: AssessmentTask
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: assessment_task
    - table:
        source_schema: objects
        source_table: ProductRequired
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: product_required
    - table:
        source_schema: objects
        source_table: WorkType
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: work_type
    # ── Inventory & fulfillment objects (9) ────────────────────────
    - table:
        source_schema: objects
        source_table: Product2
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: product2
    - table:
        source_schema: objects
        source_table: ProductItem
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: product_item
    - table:
        source_schema: objects
        source_table: ProductTransfer
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: product_transfer
    - table:
        source_schema: objects
        source_table: ProductRequest
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: product_request
    - table:
        source_schema: objects
        source_table: ProductRequestLineItem
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: product_request_line_item
    - table:
        source_schema: objects
        source_table: ProductFulfillmentLocation
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: product_fulfillment_location
    - table:
        source_schema: objects
        source_table: ProductAvailabilityProjection
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: product_availability_projection
    - table:
        source_schema: objects
        source_table: SerializedProduct
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: serialized_product
    - table:
        source_schema: objects
        source_table: Location
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: location
    # ── Supporting reference objects (2) ───────────────────────────
    - table:
        source_schema: objects
        source_table: Account
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: account
    - table:
        source_schema: objects
        source_table: Contact
        destination_catalog: <destination_catalog>
        destination_schema: <destination_schema>
        destination_table: contact
```

If the user asks for the pipeline via YAML or Genie Code, author it here — do not redirect them
to the ingestion UI wizard.

The full Intelligent Sales gallery also includes Action Plan*, Generic Visit Task*, Order,
Asset, Service Resources, User, and related objects. Do **not** add them to the default
pipeline unless the user asks — they are not required for the metric views or Genie sources
below.

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

Expect all 17 (or fewer if an object was rejected in step 4). Report anything missing instead
of proceeding as though ingestion succeeded.

## Step 6 — Reconcile landed column names

Salesforce lands **column** names in Salesforce API casing (`Id`, `Name`, `PlannedVisitStartTime`,
`QuantityOnHand`) — the pipeline does not snake_case them. The Column reference definitions
below are semantic, so map them to the real names before writing any SQL:

```sql
DESCRIBE TABLE <catalog>.<schema>.visit
```

Use the actual names in steps 7 and 8. If a metric view references a column that
`DESCRIBE` didn't return, `CREATE VIEW` fails with "cannot resolve column".

## Step 7 — Apply Unity Catalog comments

UC comments are what Genie and Catalog Explorer read, and they measurably improve Genie's SQL
accuracy. Take the text from the Column reference below and run one statement at a time:

```sql
COMMENT ON TABLE <catalog>.<schema>.visit IS
  'Field rep visit to a healthcare provider or account (Salesforce Life Sciences Visit).';

ALTER TABLE <catalog>.<schema>.visit ALTER COLUMN Status
  COMMENT 'Visit lifecycle status: Planned, InProgress, Completed, Abandoned, Unscheduled, Error, None.';
```

Escape single quotes by doubling them (`''`). Verify with `DESCRIBE TABLE EXTENDED`.

## Step 8 — Create metric views

Two views, not one: visit execution lives at the `visit` grain while availability lives at the
`product_availability_projection` grain. One view per grain avoids fan-out double counting.
Requires **DBR 17.2+** for YAML `version: 1.1`; drop `format:` blocks on older runtimes.

### 8a. Visit execution metrics

```sql
CREATE OR REPLACE VIEW <catalog>.<schema>.visit_execution_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: Provider visit execution KPIs by status, channel, priority, and visit type
  source: <catalog>.<schema>.visit
  joins:
    - name: work_type
      source: <catalog>.<schema>.work_type
      on: source.visit_type_id = work_type.id
    - name: account
      source: <catalog>.<schema>.account
      on: source.account_id = account.id
  dimensions:
    - name: Visit Status
      expr: source.status
      comment: Visit lifecycle status — Planned, InProgress, Completed, Abandoned, Unscheduled, Error, None
    - name: Channel
      expr: source.channel
      comment: Visit channel, typically In-Person
    - name: Visit Priority
      expr: source.visit_priority
      comment: Visit priority — High, Medium, Low
    - name: Visit Type
      expr: work_type.name
      comment: Work / visit type name from the work type catalog
    - name: Account Name
      expr: account.name
      comment: Account being visited (provider org or person account)
    - name: Planned Visit Month
      expr: DATE_TRUNC('MONTH', source.planned_visit_start_time)
      comment: Month of the planned visit start
  measures:
    - name: Visit Count
      expr: COUNT(1)
      comment: Number of visit records
    - name: Completed Visit Count
      expr: COUNT(CASE WHEN source.status = 'Completed' THEN 1 END)
      comment: Visits with status Completed
    - name: In Progress Visit Count
      expr: COUNT(CASE WHEN source.status = 'InProgress' THEN 1 END)
      comment: Visits currently in progress
    - name: Abandoned Visit Count
      expr: COUNT(CASE WHEN source.status = 'Abandoned' THEN 1 END)
      comment: Visits that were abandoned
    - name: Avg Planned Duration Hours
      expr: AVG(TIMESTAMPDIFF(HOUR, source.planned_visit_start_time, source.planned_visit_end_time))
      comment: Average planned visit duration in hours
$$
```

### 8b. Inventory availability metrics

```sql
CREATE OR REPLACE VIEW <catalog>.<schema>.inventory_availability_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: Projected product availability and shortfalls by inventory location and product
  source: <catalog>.<schema>.product_availability_projection
  joins:
    - name: product2
      source: <catalog>.<schema>.product2
      on: source.product2_id = product2.id
    - name: location
      source: <catalog>.<schema>.location
      on: source.product_location_id = location.id
  dimensions:
    - name: Product Name
      expr: product2.name
      comment: Sellable / inventoriable product name
    - name: Product Family
      expr: product2.family
      comment: Product family picklist
    - name: Inventory Location
      expr: location.name
      comment: Inventory location where the projection applies
    - name: Location Type
      expr: location.location_type
      comment: Location type — Warehouse, Site, Van, Plant, etc.
    - name: Projection Date
      expr: source.projection_date
      comment: Date the quantity projection applies
    - name: Availability Status
      expr: source.status
      comment: Projection status — Available, ProjectedAvailable, Shortfall
  measures:
    - name: Projected Quantity
      expr: SUM(source.projected_quantity)
      comment: Projected available quantity at the inventory location
    - name: Shortfall Count
      expr: COUNT(CASE WHEN source.status = 'Shortfall' THEN 1 END)
      comment: Number of shortfall projection rows
    - name: Available Count
      expr: COUNT(CASE WHEN source.status = 'Available' THEN 1 END)
      comment: Number of available projection rows
    - name: Projection Row Count
      expr: COUNT(1)
      comment: Number of availability projection rows
$$
```

Validate each view with a query before moving on. Metric views require `MEASURE()` around
measures and do not support `SELECT *` — see example 2 below for the shape.

## Step 9 — Create the Genie space

Give the space the **two metric views plus the detail tables users actually drill into** — not
every landed table. Duplicate query paths over the same facts create ambiguity and let Genie
aggregate inconsistently. Reference tables (`work_type`, `location`, `product2`, `contact`) are
already reachable through joins and metric views; add them only if the user asks questions that
need row-level lookups there.

```
createAsset({
  assetType: "genie",
  name: "Life Sciences Intelligent Sales",
  description: "Provider visit execution and field inventory analytics for Life Sciences Intelligent Sales.",
  tableIdentifiers: [
    "<catalog>.<schema>.visit_execution_metrics",
    "<catalog>.<schema>.inventory_availability_metrics",
    "<catalog>.<schema>.visit",
    "<catalog>.<schema>.visitor",
    "<catalog>.<schema>.visited_party",
    "<catalog>.<schema>.assessment_task",
    "<catalog>.<schema>.product_transfer",
    "<catalog>.<schema>.product_request",
    "<catalog>.<schema>.account"
  ]
})
```

Then navigate to it with the returned `assetId`:

```
openAsset({
  assetType: "genie",
  assetId: "<genie_space_id>",
  assetName: "Life Sciences Intelligent Sales",
  navigate: true,
  continueMessage: ""
})
```

**Instructions** on the space are for company-wide business context only — official definitions
(what counts as a "completed visit" or "shortfall"), territory reporting conventions, source
precedence, privacy rules, approved terminology. Take these from the user; do not invent them,
and keep join logic, table routing, and metric-view selection out of them. Those belong in the
metric view metadata (step 8), the source list above, and the example queries below.

## Step 10 — Add starter questions

Phrase these the way a business user would ask. Don't leak `MEASURE()` syntax or view names
into the question text — Genie resolves those from the metadata.

```
addStarterQuestions({
  questions: [
    { questionText: "How many visits were completed versus abandoned this quarter?", isDeepResearch: true },
    { questionText: "Which visit types have the highest completion rate?", isDeepResearch: true },
    { questionText: "Where are the inventory shortfalls by product and location?", isDeepResearch: true },
    { questionText: "Which product transfers are still outstanding?", isDeepResearch: true },
    { questionText: "What assessment tasks are incomplete for recent visits?", isDeepResearch: true }
  ]
})
```

Register the example queries below as the space's example queries / benchmarks so Genie learns
the join paths from SQL that runs.

---

## Object reference — 17 ingested objects

**Core visit execution (6)** — Salesforce API name → landed table:
`Visit` → `visit`, `Visitor` → `visitor`, `VisitedParty` → `visited_party`,
`AssessmentTask` → `assessment_task`, `ProductRequired` → `product_required`,
`WorkType` → `work_type`

**Inventory & fulfillment (9)**:
`Product2` → `product2`, `ProductItem` → `product_item`, `ProductTransfer` → `product_transfer`,
`ProductRequest` → `product_request`, `ProductRequestLineItem` → `product_request_line_item`,
`ProductFulfillmentLocation` → `product_fulfillment_location`,
`ProductAvailabilityProjection` → `product_availability_projection`,
`SerializedProduct` → `serialized_product`, `Location` → `location`

**Supporting (2)**:
`Account` → `account`, `Contact` → `contact`

---

## Column reference

Semantic column definitions for the 17 ingested tables. Salesforce lands the **physical**
columns in API casing (`Id`, `Name`, `PlannedVisitStartTime`, `QuantityOnHand`), so reconcile
names with `DESCRIBE TABLE` before writing SQL (step 6). Use these descriptions as the text for
the `COMMENT ON TABLE` / `ALTER COLUMN ... COMMENT` statements in step 7.

### 1. visit
Field rep visit to a healthcare provider / account (core fact table).
- `id` (STRING): Primary key.
- `name` (STRING): Visit display / autonumber name.
- `account_id` (STRING): FK to Account (business or person account being visited).
- `place_id` (STRING): Polymorphic place of the visit (Address, ContactPointAddress, Location, RetailStore).
- `visit_type_id` (STRING): Polymorphic visit type; commonly Work Type (`work_type.id`).
- `parent_visit_id` (STRING): Optional parent Visit for grouped / child visits (Life Sciences CE).
- `territory_id` (STRING): Optional Territory2 for the visit.
- `channel` (STRING): Visit channel (default `In-Person`; Life Sciences CE).
- `status` (STRING): `Planned` (default), `InProgress`, `Completed`, `Abandoned`, `Unscheduled`, `Error`, `None`.
- `visit_priority` (STRING): `High`, `Medium`, `Low`.
- `planned_visit_start_time` (TIMESTAMP): Expected start.
- `planned_visit_end_time` (TIMESTAMP): Expected end.
- `actual_visit_start_time` (TIMESTAMP): Actual start when execution begins.
- `actual_visit_end_time` (TIMESTAMP): Actual end when completed.
- `signature_type` (STRING): Signature capture type (Life Sciences CE).
- `context` (STRING): Purpose / context of the visit.
- `owner_id` (STRING): Record owner.

### 2. visitor
Sales reps / service resources executing the visit.
- `id` (STRING): Primary key.
- `name` (STRING): Visitor record name.
- `visit_id` (STRING): FK → `visit.id`.
- `assignee_id` (STRING): Polymorphic assignee (User, ServiceResource, Contact).
- `is_primary_resource` (BOOLEAN): Primary visitor on the visit.
- `is_required` (BOOLEAN): Whether this visitor is required.

### 3. visited_party
Contact person(s) at the account being visited (e.g. surgeon, HCP).
- `id` (STRING): Primary key.
- `name` (STRING): Visited party name.
- `visit_id` (STRING): FK → `visit.id`.
- `contact_id` (STRING): FK → `contact.id`.
- `is_primary_contact` (BOOLEAN): Primary visited party flag.

### 4. assessment_task
Activities performed during a visit (registration, inventory check, order auth, surveys, etc.).
- `id` (STRING): Primary key.
- `name` (STRING): Task identifier.
- `parent_id` (STRING): FK → `visit.id`.
- `assessment_task_definition_id` (STRING): FK to Assessment Task Definition.
- `assigned_to_id` (STRING): Assigned User.
- `task_type` (STRING): e.g. `InventoryCheck`, `PlaceOrder`, `ConductInStoreSurveys`, `PlanogramCheck`, `PromotionCheck`, `Other`.
- `status` (STRING): `NotStarted` (default), `InProgress`, `Completed`, `Skipped`, `Started`.
- `is_required` (BOOLEAN): Must complete to finish the visit.
- `sequence_number` (INT): Execution order.
- `start_time` (TIMESTAMP): When the field rep started the task.
- `end_time` (TIMESTAMP): When the task completed.
- `description` (STRING): Task description.
- `reference_record_id` (STRING): Polymorphic related record (ActionPlan, compliance cycle, etc.).
- `owner_id` (STRING): Owner.

### 5. product_required
Products needed to complete a visit (samples, devices, trays).
- `id` (STRING): Primary key.
- `product_required_number` (STRING): Autonumber.
- `parent_record_id` (STRING): Parent Visit (or Work Order / Work Order Line Item).
- `parent_record_type` (STRING): Parent object type discriminator.
- `product2_id` (STRING): FK → `product2.id`.
- `product_name` (STRING): Denormalized product name.
- `quantity_required` (DOUBLE): Required quantity.
- `quantity_unit_of_measure` (STRING): UoM (often `Each`).

### 6. work_type
Visit type catalog (used via `visit.visit_type_id`).
- `id` (STRING): Primary key.
- `name` (STRING): Work / visit type name.
- `estimated_duration` (DOUBLE): Optional duration.
- `should_auto_create_svc_appt` (BOOLEAN): Optional automation flag.

### 7. product2
Sellable / inventoriable product catalog.
- `id` (STRING): Primary key.
- `name` (STRING): Product name.
- `product_code` (STRING): Product code.
- `stock_keeping_unit` (STRING): SKU.
- `family` (STRING): Product family picklist.
- `description` (STRING): Product description.
- `is_active` (BOOLEAN): Active flag.
- `is_serialized` (BOOLEAN): Supports serial numbers.
- `quantity_unit_of_measure` (STRING): Default UoM (inherited by Product Item).

### 8. product_item
Stock of a product at a location (van, warehouse, plant).
- `id` (STRING): Primary key.
- `product_item_number` (STRING): Autonumber.
- `product2_id` (STRING): FK → `product2.id`.
- `location_id` (STRING): FK → `location.id` (where stock sits).
- `quantity_on_hand` (DOUBLE): Current qty (must be 1 if adding a serial number).
- `quantity_unit_of_measure` (STRING): UoM.
- `is_product2_serialized` (BOOLEAN): Serialized product flag.
- `serial_number` (STRING): Optional serial when qty is 1.
- `product_name` (STRING): Denormalized name.
- `owner_id` (STRING): Owner.

### 9. product_transfer
Movement of inventory between locations (often fulfilling a Product Request).
- `id` (STRING): Primary key.
- `product_transfer_number` (STRING): Autonumber.
- `product2_id` (STRING): FK → `product2.id`.
- `source_location_id` (STRING): FK → `location.id` (from).
- `destination_location_id` (STRING): FK → `location.id` (to).
- `source_product_item_id` (STRING): FK → `product_item.id` at source.
- `product_request_id` (STRING): Optional FK → `product_request.id`.
- `product_request_line_item_id` (STRING): Optional FK → `product_request_line_item.id`.
- `quantity_sent` (DOUBLE): Qty sent.
- `quantity_received` (DOUBLE): Qty received.
- `is_sent` (BOOLEAN): Sent flag.
- `is_received` (BOOLEAN): Received flag (irreversible once set).
- `is_product2_serialized` (BOOLEAN): Serialized transfer.
- `status` (STRING): Transfer status.
- `expected_pickup_date` (TIMESTAMP): Expected pickup.
- `description` (STRING): Notes.
- `owner_id` (STRING): Owner.

### 10. product_request
Request for product / device / sample (often created from shortfall on a visit).
- `id` (STRING): Primary key.
- `product_request_number` (STRING): Autonumber / name.
- `status` (STRING): Request lifecycle status.
- `need_by_date` (DATE): When product is needed.
- `ship_to_address` / destination fields as landed in UC.
- `owner_id` (STRING): Requester / owner.

### 11. product_request_line_item
Line-level request detail; junction toward Product Transfer.
- `id` (STRING): Primary key.
- `product_request_id` (STRING): FK → `product_request.id`.
- `product2_id` (STRING): FK → `product2.id`.
- `quantity_requested` (DOUBLE): Requested qty.
- `quantity_unit_of_measure` (STRING): UoM.
- `need_by_date` (DATE): Line need-by.

### 12. product_fulfillment_location
Associates a business account + product inventory location with the responsible field rep.
Must align with Visit (same visitor/product/account/account-location/inventory-location combo)
before scheduling.
- `id` (STRING): Primary key.
- `name` (STRING): Record name.
- `account_id` (STRING): Business account the rep covers.
- `location_id` (STRING): Account visit location.
- `fulfillment_location_id` (STRING): Inventory location that fulfills orders.
- `product_id` (STRING): FK → `product2.id` fulfilled at the account.
- `user_id` (STRING): Field rep responsible.

### 13. product_availability_projection
Projected on-hand qty at an inventory location over time (auto-created by Intelligent Sales).
- `id` (STRING): Primary key.
- `name` (STRING): Record name.
- `product2_id` (STRING): FK → `product2.id`.
- `product_location_id` (STRING): FK → `location.id` (inventory location).
- `projection_date` (DATE): Date the projection applies.
- `projected_quantity` (DOUBLE): Projected available quantity.
- `status` (STRING): `Available`, `ProjectedAvailable`, `Shortfall`.
- `owner_id` (STRING): Owner.

### 14. serialized_product
Individual serial-numbered units in inventory.
- `id` (STRING): Primary key.
- `serial_number` (STRING): Unique serial.
- `product2_id` (STRING): FK → `product2.id`.
- `product_item_id` (STRING): FK → `product_item.id` when assigned to a stock record.
- `status` (STRING): Serialization / custody status as landed.

### 15. location
Inventory or visit place (Warehouse, Site, Van, Plant, …).
- `id` (STRING): Primary key.
- `name` (STRING): Location name.
- `location_type` (STRING): e.g. `Warehouse`, `Site`, `Van`, `Plant`.
- `parent_location_id` (STRING): Optional parent location.
- Address / geo fields as landed (`street`, `city`, `state`, `postal_code`, `country`, `latitude`, `longitude`).

### 16. account
Salesforce Account. Carries **both** roles in this model — provider organizations (business
accounts) and person accounts. Split on `is_person_account` rather than ingesting twice.
- `id` (STRING): Unique ID of the account (Primary Key).
- `name` (STRING): Account name — organization name for business accounts, full name for person accounts.
- `is_person_account` (BOOLEAN): True for person accounts, false for business accounts.
- `type` (STRING): Account type classification (e.g., provider, hospital, clinic).
- `industry` (STRING): Industry classification of the organization.
- `phone` (STRING): Primary phone number.
- `billing_state` (STRING): State of the account's primary address.
- `billing_postal_code` (STRING): Postal code of the account's primary address.
- `billing_country` (STRING): Country of the account's primary address.
- `owner_id` (STRING): The ID of the user who owns this record.

### 17. contact
Contact person at a provider account — typically the HCP referenced by `visited_party`.
- `id` (STRING): Unique ID of the contact (Primary Key).
- `name` (STRING): Full name of the contact.
- `first_name` (STRING): Given name.
- `last_name` (STRING): Family name.
- `account_id` (STRING): FK → `account.id` (the provider organization the contact belongs to).
- `title` (STRING): Job title / specialty.
- `email` (STRING): Email address.
- `phone` (STRING): Phone number.
- `mailing_state` (STRING): State of the mailing address.
- `mailing_postal_code` (STRING): Postal code of the mailing address.
- `owner_id` (STRING): The ID of the user who owns this record.

---

## Join paths

Visit execution hierarchy:
`visit` → `visitor` (`visit_id`) / `visited_party` (`visit_id`) → `assessment_task` (`parent_id`)
→ `product_required` (`parent_record_id` = visit). Visit type via `visit.visit_type_id → work_type.id`.
Account via `visit.account_id → account.id`. HCP detail via `visited_party.contact_id → contact.id`.

Inventory & fulfillment hierarchy:
`product_fulfillment_location` → `product_item` → `product_availability_projection`
→ on shortfall: `product_request` → `product_request_line_item` → `product_transfer`
→ `serialized_product` when `product2.is_serialized`. Location joins on
`product_item.location_id`, `product_transfer.source_location_id` /
`destination_location_id`, and `product_availability_projection.product_location_id`.

---

## Example queries

### Example 1 — Completed visits with primary HCP and products required
```sql
SELECT
    v.name AS visit_name,
    v.status,
    v.planned_visit_start_time,
    v.actual_visit_start_time,
    v.actual_visit_end_time,
    a.name AS account_name,
    vp.name AS visited_party_name,
    p2.name AS product_required_name,
    pr.quantity_required,
    pr.quantity_unit_of_measure
FROM visit v
LEFT JOIN account a ON a.id = v.account_id
LEFT JOIN visited_party vp
  ON vp.visit_id = v.id AND vp.is_primary_contact = true
LEFT JOIN product_required pr
  ON pr.parent_record_id = v.id
LEFT JOIN product2 p2
  ON p2.id = pr.product2_id
WHERE v.status = 'Completed';
```

### Example 2 — Visit counts by status and type (metric view)
```sql
SELECT
    `Visit Status`,
    `Visit Type`,
    MEASURE(`Visit Count`) AS visit_count,
    MEASURE(`Completed Visit Count`) AS completed_visit_count
FROM <catalog>.<schema>.visit_execution_metrics
GROUP BY ALL
ORDER BY ALL;
```

### Example 3 — Inventory shortfalls by product and location (metric view)
```sql
SELECT
    `Product Name`,
    `Inventory Location`,
    `Projection Date`,
    MEASURE(`Projected Quantity`) AS projected_quantity,
    MEASURE(`Shortfall Count`) AS shortfall_count
FROM <catalog>.<schema>.inventory_availability_metrics
WHERE `Availability Status` = 'Shortfall'
GROUP BY ALL
ORDER BY ALL;
```

### Example 4 — Open product transfers tied to requests
```sql
SELECT
    pt.product_transfer_number,
    p2.name AS product_name,
    src.name AS source_location,
    dst.name AS destination_location,
    pt.quantity_sent,
    pt.quantity_received,
    pt.is_sent,
    pt.is_received,
    pt.status,
    pr.product_request_number
FROM product_transfer pt
JOIN product2 p2 ON p2.id = pt.product2_id
LEFT JOIN location src ON src.id = pt.source_location_id
LEFT JOIN location dst ON dst.id = pt.destination_location_id
LEFT JOIN product_request pr ON pr.id = pt.product_request_id
WHERE pt.is_received = false;
```

### Example 5 — Visit task completion for a field rep
```sql
SELECT
    v.name AS visit_name,
    vis.name AS visitor_name,
    at.task_type,
    at.status AS task_status,
    at.is_required,
    at.sequence_number
FROM visit v
JOIN visitor vis ON vis.visit_id = v.id AND vis.is_primary_resource = true
JOIN assessment_task at ON at.parent_id = v.id
WHERE v.planned_visit_start_time >= CURRENT_DATE() - INTERVAL 30 DAYS
ORDER BY v.planned_visit_start_time, at.sequence_number;
```
