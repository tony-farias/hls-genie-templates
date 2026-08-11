# Life Sciences Intelligent Sales — column reference

Semantic column definitions for the 17 ingested tables. Salesforce lands the **physical**
columns in API casing (`Id`, `Name`, `PlannedVisitStartTime`, `QuantityOnHand`), so reconcile
names with `DESCRIBE TABLE` before writing SQL — see step 6 of [SKILL.md](SKILL.md).

Use these descriptions as the text for the `COMMENT ON TABLE` / `ALTER COLUMN ... COMMENT`
statements in step 7.

## 1. visit
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

## 2. visitor
Sales reps / service resources executing the visit.
- `id` (STRING): Primary key.
- `name` (STRING): Visitor record name.
- `visit_id` (STRING): FK → `visit.id`.
- `assignee_id` (STRING): Polymorphic assignee (User, ServiceResource, Contact).
- `is_primary_resource` (BOOLEAN): Primary visitor on the visit.
- `is_required` (BOOLEAN): Whether this visitor is required.

## 3. visited_party
Contact person(s) at the account being visited (e.g. surgeon, HCP).
- `id` (STRING): Primary key.
- `name` (STRING): Visited party name.
- `visit_id` (STRING): FK → `visit.id`.
- `contact_id` (STRING): FK → `contact.id`.
- `is_primary_contact` (BOOLEAN): Primary visited party flag.

## 4. assessment_task
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

## 5. product_required
Products needed to complete a visit (samples, devices, trays).
- `id` (STRING): Primary key.
- `product_required_number` (STRING): Autonumber.
- `parent_record_id` (STRING): Parent Visit (or Work Order / Work Order Line Item).
- `parent_record_type` (STRING): Parent object type discriminator.
- `product2_id` (STRING): FK → `product2.id`.
- `product_name` (STRING): Denormalized product name.
- `quantity_required` (DOUBLE): Required quantity.
- `quantity_unit_of_measure` (STRING): UoM (often `Each`).

## 6. work_type
Visit type catalog (used via `visit.visit_type_id`).
- `id` (STRING): Primary key.
- `name` (STRING): Work / visit type name.
- `estimated_duration` (DOUBLE): Optional duration.
- `should_auto_create_svc_appt` (BOOLEAN): Optional automation flag.

## 7. product2
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

## 8. product_item
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

## 9. product_transfer
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

## 10. product_request
Request for product / device / sample (often created from shortfall on a visit).
- `id` (STRING): Primary key.
- `product_request_number` (STRING): Autonumber / name.
- `status` (STRING): Request lifecycle status.
- `need_by_date` (DATE): When product is needed.
- `ship_to_address` / destination fields as landed in UC.
- `owner_id` (STRING): Requester / owner.

## 11. product_request_line_item
Line-level request detail; junction toward Product Transfer.
- `id` (STRING): Primary key.
- `product_request_id` (STRING): FK → `product_request.id`.
- `product2_id` (STRING): FK → `product2.id`.
- `quantity_requested` (DOUBLE): Requested qty.
- `quantity_unit_of_measure` (STRING): UoM.
- `need_by_date` (DATE): Line need-by.

## 12. product_fulfillment_location
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

## 13. product_availability_projection
Projected on-hand qty at an inventory location over time (auto-created by Intelligent Sales).
- `id` (STRING): Primary key.
- `name` (STRING): Record name.
- `product2_id` (STRING): FK → `product2.id`.
- `product_location_id` (STRING): FK → `location.id` (inventory location).
- `projection_date` (DATE): Date the projection applies.
- `projected_quantity` (DOUBLE): Projected available quantity.
- `status` (STRING): `Available`, `ProjectedAvailable`, `Shortfall`.
- `owner_id` (STRING): Owner.

## 14. serialized_product
Individual serial-numbered units in inventory.
- `id` (STRING): Primary key.
- `serial_number` (STRING): Unique serial.
- `product2_id` (STRING): FK → `product2.id`.
- `product_item_id` (STRING): FK → `product_item.id` when assigned to a stock record.
- `status` (STRING): Serialization / custody status as landed.

## 15. location
Inventory or visit place (Warehouse, Site, Van, Plant, …).
- `id` (STRING): Primary key.
- `name` (STRING): Location name.
- `location_type` (STRING): e.g. `Warehouse`, `Site`, `Van`, `Plant`.
- `parent_location_id` (STRING): Optional parent location.
- Address / geo fields as landed (`street`, `city`, `state`, `postal_code`, `country`, `latitude`, `longitude`).

## 16. account
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

## 17. contact
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
