# Customer deployment architecture

## Runtime

```text
React/Vite SPA
    -> Express REST API
       -> Databricks Statement Execution API -> curated UC layer -> Scintilla feeds
       -> Genie Conversation API             -> page-scoped Genie rooms
       -> Foundation Model endpoint           -> briefs and recommendations
       -> Vector Search (optional)             -> shopper/research notes
       -> Lakebase (optional)                  -> chat, campaigns and action receipts
       -> Multi-Agent Supervisor (optional)    -> routes across Genie rooms
```

## Customer resources

Create resources only after approval:

1. A customer-owned curated schema beside, not inside, the licensed source schema.
2. Serverless SQL warehouse or an approved existing warehouse.
3. Databricks App with environment-specific resource IDs.
4. Genie rooms for sales, demand, e-commerce/inventory, supply chain and measurement as supported by available feeds.
5. Foundation Model endpoint available in the target region.
6. Optional Lakebase database and Vector Search endpoint/index.

## App configuration

Parameterize at minimum:

- `WAREHOUSE_ID`, `CATALOG`, `SCHEMA`
- shared and page-specific `GENIE_SPACE_*` values
- `LLM_MODEL`
- optional `SUPERVISOR_ENDPOINT`
- optional `VECTOR_SEARCH_ENDPOINT`, `VECTOR_SEARCH_INDEX`
- optional `LAKEBASE_HOST`, `LAKEBASE_DB`, `LAKEBASE_USER`

The app runtime receives Databricks OAuth credentials automatically. Mint short-lived tokens for SQL, Genie, Files, model serving and Lakebase. Do not embed a personal access token.

## Validation gates

- Inventory: every enabled capability has source tables and required join/metric columns.
- Data: row counts, latest dates and supplier partitions are nonempty; join fanout is measured.
- API: `/api/health` and every enabled dashboard endpoint return 2xx.
- Genie: suggested prompts produce grounded SQL over allowed tables.
- Security: the app service principal has only required catalog, warehouse, room, endpoint and database permissions.
- UX: disabled capabilities are hidden or clearly labeled; no mock result is presented as live.
- Operations: prebuild `dist/`, warm the warehouse asynchronously and configure bounded caches/timeouts.
