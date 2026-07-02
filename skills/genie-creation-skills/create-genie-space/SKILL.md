---
name: create-genie-space
description: Create a Databricks AI/BI Genie space via the REST API and (optionally) wire it to open on click inside a Databricks App — e.g. the hls-data-models ERD app's per-domain "Ask Genie" button. Use when asked to create/provision a Genie space or room, or to hook an existing Genie space into an app.
---

# Create a Genie space and wire it into an app

Covers (1) creating a Genie space over UC tables via API, and (2) making it open on
click from a Databricks App (the hls-data-models "Ask Genie" pattern).

## 1. Auth (dogfood staging quirk)
Most FE demos live in **dogfood staging**, whose multi-org host the CLI can't pin.
Call the REST API with curl + the org header:

```bash
HOST="https://dogfood.staging.databricks.com"; ORG="6051921418418893"
TOK=$(databricks auth token --profile dogfood-staging | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
auth=(-H "Authorization: Bearer $TOK" -H "X-Databricks-Org-Id: $ORG")
```
For a normal (non-dogfood) workspace, use the matching `--profile` and drop the org header.
Pick a **running serverless SQL warehouse** for the space (list: `GET /api/2.0/sql/warehouses`).

## 2. Create the space
Two APIs exist; use whichever the workspace supports:

**a) data-rooms API (simple, table list):**
```bash
curl -s "$HOST/api/2.0/data-rooms" "${auth[@]}" -H "Content-Type: application/json" -X POST -d '{
  "display_name": "My Genie",
  "description": "Natural-language questions over <domain>.",
  "warehouse_id": "<WH_ID>",
  "table_identifiers": ["cat.schema.table_a", "cat.schema.table_b"],
  "instructions": "Scope + column semantics for the LLM.",
  "sample_questions": ["Q1?", "Q2?"]
}'
# returns space_id (== id). URL: $HOST/genie/rooms/<space_id>
```

**b) genie/spaces API (newer, richer):** `POST /api/2.0/genie/spaces` needs a
`serialized_space` JSON **string** (`{version:2, config.sample_questions,
data_sources.tables[].identifier, benchmarks}`) — NOT a plain table list — and
`data_sources.tables` MUST be sorted by identifier. Read an existing space's exact
format first: `GET /api/2.0/genie/spaces/{id}?include_serialized_space=true`.
Read a space's table list with `GET /api/2.0/data-rooms/{id}`. Delete with
`DELETE /api/2.0/genie/spaces/{id}`.

Keep instructions tight and table sets focused (a 15–20 table space answers far
better than a 45-table one).

## 3. Test it end-to-end
```bash
# start a conversation, then poll the message until COMPLETED
curl -s -X POST "$HOST/api/2.0/genie/spaces/$SID/start-conversation" "${auth[@]}" \
  -H "Content-Type: application/json" -d '{"content":"How many rows per category?"}'
curl -s "$HOST/api/2.0/genie/spaces/$SID/conversations/$CONV/messages/$MSG" "${auth[@]}"
```
Parse responses with `json.loads(..., strict=False)` — Genie answers contain raw
newlines that break strict JSON parsers.

## 4. Wire it to open on click in the hls-data-models app
The app (`~/dev/hls-data-models-deployed`, deployed as `hls-data-models` in fe-hls,
profile `fe-vm-hls-amer`) has a `MODELS` registry in `static/index.html`. Each model
(tab) may carry a `genieByDomain` map: **section/domain name → Genie URL**. When a
section has an entry, its button reads "Ask Genie" and opens that URL in a new tab;
otherwise it shows the mock modal.

```js
{
  tabId: "tab-patient-services",
  tabLabel: "Health Cloud · Benefits Verification",
  data: PATIENTSERVICES,
  ...
  genieByDomain: {
    "Benefits Verification": "https://<workspace-host>/genie/rooms/<space_id>?o=<org_id>"
  }
}
```
- The domain key must **exactly match** a `d.name` in that model's `data.domains`.
  List them: `node -e "$(cat static/data.js); MODEL.domains.forEach(d=>console.log(d.name))"`.
- Cross-workspace URLs are fine (the button just opens the link). Databricks One
  spaces use `?isDbOne=true&utm_source=databricks-one&o=<org>` — keep those params.

## 5. Deploy + check in
```bash
WS="/Workspace/Users/antonio.farias@databricks.com/apps/hls-data-models"
databricks workspace import "$WS/static/index.html" --file static/index.html --format AUTO --overwrite --profile fe-vm-hls-amer
databricks apps deploy hls-data-models --source-code-path "$WS" --profile fe-vm-hls-amer
# verify live (apps accept a bearer token for GET):
TOKEN=$(databricks auth token --profile fe-vm-hls-amer | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -sL -H "Authorization: Bearer $TOKEN" "https://hls-data-models-1602460480284688.aws.databricksapps.com/" | grep -c "<space_id>"
```
Then commit in the git repo at `~/dev/hls-data-models-deployed`.

**IMPORTANT — verify deployed source before redeploy:** the deployed app is the source
of truth (local copies can be stale). Always `databricks workspace export-dir "$WS" <dest>`
and edit that, or you'll clobber tabs that only exist in the deployment.
