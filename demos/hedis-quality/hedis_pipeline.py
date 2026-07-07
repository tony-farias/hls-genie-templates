"""HEDIS Quality Measures — Lakeflow Declarative Pipeline (DLT).

Demonstrates the two-source pattern for the hls-data-models HEDIS tab:

  • HEDIS FILES  → ingested from a UC Volume with Auto Loader (cloudFiles).
                   This is the file-based Lakeflow ingestion path (EDI/claims files
                   land in object storage; here CSV shards under /Volumes/.../claims,
                   /Volumes/.../enrollment).

  • DATA CLOUD DIMENSIONS → read from the `salesforce_datacloud` schema, which in a
                   real deployment is a zero-copy foreign catalog federated from
                   Salesforce Data Cloud. Here it is mocked as UC tables (see
                   10_datacloud_dims.sql) so the demo is fully self-contained.

Medallion:
  bronze_*  raw Auto Loader ingest of the HEDIS files (streaming tables)
  dc_*      Data Cloud dimensions (member, provider) — read as-is
  silver_*  typed / cleaned claims + enrollment
  fact_*    gold star-schema facts (claims, enrollment, computed quality events)
  mv_quality_performance  gold measure-rate summary (numerator / denominator / rate)

Pipeline config injects two params (see run_demo.sh / pipeline settings):
  spark.hedis.landing_path   e.g. /Volumes/main/hedis_quality_demo/hedis_landing
  spark.hedis.datacloud_schema  e.g. main.salesforce_datacloud
Target catalog/schema for published tables come from the pipeline's own settings.
"""
import dlt
from pyspark.sql import functions as F

LANDING = spark.conf.get("spark.hedis.landing_path")
DC_SCHEMA = spark.conf.get("spark.hedis.datacloud_schema")

# ----------------------------------------------------------------------------- #
# BRONZE — HEDIS files, read incrementally with Auto Loader (cloudFiles)
# ----------------------------------------------------------------------------- #

def _autoload(subdir, schema_hints):
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .option("cloudFiles.schemaHints", schema_hints)
        .option("cloudFiles.inferColumnTypes", "true")
        .load(f"{LANDING}/{subdir}")
        .withColumn("_ingest_file", F.col("_metadata.file_path"))
        .withColumn("_ingested_at", F.current_timestamp())
    )


@dlt.table(comment="Raw medical claims ingested from HEDIS files via Auto Loader.",
           table_properties={"source": "hedis-files", "layer": "bronze"})
def bronze_claims():
    return _autoload(
        "claims",
        "billed_amount double, paid_amount double, service_date date",
    )


@dlt.table(comment="Raw member-month enrollment spans ingested from HEDIS files via Auto Loader.",
           table_properties={"source": "hedis-files", "layer": "bronze"})
def bronze_enrollment():
    return _autoload("enrollment", "month string")


# ----------------------------------------------------------------------------- #
# DATA CLOUD DIMENSIONS — zero-copy foreign catalog (mocked as UC tables here)
# ----------------------------------------------------------------------------- #

@dlt.table(comment="Member dimension sourced from Salesforce Data Cloud (zero-copy).",
           table_properties={"source": "salesforce-data-cloud", "layer": "dimension"})
def dim_member():
    return (
        spark.read.table(f"{DC_SCHEMA}.member")
        .withColumn("age", F.floor(F.datediff(F.current_date(), F.col("birth_date")) / 365.25))
        .withColumn("chronic_condition_arr", F.split("chronic_conditions", r"\|"))
    )


@dlt.table(comment="Provider dimension sourced from Salesforce Data Cloud (zero-copy).",
           table_properties={"source": "salesforce-data-cloud", "layer": "dimension"})
def dim_provider():
    return spark.read.table(f"{DC_SCHEMA}.provider")


@dlt.table(comment="HEDIS/CMS quality-measure reference.",
           table_properties={"source": "reference", "layer": "dimension"})
def dim_measure():
    return spark.read.table(f"{DC_SCHEMA}.measure")


# ----------------------------------------------------------------------------- #
# SILVER — typed / cleaned facts from the file feeds
# ----------------------------------------------------------------------------- #

@dlt.table(comment="Cleaned, typed claims (PAID only) with exploded dx/proc arrays.")
@dlt.expect_or_drop("valid_member", "member_id IS NOT NULL")
@dlt.expect_or_drop("valid_service_date", "service_date IS NOT NULL")
def silver_claims():
    return (
        dlt.read("bronze_claims")
        .filter(F.col("claim_status") == "PAID")
        .withColumn("dx_arr", F.split("dx_codes", r"\|"))
        .withColumn("proc_arr", F.split("proc_codes", r"\|"))
        .withColumn("service_year", F.year("service_date"))
    )


