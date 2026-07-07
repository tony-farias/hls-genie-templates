# Shared config for the HEDIS Quality demo. Edit to retarget, then run ./run_demo.sh.
# All values can be overridden via environment before sourcing.

export PROFILE="${PROFILE:-fe-vm-hls-amer}"          # Databricks CLI profile (fe-hls workspace)
export CATALOG="${CATALOG:-tony_farias}"              # target catalog (needs CREATE SCHEMA; 'main' is not writable in fe-hls)
export SCHEMA="${SCHEMA:-hedis_quality_demo}"         # schema for pipeline output + volume
export DC_SCHEMA="${DC_SCHEMA:-salesforce_datacloud}" # schema standing in for the Data Cloud zero-copy catalog
export VOLUME="${VOLUME:-hedis_landing}"              # UC managed volume = the file landing zone
export PIPELINE_NAME="${PIPELINE_NAME:-hls-hedis-quality}"
export WAREHOUSE_ID="${WAREHOUSE_ID:-}"               # SQL warehouse id for the *.sql steps (required)
export HEDIS_OUT_DIR="${HEDIS_OUT_DIR:-/tmp/hedis_demo}"

export VOLUME_ROOT="/Volumes/${CATALOG}/${SCHEMA}/${VOLUME}"
export LANDING_PATH="${VOLUME_ROOT}"                  # claims/ and enrollment/ live directly under here
