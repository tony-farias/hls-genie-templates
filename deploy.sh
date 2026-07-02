#!/usr/bin/env bash
# Deploy the hls-data-models Databricks App to the fe-hls workspace.
#
# Uploads only the RUNTIME files (app.py, app.yaml, requirements.txt, static/) to the
# app's workspace folder, then runs `databricks apps deploy`. Build-time files
# (generate_*.py, netsuite_gtn.js) and skills/ are intentionally NOT deployed.
#
# Requires: Databricks CLI authenticated to the fe-vm-hls-amer profile.
set -euo pipefail

PROFILE="fe-vm-hls-amer"
APP="hls-data-models"
WS="/Workspace/Users/antonio.farias@databricks.com/apps/${APP}"
cd "$(dirname "$0")"

RUNTIME_FILES=(app.py app.yaml requirements.txt static/index.html static/data.js)

echo "== ensure workspace dirs"
databricks workspace mkdirs "${WS}/static" --profile "$PROFILE"

echo "== upload runtime files"
for f in "${RUNTIME_FILES[@]}"; do
  databricks workspace import "${WS}/${f}" --file "$f" --format AUTO --overwrite --profile "$PROFILE"
  echo "   ${f}"
done

echo "== deploy"
databricks apps deploy "$APP" --source-code-path "$WS" --profile "$PROFILE" --output json \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); s=d.get("status",{}); print("   deploy:", s.get("state"), "-", d.get("deployment_id",""))'

echo "== app status"
databricks apps get "$APP" --profile "$PROFILE" --output json \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print("   URL:", d.get("url")); print("   state:", d.get("app_status",{}).get("state"))'