@dlt.table(comment="Member-months of continuous enrollment per member per year.")
def silver_enrollment():
    return (
        dlt.read("bronze_enrollment")
        .withColumn("month_date", F.to_date(F.concat_ws("-", "month"), "yyyy-MM"))
        .withColumn("measurement_year", F.substring("month", 1, 4).cast("int"))
    )


# ----------------------------------------------------------------------------- #
# GOLD — star-schema facts
# ----------------------------------------------------------------------------- #

@dlt.table(comment="Fact: paid claims joined to Data Cloud member/provider dims.",
           table_properties={"layer": "gold"})
def fact_claims():
    c = dlt.read("silver_claims")
    m = dlt.read("dim_member").select("member_id", "aid_category", "county_fips")
    p = dlt.read("dim_provider").select("provider_npi", "specialty", "provider_type")
    return (
        c.join(m, "member_id", "left")
         .join(p, "provider_npi", "left")
         .select("claim_id", "member_id", "provider_npi", "service_date", "service_year",
                 "claim_type", "dx_codes", "proc_codes", "billed_amount", "paid_amount",
                 "aid_category", "county_fips", "specialty", "provider_type")
    )


@dlt.table(comment="Fact: member-months eligible (denominator base).",
           table_properties={"layer": "gold"})
def fact_enrollment():
    e = dlt.read("silver_enrollment")
    return (
        e.groupBy("member_id", "measurement_year")
         .agg(F.countDistinct("month").alias("enrolled_months"))
         .withColumn("continuously_enrolled", F.col("enrolled_months") >= 11)
    )


@dlt.table(comment="Fact: HEDIS quality events — computed numerator/denominator per member x measure.",
           table_properties={"layer": "gold"})
def fact_quality_events():
    """Simplified HEDIS gaps-in-care logic: a member is in a measure's denominator if
    continuously enrolled and (for condition-specific measures) has the relevant dx;
    in the numerator if a qualifying CPT (screening/test) appears in their claims."""
    claims = dlt.read("silver_claims")
    enr = dlt.read("fact_enrollment").filter(F.col("continuously_enrolled"))

    # member-level claim signals
    sig = claims.groupBy("member_id").agg(
        F.array_distinct(F.flatten(F.collect_list("dx_arr"))).alias("dxs"),
        F.array_distinct(F.flatten(F.collect_list("proc_arr"))).alias("procs"),
    )
    base = enr.join(sig, "member_id", "left")

    def has(col, code):
        return F.array_contains(F.col(col), F.lit(code))

    # (measure_id, denominator_condition, numerator_condition)
    rules = [
        ("CDC-HbA1c", has("dxs", "E11.9"), has("procs", "83036")),
        ("CDC-Eye",   has("dxs", "E11.9"), has("procs", "77067")),
        ("CBP",       has("dxs", "I10"),   has("procs", "99214")),
        ("BCS",       F.lit(True),         has("procs", "77067")),
        ("COL",       F.lit(True),         has("procs", "45378")),
        ("SPD",       has("dxs", "E78.5"), has("procs", "80061")),
        ("AMR",       has("dxs", "J45.909"), has("procs", "99213")),
        ("AMM",       has("dxs", "F32.9"), has("procs", "99214")),
    ]
    parts = []
    for measure_id, denom_cond, num_cond in rules:
        parts.append(
            base.withColumn("measure_id", F.lit(measure_id))
                .withColumn("in_denominator", denom_cond & F.col("dxs").isNotNull())
                .withColumn("in_numerator", num_cond)
                .select("member_id", "measurement_year", "measure_id",
                        "in_denominator", "in_numerator")
        )
    out = parts[0]
    for p in parts[1:]:
        out = out.unionByName(p)
    return out.filter(F.col("in_denominator"))


@dlt.table(comment="Gold: HEDIS measure performance — denominator, numerator, compliance rate vs threshold.",
           table_properties={"layer": "gold"})
def mv_quality_performance():
    qe = dlt.read("fact_quality_events")
    # drop dim_measure's own measurement_year to avoid an ambiguous ref after the join
    dm = dlt.read("dim_measure").select(
        "measure_id", "measure_name", "domain", "regulatory_threshold",
        "star_rating_flag", "high_priority_flag")
    perf = qe.groupBy("measure_id", "measurement_year").agg(
        F.count("*").alias("denominator"),
        F.sum(F.col("in_numerator").cast("int")).alias("numerator"),
    ).withColumn("compliance_rate", F.round(F.col("numerator") / F.col("denominator"), 4))
    return (
        perf.join(dm, "measure_id", "left")
            .withColumn("meets_threshold", F.col("compliance_rate") >= F.col("regulatory_threshold"))
            .select("measure_id", "measure_name", "domain", "measurement_year",
                    "denominator", "numerator", "compliance_rate",
                    "regulatory_threshold", "meets_threshold",
                    "star_rating_flag", "high_priority_flag")
    )
