#!/usr/bin/env bash
# End-to-end Research In-Licensing demo runner (fe-hls workspace).
#
#   1. generate the sanitized, fictional data-room package (local)
#   2. create schema + landing Volume            (00_setup.sql)
#   3. upload the data_room/ tree to the Volume
#   4. create/refresh the Lakeflow pipeline and run an update (pipeline/licensing_pipeline.py)
#
# Requires: Databricks CLI authed to $PROFILE, and a SQL warehouse id in $WAREHOUSE_ID.
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

if [[ -z "${WAREHOUSE_ID}" ]]; then
  echo "ERROR: set WAREHOUSE_ID (a SQL warehouse in fe-hls) before running." >&2
  echo "  e.g.  WAREHOUSE_ID=abc123 ./run_demo.sh" >&2
  exit 1
fi

WS_DIR="/Workspace/Users/antonio.farias@databricks.com/demos/research-licensing"

run_sql() {
  local file="$1"; echo "   >> $file"
  envsubst < "$file" | DATABRICKS_PROFILE="$PROFILE" WAREHOUSE_ID="$WAREHOUSE_ID" python3 exec_sql.py
}

echo "== 1. generate the fictional data-room package (local)"
LICENSING_OUT_DIR="$LICENSING_OUT_DIR" python3 generate/generate_licensing_package.py

echo "== 2. create schema + volume"
run_sql 00_setup.sql

echo "== 3. upload the data room to the landing volume"
databricks fs cp -r --overwrite "${LICENSING_OUT_DIR}/data_room" "dbfs:${VOLUME_ROOT}/data_room" --profile "$PROFILE"

echo "== 4. upload pipeline source to workspace"
databricks workspace mkdirs "$WS_DIR" --profile "$PROFILE"
databricks workspace import "${WS_DIR}/licensing_pipeline.py" --file pipeline/licensing_pipeline.py \
  --language PYTHON --format SOURCE --overwrite --profile "$PROFILE"

echo "== 5. create/refresh Lakeflow pipeline and run an update"
SPEC_FILE="$(mktemp /tmp/licensing_pipeline_spec.XXXXXX.json)"
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
    "configuration": {"spark.licensing.landing_path": os.environ["LANDING_PATH"]},
    "libraries": [{"file": {"path": os.environ["WS_DIR"] + "/licensing_pipeline.py"}}],
}, indent=2))
PY

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
echo "Tables in ${CATALOG}.${SCHEMA}: bronze_documents, silver_* (assay/pk_pd/tox/stability/patent), gold_dataroom_index"
