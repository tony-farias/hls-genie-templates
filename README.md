# HLS Data Models

An interactive **entity-relationship (ERD) explorer** for Health & Life Sciences data
models, deployed as a **Databricks App**. Each tab is one source system's schema, drawn
as clickable Mermaid ER diagrams grouped into functional domains, with live links to the
underlying Unity Catalog tables and per-domain **"Ask Genie"** buttons.

**Live app:** https://hls-data-models-1602460480284688.aws.databricksapps.com
(deployed in the `fe-hls` workspace, profile `fe-vm-hls-amer`)

## Tabs / models

| Tab | Source | Data const |
|-----|--------|-----------|
| Commercial CRM | Veeva Vault CRM (`veeva836`) | `VEEVA836` |
| Safety · Pharmacovigilance | Veeva Safety Vault (`safety-vault`) | `SAFETYVAULT` |
| Quality · QMS | Veeva Quality (`quality-qms-veeva`) | `QMSVEEVA` |
| Clinical · CTMS | Veeva Clinical (`clinical-ctms-veeva`) | `CTMSVEEVA` |
| Health Cloud · Benefits Verification | Salesforce Health Cloud (mock) | `PATIENTSERVICES` |
| Finance · Gross-to-Net | Oracle NetSuite (mock) | `NETSUITE_GTN` |

Per-source branding is applied automatically (Veeva orange, Salesforce blue, NetSuite red).

## How it works

- **`app.py`** — minimal Flask server that serves the `static/` folder. No backend logic.
- **`static/index.html`** — the entire UI: a `MODELS` registry (one entry per tab) plus
  rendering/branding/Genie-wiring code. This is the file you edit to add a tab, change
  branding, or wire a Genie space.
- **`static/data.js`** — generated model data (one `const` per tab). **Do not hand-edit**;
  regenerate with the `generate_*.py` scripts (see [BUILD.md](BUILD.md)).

### Wiring a Genie space to a tab/section
Add a `genieByDomain` map to that model in `index.html` — keys are section (domain) names,
values are Genie room URLs. When present, that section's button opens the Genie space
instead of the mock modal. Cross-workspace URLs are fine. Example:
```js
genieByDomain: {
  "Benefits Verification": "https://<host>/genie/rooms/<space_id>?o=<org_id>"
}
```

## Local development
```bash
pip install -r requirements.txt
python app.py            # serves on http://localhost:8000
```

## Deploy
Deploys are handled by [`deploy.sh`](deploy.sh) (uploads the runtime files to the
workspace and runs `databricks apps deploy`):
```bash
./deploy.sh
```
Requires the Databricks CLI authenticated to the `fe-vm-hls-amer` profile.

> ⚠️ **The deployed app is the source of truth.** Local copies can drift. Before making
> changes, pull the current deployment first:
> ```bash
> databricks workspace export-dir \
>   /Workspace/Users/antonio.farias@databricks.com/apps/hls-data-models . \
>   --profile fe-vm-hls-amer --overwrite
> ```

## Repo layout
```
app.py app.yaml requirements.txt   # Databricks App runtime (deployed)
static/index.html static/data.js   # UI + generated data (deployed)
generate_*.py  netsuite_gtn.js     # build-time model generators (NOT deployed) — see BUILD.md
deploy.sh                          # deploy to fe-hls
skills/                            # Claude Code skills for this project (NOT deployed)
  genie-creation-skills/           #   create-genie-space: create a Genie space + wire it into the app
  lakeflow-connect-skills/         #   (placeholder for Lakeflow Connect ingestion skills)
```

## Skills
The `skills/` folder holds Claude Code skills for working on this project, grouped into
two categories under the common `skills/` folder:
- **`genie-creation-skills/create-genie-space`** — create a Databricks AI/BI Genie space
  via API and wire it to a tab's per-domain "Ask Genie" button.
- **`lakeflow-connect-skills/`** — placeholder for Lakeflow Connect ingestion skills.

To use them with Claude Code, symlink or copy the category contents into `~/.claude/skills`
(personal skills are discovered one level under that folder), or package them as a plugin.
