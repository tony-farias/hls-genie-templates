---
name: life-sciences-intelligent-sales
description: Schema definitions, Unity Catalog column comments, metric view definitions, and example join queries for the Salesforce Life Sciences Intelligent Sales data model (provider visits, field inventory, product transfers), and the end-to-end workflow for grounding a Databricks Genie space over it. Use when a user asks to "create life sciences intelligent sales genie template" (or to create, build, or generate a Life Sciences Intelligent Sales Genie template, space, or room), and whenever a user asks about sales visits to providers, visitors, visited parties, assessment tasks, product items, product transfers, product requests, product required, fulfillment locations, availability projections, or serialized field inventory.
---

# Salesforce Life Sciences Intelligent Sales Skill

This skill provides production-ready schema structures, column semantics, relationship mappings,
and governed metric definitions for Databricks Genie to query medical sales visits and field
inventory data from the Salesforce Life Sciences Intelligent Sales model (ingested via Lakeflow
Connect or similar).

**Canonical docs:**
- [Intelligent Sales data model (Life Sciences)](https://developer.salesforce.com/docs/atlas.en-us.life_sciences_dev_guide.meta/life_sciences_dev_guide/hc_intelligent_sales_data_model.htm)
- [Data Model Gallery — Intelligent Sales](https://developer.salesforce.com/docs/platform/data-models/guide/intelligent-sales.html)

## Genie template workflow

When asked to create the Life Sciences Intelligent Sales Genie template, work through the steps
below in order. Each layer carries a different kind of knowledge — keep them separate.

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
COMMENT ON TABLE <catalog>.<schema>.visit IS
  'Field rep visit to a healthcare provider or account (Salesforce Life Sciences Visit).';

ALTER TABLE <catalog>.<schema>.visit ALTER COLUMN status
  COMMENT 'Visit lifecycle status: Planned, InProgress, Completed, Abandoned, Unscheduled, Error, None.';
```

Escape single quotes inside a comment by doubling them (`''`). Verify with
`DESCRIBE TABLE EXTENDED <catalog>.<schema>.visit`.

## Full object catalog (from the data model)

Action Plan, Action Plan Item, Action Plan Template, Action Plan Template Item,
Assessment Indicator Definition, Assessment Task, Assessment Task Order, Asset,
Business Account, Care Registered Device, Contact, Digital Signature,
Generic Visit Key Performance Indicator, Generic Visit Task, Generic Visit Task Context,
Generic Visit Task Context Relation, Location, Order, Person Account,
Product Availability Projection, Product Fulfillment Location, Product Item,
Product Item Transaction, Product Request, Product Request Line Item, Product Required,
Product Transfer, Product2, Record Action, Serialized Product, Service Resources, User,
Visit, Visit Task Interface, Visited Party, Visitor, Work Type.

## Table Schemas & Column Metadata

Use snake_case table/column names below as the UC landing shape after Lakeflow Connect.
Salesforce API names are PascalCase (`Visit`, `AccountId`, …); map `FooId` → `foo_id`.

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
- `contact_id` (STRING): FK → Contact.
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

### 6. product2
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

### 7. product_item
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

### 8. product_transfer
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

### 9. product_request
Request for product / device / sample (often created from shortfall on a visit).
- `id` (STRING): Primary key.
- `product_request_number` (STRING): Autonumber / name.
- `status` (STRING): Request lifecycle status.
- `need_by_date` (DATE): When product is needed.
- `ship_to_address` / destination fields as landed in UC.
- `owner_id` (STRING): Requester / owner.

### 10. product_request_line_item
Line-level request detail; junction toward Product Transfer.
- `id` (STRING): Primary key.
- `product_request_id` (STRING): FK → `product_request.id`.
- `product2_id` (STRING): FK → `product2.id`.
- `quantity_requested` (DOUBLE): Requested qty.
- `quantity_unit_of_measure` (STRING): UoM.
- `need_by_date` (DATE): Line need-by.

### 11. product_fulfillment_location
Associates a business account + product inventory location with the responsible field rep.
Must align with Visit (same visitor/product/account/account-location/inventory-location combo) before scheduling.
- `id` (STRING): Primary key.
- `name` (STRING): Record name.
- `account_id` (STRING): Business account the rep covers.
- `location_id` (STRING): Account visit location.
- `fulfillment_location_id` (STRING): Inventory location that fulfills orders.
- `product_id` (STRING): FK → `product2.id` fulfilled at the account.
- `user_id` (STRING): Field rep responsible.

### 12. product_availability_projection
Projected on-hand qty at an inventory location over time (auto-created by Intelligent Sales).
- `id` (STRING): Primary key.
- `name` (STRING): Record name.
- `product2_id` (STRING): FK → `product2.id`.
- `product_location_id` (STRING): FK → `location.id` (inventory location).
- `projection_date` (DATE): Date the projection applies.
- `projected_quantity` (DOUBLE): Projected available quantity.
- `status` (STRING): `Available`, `ProjectedAvailable`, `Shortfall`.
- `owner_id` (STRING): Owner.

### 13. serialized_product
Individual serial-numbered units in inventory.
- `id` (STRING): Primary key.
- `serial_number` (STRING): Unique serial.
- `product2_id` (STRING): FK → `product2.id`.
- `product_item_id` (STRING): FK → `product_item.id` when assigned to a stock record.
- `status` (STRING): Serialization / custody status as landed.

### 14. location
Inventory or visit place (Warehouse, Site, Van, Plant, …).
- `id` (STRING): Primary key.
- `name` (STRING): Location name.
- `location_type` (STRING): e.g. `Warehouse`, `Site`, `Van`, `Plant`.
- `parent_location_id` (STRING): Optional parent location.
- Address / geo fields as landed (`street`, `city`, `state`, `postal_code`, `country`, `latitude`, `longitude`).

### 15. work_type
Visit type catalog (used via `visit.visit_type_id`).
- `id` (STRING): Primary key.
- `name` (STRING): Work / visit type name.
- `estimated_duration` (DOUBLE): Optional duration.
- `should_auto_create_svc_appt` (BOOLEAN): Optional automation flag.

---

## Step 2 — Metric views

Build the governed KPI layer before creating the space. Carry the business meaning in each
dimension's and measure's `comment` (and `synonyms` on DBR 17.3+) — that metadata is what
Genie reads, so it does not need to be repeated as instructions.

### `visit_execution_metrics` — visit and task rollups
```sql
CREATE OR REPLACE VIEW <catalog>.<schema>.visit_execution_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: <catalog>.<schema>.visit
  comment: "Provider visit execution KPIs by status, channel, priority, and visit type."
  joins:
    - name: work_type
      source: <catalog>.<schema>.work_type
      on: source.visit_type_id = work_type.id
  dimensions:
    - name: Visit Status
      expr: source.status
      comment: "Visit lifecycle status: Planned, InProgress, Completed, Abandoned, Unscheduled, Error, None."
    - name: Channel
      expr: source.channel
      comment: "Visit channel, typically In-Person."
    - name: Visit Priority
      expr: source.visit_priority
      comment: "Visit priority: High, Medium, Low."
    - name: Visit Type
      expr: work_type.name
      comment: "Work / visit type name from the work type catalog."
    - name: Planned Visit Month
      expr: DATE_TRUNC('MONTH', source.planned_visit_start_time)
      comment: "Month of the planned visit start."
  measures:
    - name: Visit Count
      expr: COUNT(1)
      comment: "Number of visit records."
    - name: Completed Visit Count
      expr: COUNT(CASE WHEN source.status = 'Completed' THEN 1 END)
      comment: "Visits with status Completed."
    - name: In Progress Visit Count
      expr: COUNT(CASE WHEN source.status = 'InProgress' THEN 1 END)
      comment: "Visits currently in progress."
    - name: Avg Planned Duration Hours
      expr: AVG(TIMESTAMPDIFF(HOUR, source.planned_visit_start_time, source.planned_visit_end_time))
      comment: "Average planned visit duration in hours."
$$
```

### `inventory_availability_metrics` — stock, shortfalls, and transfers
```sql
CREATE OR REPLACE VIEW <catalog>.<schema>.inventory_availability_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: <catalog>.<schema>.product_availability_projection
  comment: "Projected product availability and shortfalls by inventory location and product."
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
      comment: "Sellable / inventoriable product name."
    - name: Product Family
      expr: product2.family
      comment: "Product family picklist."
    - name: Inventory Location
      expr: location.name
      comment: "Inventory location where the projection applies."
    - name: Location Type
      expr: location.location_type
      comment: "Location type: Warehouse, Site, Van, Plant, etc."
    - name: Projection Date
      expr: source.projection_date
      comment: "Date the quantity projection applies."
    - name: Availability Status
      expr: source.status
      comment: "Projection status: Available, ProjectedAvailable, Shortfall."
  measures:
    - name: Projected Quantity
      expr: SUM(source.projected_quantity)
      comment: "Projected available quantity at the inventory location."
    - name: Shortfall Count
      expr: COUNT(CASE WHEN source.status = 'Shortfall' THEN 1 END)
      comment: "Number of shortfall projection rows."
    - name: Available Count
      expr: COUNT(CASE WHEN source.status = 'Available' THEN 1 END)
      comment: "Number of available projection rows."
$$
```

---

## Step 3 — Genie space sources

Give the space the **metric views first**. Add underlying tables only for questions the
metric views cannot answer — row-level lookups such as a specific visit, visitor, transfer,
or serial number.

- **Default set:** `visit_execution_metrics`, `inventory_availability_metrics`
- **Add for record-level detail:** `visit`, `visitor`, `visited_party`, `assessment_task`,
  `product_transfer`, `product_request`, `serialized_product`
- **Do not** add every underlying table alongside the metric views by default. Duplicate query
  paths over the same facts create ambiguity and let Genie aggregate inconsistently.

---

## Step 4 — Example queries

Join paths belong here, as working SQL, not in instructions. Register these as the space's
example queries / benchmarks so Genie learns the join hierarchy from queries that run.

Visit execution hierarchy:
`visit` → `visitor` (`visit_id`) / `visited_party` (`visit_id`) → `assessment_task` (`parent_id`)
→ `product_required` (`parent_record_id` = visit)

Inventory & fulfillment hierarchy:
`product_fulfillment_location` → `product_item` → `product_availability_projection`
→ on shortfall: `product_request` → `product_request_line_item` → `product_transfer`
→ `serialized_product` when `product2.is_serialized`

### Example 1 — Completed visits with primary HCP and products required
```sql
SELECT
    v.name AS visit_name,
    v.status,
    v.planned_visit_start_time,
    v.actual_visit_start_time,
    v.actual_visit_end_time,
    vp.name AS visited_party_name,
    p2.name AS product_required_name,
    pr.quantity_required,
    pr.quantity_unit_of_measure
FROM visit v
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

---

## Step 5 — Instructions

Instructions are for **company-wide business context only** — the things no amount of schema
metadata can convey:

- official definitions (what counts as a "completed visit" or "shortfall")
- fiscal or territory reporting conventions
- authoritative source precedence when systems disagree
- privacy and exclusion rules
- approved terminology and reporting/rounding policy

Take these from the user. **Do not invent them, and do not put join logic, table routing, or
metric-view selection into instructions** — those belong in the metric view metadata (step 2),
the source selection (step 3), and the example queries (step 4). If the user supplies no
company-wide context, leave the instructions empty.
