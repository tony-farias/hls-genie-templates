# HEDIS Quality Measures — Lakeflow ingestion demo

A runnable, self-contained demo that lands a HEDIS/CMS quality-measure star schema in
Unity Catalog from **two sources**, exactly mirroring the app's **Quality · HEDIS Measures**
tab:

| Source | What | How |
|--------|------|-----|
| 🟢 **HEDIS files** | `fact_claims`, `fact_enrollment` | CSV shards landed in a UC Volume, read with **Auto Loader** (`cloudFiles`) in a Lakeflow pipeline |
| 🔵 **Salesforce Data Cloud** | `dim_member`, `dim_provider` | Read from the `salesforce_datacloud` schema (mock of a Data Cloud **zero-copy** foreign catalog) |
| 🟣 **Computed** | `fact_quality_events`, `mv_quality_performance` | HEDIS numerator/denominator gap logic + measure-rate rollup in the pipeline |
| ⚪ **Reference** | `dim_measure`, `dim_county` | Static seed tables (18 HEDIS/CMS measures) |

> The Salesforce Data Cloud dimensions are **mocked as UC tables** so the demo needs no live
> Data Cloud org. In production, `salesforce_datacloud` becomes a foreign catalog federated
> from Salesforce Data Cloud via zero-copy — the pipeline code does not change, only the
> `spark.hedis.datacloud_schema` target.

## Files

```
generate_hedis_files.py   synth HEDIS files + Data Cloud/reference seeds (stdlib, seed=42)
00_setup.sql              schemas + landing Volume
10_datacloud_dims.sql     load dim_member / dim_provider / dim_measure (Data Cloud + ref)
hedis_pipeline.py         Lakeflow Declarative Pipeline (Auto Loader → bronze → gold star + measures)
config.sh                 target catalog/schema/volume/profile/warehouse
run_demo.sh               one-command end-to-end runner
```

## Run

```bash
cd demos/hedis-quality
# 1. authenticate the CLI to the fe-hls workspace
databricks auth login --profile fe-vm-hls-amer
# 2. set a SQL warehouse id (for the *.sql steps) and any target overrides
export WAREHOUSE_ID=<sql_warehouse_id>
# optional: CATALOG=main SCHEMA=hedis_quality_demo DC_SCHEMA=salesforce_datacloud
./run_demo.sh
```

`run_demo.sh` generates the data, creates the schemas + Volume, uploads the files, loads
the Data Cloud dimensions, then creates and runs the Lakeflow pipeline. Output tables land
in `${CATALOG}.${SCHEMA}`:

- `fact_claims`, `fact_enrollment` — gold facts from the HEDIS files
- `fact_quality_events` — computed per member × measure (in_denominator / in_numerator)
- `mv_quality_performance` — denominator, numerator, `compliance_rate` vs `regulatory_threshold`

## Verify

```sql
-- measure performance leaderboard
SELECT measure_id, measure_name, denominator, numerator, compliance_rate,
       regulatory_threshold, meets_threshold
FROM tony_farias.hedis_quality_demo.mv_quality_performance
ORDER BY compliance_rate DESC;

-- confirm dims came from "Data Cloud"
DESCRIBE DETAIL tony_farias.salesforce_datacloud.member;   -- see the zero-copy comment
```

## Notes on the "real" Lakeflow connector choice

There is no single "claims" connector — you pick by where claims live:

- **Files** (EDI X12 837/835, CSV, Parquet in S3/ADLS) → **Auto Loader / Lakeflow file ingestion** (what this demo shows).
- **A claims/EDW database** (SQL Server, Oracle, Postgres) → **Lakeflow Connect database connector**.
- **Salesforce** operational objects → **Lakeflow Connect Salesforce connector**.

Salesforce holds the operational layer (members, providers, claims, enrollment); the HEDIS
quality-measure layer (`dim_measure`, `fact_quality_events`, `mv_quality_performance`) is a
Databricks computation, which is why it is built in the pipeline rather than sourced.
