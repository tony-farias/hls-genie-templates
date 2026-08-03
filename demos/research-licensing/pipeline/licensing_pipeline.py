"""In-Licensing Package — Lakeflow Declarative Pipeline (DLT).

Lands a mixed-format BD&L due-diligence data room from a UC Volume into Unity Catalog,
turning a messy SharePoint-style package (docs + tables) into governed, queryable tables
ready for Genie Ontology and agent tooling. This is the "IP knowledge transfer on
licensing with Lakeflow + Genie Ontology" story.

Two ingest streams, both via Auto Loader (cloudFiles) over the landing Volume:

  UNSTRUCTURED  .md/.txt docs (term sheet, memos, narratives)
                -> bronze_documents : one row per doc, full text + path-derived metadata
                   (this is what you'd chunk + embed for Genie / vector search)

  STRUCTURED    .csv tables (assays, PK/PD, tox, stability, IP, manifest)
                -> per-domain silver tables, typed

  gold_dataroom_index  : the manifest joined to what actually landed — a single
                         governed catalog of the data room for due-diligence tracking.

Pipeline config params (set in the pipeline settings / run_demo.sh):
  spark.licensing.landing_path   /Volumes/<cat>/<schema>/<vol>/data_room
Target catalog/schema come from the pipeline's own settings.
"""
import dlt
from pyspark.sql import functions as F

LANDING = spark.conf.get("spark.licensing.landing_path")

# --------------------------------------------------------------------------- #
# UNSTRUCTURED — documents (whole-text ingest, ready for chunk/embed)
# --------------------------------------------------------------------------- #
@dlt.table(
    comment="Raw due-diligence documents (md/txt) ingested whole-file via Auto Loader. "
            "Full text + data-room metadata; the input to Genie Ontology / vector search.",
    table_properties={"source": "data-room-docs", "layer": "bronze"},
)
def bronze_documents():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "text")
        .option("wholeText", "true")                      # one row per file
        .option("cloudFiles.schemaHints", "value string")
        .load(f"{LANDING}")
        .withColumn("path", F.col("_metadata.file_path"))
        .filter(F.col("path").rlike(r"\.(md|txt)$"))
        .withColumn("doc_text", F.col("value"))
        .withColumn("section", F.regexp_extract("path", r"data_room/([^/]+)/", 1))
        .withColumn("filename", F.regexp_extract("path", r"/([^/]+)$", 1))
        .withColumn("word_count", F.size(F.split(F.col("doc_text"), r"\s+")))
        .withColumn("_ingested_at", F.current_timestamp())
        .select("path", "section", "filename", "word_count", "doc_text", "_ingested_at")
    )


# --------------------------------------------------------------------------- #
# STRUCTURED — CSV tables, one Auto Loader stream, split by filename
# --------------------------------------------------------------------------- #
def _csv_stream():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .option("cloudFiles.inferColumnTypes", "true")
        .load(f"{LANDING}")
        .withColumn("path", F.col("_metadata.file_path"))
    )


@dlt.table(comment="In vitro assay results (structured).", table_properties={"layer": "silver"})
def silver_assay_results():
    return (_csv_stream().filter(F.col("path").endswith("assay_results.csv"))
            .select("compound", "assay", "replicate", "value", "note"))


@dlt.table(comment="Rodent PK/PD parameters (structured).", table_properties={"layer": "silver"})
def silver_pk_pd():
    return (_csv_stream().filter(F.col("path").endswith("pk_pd.csv"))
            .select("compound", "species", "dose_mpk", "cmax_uM", "auc", "t_half_h", "bioavail_pct"))


@dlt.table(comment="GLP tox summary (structured).", table_properties={"layer": "silver"})
def silver_tox_summary():
    return (_csv_stream().filter(F.col("path").endswith("tox_summary.csv"))
            .select("compound", "species", "study", "dose_mpk", "finding", "histopath"))


@dlt.table(comment="CMC stability (structured).", table_properties={"layer": "silver"})
def silver_stability():
    return (_csv_stream().filter(F.col("path").endswith("stability.csv"))
            .select("compound", "material", "condition", "timepoint_month",
                    "purity_pct", "total_impurities_pct"))


@dlt.table(comment="Patent family (structured).", table_properties={"layer": "silver"})
def silver_patent_family():
    return (_csv_stream().filter(F.col("path").endswith("patent_family.csv"))
            .select("application_no", "type", "filing_date", "status", "note"))


@dlt.table(comment="Data-room manifest as delivered by the licensor.", table_properties={"layer": "bronze"})
def bronze_manifest():
    return (_csv_stream().filter(F.col("path").endswith("manifest.csv"))
            .select("path", "content_kind", "size_or_rows", "program", "asset"))


# --------------------------------------------------------------------------- #
# GOLD — governed data-room index (manifest vs what actually landed)
# --------------------------------------------------------------------------- #
@dlt.table(
    comment="Gold: the licensor manifest reconciled with ingested artifacts — a governed, "
            "queryable index of the entire due-diligence data room.",
    table_properties={"layer": "gold"},
)
def gold_dataroom_index():
    man = dlt.read("bronze_manifest").withColumn(
        "rel_path", F.regexp_extract("path", r"(data_room/.*)$", 1))
    docs = dlt.read("bronze_documents").withColumn(
        "rel_path", F.regexp_extract("path", r"(data_room/.*)$", 1)
    ).select("rel_path", F.lit(True).alias("landed_as_doc"), "word_count")
    return (
        man.join(docs, "rel_path", "left")
           .withColumn("ingested", F.when(F.col("content_kind") == "doc",
                                           F.col("landed_as_doc").isNotNull())
                                     .otherwise(F.lit(True)))
           .select("program", "asset", "rel_path", "content_kind",
                   "size_or_rows", "word_count", "ingested")
    )
