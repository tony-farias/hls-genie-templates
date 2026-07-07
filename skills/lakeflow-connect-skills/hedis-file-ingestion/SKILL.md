---
name: hedis-file-ingestion
description: Ingest a HEDIS/CMS quality-measure star schema into Unity Catalog — claims & enrollment from HEDIS files via Auto Loader, member/provider dimensions from Salesforce Data Cloud (zero-copy), plus computed quality events and measure performance. Use when building or running the "Quality · HEDIS Measures" demo, adding file-based (Auto Loader) claims ingestion, wiring Salesforce Data Cloud dimensions, or standing up the demos/hedis-quality Lakeflow pipeline.
---

# HEDIS file ingestion (Lakeflow)

Builds the HEDIS Quality Measures model behind the app's **Quality · HEDIS Measures** tab.
Full implementation lives in [`demos/hedis-quality/`](../../../demos/hedis-quality/).

## When to use
- Demoing **file-based Lakeflow ingestion** (Auto Loader / `cloudFiles`) for claims data.
- Showing **Salesforce Data Cloud** dimensions joined to file-sourced facts.
- Standing up / re-running the `hls-hedis-quality` Lakeflow pipeline in `fe-hls`.

## Source → connector mapping (claims data)
There is no dedicated "claims" connector. Choose by source:

| Claims source | Connector |
|---|---|
| EDI X12 837/835, CSV, Parquet in S3/ADLS | **Auto Loader / Lakeflow file ingestion** ← this demo |
| Claims adjudication / EDW database | Lakeflow Connect **database** connector (SQL Server GA) |
| Salesforce operational objects | Lakeflow Connect **Salesforce** connector |

The HEDIS quality layer (`dim_measure`, `fact_quality_events`, `mv_quality_performance`)
is a **Databricks computation**, not a sourced table — build it in the pipeline.

## How to run
```bash
cd demos/hedis-quality
databricks auth login --profile fe-vm-hls-amer
export WAREHOUSE_ID=<sql_warehouse_id>
./run_demo.sh
```
See `demos/hedis-quality/README.md` for the full walkthrough and verification queries.

## Architecture
```
HEDIS files ─(Auto Loader)→ bronze_claims / bronze_enrollment ┐
                                                              ├─→ fact_* (gold star) → mv_quality_performance
Salesforce Data Cloud ─(zero-copy)→ dim_member / dim_provider ┘
```
- `spark.hedis.landing_path` — Volume the pipeline watches for files.
- `spark.hedis.datacloud_schema` — schema standing in for the Data Cloud foreign catalog
  (swap to a real zero-copy foreign catalog with no pipeline code change).
