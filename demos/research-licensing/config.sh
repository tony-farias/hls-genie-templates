# Shared config for the Research In-Licensing demo. Edit to retarget, then ./run_demo.sh.
export PROFILE="${PROFILE:-fe-vm-hls-amer}"            # Databricks CLI profile (fe-hls)
export CATALOG="${CATALOG:-tony_farias}"              # writable catalog (main is not writable in fe-hls)
export SCHEMA="${SCHEMA:-research_licensing_demo}"    # pipeline output schema
export VOLUME="${VOLUME:-dataroom_landing}"           # UC Volume = the SharePoint-style landing zone
export PIPELINE_NAME="${PIPELINE_NAME:-hls-research-licensing}"
export WAREHOUSE_ID="${WAREHOUSE_ID:-}"               # SQL warehouse id for the *.sql steps (required)
export LICENSING_OUT_DIR="${LICENSING_OUT_DIR:-/tmp/licensing_demo}"

export VOLUME_ROOT="/Volumes/${CATALOG}/${SCHEMA}/${VOLUME}"
export LANDING_PATH="${VOLUME_ROOT}/data_room"        # pipeline watches here
