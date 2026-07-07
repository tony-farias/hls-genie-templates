#!/usr/bin/env bash
# End-to-end HEDIS Quality demo runner (fe-hls workspace).
#
#   1. generate synthetic HEDIS files + Data Cloud seeds (local)
#   2. create schemas + landing Volume            (00_setup.sql)
#   3. upload files: claims/ + enrollment/ -> Volume;  seeds -> Volume/_seed/
#   4. load Data Cloud dims + measure reference   (10_datacloud_dims.sql)
#   5. create/refresh the Lakeflow pipeline and run an update (hedis_pipeline.py)
#
# Requires: Databricks CLI authed to $PROFILE, and a SQL warehouse id in $WAREHOUSE_ID.
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

if [[ -z "${WAREHOUSE_ID}" ]]; then
  echo "ERROR: set WAREHOUSE_ID (a SQL warehouse in the fe-hls workspace) before running." >&2
  echo "  e.g.  WAREHOUSE_ID=abc123 ./run_demo.sh" >&2
  exit 1
fi

WS_DIR="/Workspace/Users/antonio.farias@databricks.com/demos/hedis-quality"

# --- helper: run a multi-statement SQL file with ${VAR} substitution ---
run_sql() {
  local file="$1"
  echo "   >> $file"
  envsubst < "$file" | DATABRICKS_PROFILE="$PROFILE" WAREHOUSE_ID="$WAREHOUSE_ID" python3 exec_sql.py
}

echo "== 1. generate synthetic data (local)"
python3 generate_hedis_files.py

echo "== 2. create schemas + volume"
run_sql 00_setup.sql

echo "== 3. upload files to the landing volume"
# HEDIS file feeds Auto Loader watches:
databricks fs cp -r --overwrite "${HEDIS_OUT_DIR}/claims"     "dbfs:${VOLUME_ROOT}/claims"     --profile "$PROFILE"
databricks fs cp -r --overwrite "${HEDIS_OUT_DIR}/enrollment" "dbfs:${VOLUME_ROOT}/enrollment" --profile "$PROFILE"
# Data Cloud + reference seeds (loaded into dim tables by step 4):
databricks fs mkdir "dbfs:${VOLUME_ROOT}/_seed" --profile "$PROFILE"
for f in member provider; do
  databricks fs cp --overwrite "${HEDIS_OUT_DIR}/datacloud/${f}.csv" "dbfs:${VOLUME_ROOT}/_seed/${f}.csv" --profile "$PROFILE"
done
for f in measure county; do
  databricks fs cp --overwrite "${HEDIS_OUT_DIR}/reference/${f}.csv" "dbfs:${VOLUME_ROOT}/_seed/${f}.csv" --profile "$PROFILE"
done

echo "== 4. load Data Cloud dimensions + measure reference"
run_sql 10_datacloud_dims.sql

echo "== 5. upload pipeline source to workspace"
databricks workspace mkdirs "$WS_DIR" --profile "$PROFILE"
databricks workspace import "${WS_DIR}/hedis_pipeline.py" --file hedis_pipeline.py \
  --language PYTHON --format SOURCE --overwrite --profile "$PROFILE"

echo "== 6. create/refresh Lakeflow pipeline and run an update"
SPEC_FILE="$(mktemp /tmp/hedis_pipeline_spec.XXXXXX.json)"
trap 'rm -f "$SPEC_FILE"' EXIT
WS_DIR="$WS_DIR" python3 - <<'PY' > "$SPEC_FILE"
import json, os
print(json.dumps({
    "name": os.environ["PIPELINE_NAME"],
    "catalog": os.environ["CATALOG"],
    "schema": os.environ["SCHEMA"],
    "serverless": True,
    "continuous": False,
    "development": True,
    "configuration": {
        "spark.hedis.landing_path": os.environ["LANDING_PATH"],
        "spark.hedis.datacloud_schema": f"{os.environ['CATALOG']}.{os.environ['DC_SCHEMA']}",
    },
    "libraries": [{"file": {"path": os.environ["WS_DIR"] + "/hedis_pipeline.py"}}],
}, indent=2))
PY

# reuse existing pipeline if one with this name already exists
EXISTING=$(databricks pipelines list-pipelines --profile "$PROFILE" --output json 2>/dev/null \
  | python3 -c "import sys,json;[print(p['pipeline_id']) for p in json.load(sys.stdin) if p.get('name')=='${PIPELINE_NAME}']" | head -1 || true)

if [[ -n "${EXISTING}" ]]; then
  echo "   updating existing pipeline ${EXISTING}"
  python3 -c "import json;d=json.load(open('${SPEC_FILE}'));d['id']='${EXISTING}';json.dump(d,open('${SPEC_FILE}','w'))"
  databricks pipelines update "${EXISTING}" --json "@${SPEC_FILE}" --profile "$PROFILE" >/dev/null
  PID="${EXISTING}"
else
  PID=$(databricks pipelines create --json "@${SPEC_FILE}" --profile "$PROFILE" --output json \
    | python3 -c 'import sys,json;print(json.load(sys.stdin)["pipeline_id"])')
  echo "   created pipeline ${PID}"
fi

echo "   starting update..."
databricks pipelines start-update "${PID}" --profile "$PROFILE" --output json \
  | python3 -c 'import sys,json;print("   update:",json.load(sys.stdin).get("update_id","?"))'

echo
echo "Done. Pipeline: ${PID}"
echo "Tables published to ${CATALOG}.${SCHEMA} (fact_claims, fact_enrollment, fact_quality_events, mv_quality_performance)."
echo "Watch the run: databricks pipelines get ${PID} --profile ${PROFILE}"
