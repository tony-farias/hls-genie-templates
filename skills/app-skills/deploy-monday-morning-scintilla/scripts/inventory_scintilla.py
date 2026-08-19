#!/usr/bin/env python3
"""Read-only Scintilla Cloud Feed readiness inventory using the Databricks CLI."""

import argparse
import json
import subprocess
from pathlib import Path


CAPABILITIES = {
    "Sales performance": ["store_sales", "omni_sales", "upc_sales"],
    "Product hierarchy": ["item_dim", "prod_dim", "omni_item_dim"],
    "Store geography": ["store_dim"],
    "Calendar": ["calendar_dim"],
    "Inventory availability": ["store_invt", "hourly_store_invt", "dc_invt"],
    "Out-of-stock diagnosis": ["oos_root_cause", "invt_adj", "bkrm_adj"],
    "Forecasting": ["dly_dmnd_fcst", "store_demand_forecast", "order_demand_forecast"],
    "E-commerce": ["ecom_invt", "ecom_instock_pct", "fc_ecom_instock_pct", "digital_transactability", "ecom_prod_cntnt_score", "ecom_returns"],
    "Store fulfillment": ["store_fulfillment", "hourly_store_fulfillment"],
    "Supply chain and OTIF": ["purchase_order", "po_line", "po_line_destination", "po_dc_receiver", "po_dc_receiver_line", "omni_otif", "dc_alignment", "dc_dim"],
    "Pricing and funding": ["sku_mumd", "coops"],
    "Returns": ["store_customer_return", "store_returns"],
    "Assortment and modular": ["store_modular", "modular_plan", "modular_plan_upc", "modular_trait", "modular_upc_loc", "item_trait", "store_trait", "traits"],
    "Affinity and bundles": ["item_affinity", "kit_sales"],
}

CORE = {"Sales performance", "Product hierarchy", "Store geography", "Calendar", "Inventory availability", "Out-of-stock diagnosis"}


def sql(profile, warehouse_id, statement):
    payload = json.dumps({"statement": statement, "warehouse_id": warehouse_id, "format": "JSON_ARRAY", "wait_timeout": "50s"})
    result = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/sql/statements/", f"--json={payload}", f"--profile={profile}"],
        check=True, capture_output=True, text=True,
    )
    response = json.loads(result.stdout)
    if response.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError(response.get("status"))
    return response.get("result", {}).get("data_array", [])


def ident(value):
    if not value or not value.replace("_", "").isalnum():
        raise ValueError(f"Unsafe identifier: {value!r}")
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--warehouse-id", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    catalog, schema = ident(args.catalog), ident(args.schema)

    rows = sql(args.profile, args.warehouse_id, (
        "SELECT table_name, count(*) AS column_count, "
        "concat_ws(',', sort_array(collect_list(column_name))) AS columns "
        f"FROM {catalog}.information_schema.columns WHERE table_schema = '{schema}' "
        "GROUP BY table_name ORDER BY table_name"
    ))
    tables = {name: {"columns": int(count), "names": names.split(",") if names else []} for name, count, names in rows}

    lines = [
        "# Monday Morning / Scintilla readiness", "",
        f"Source: `{catalog}.{schema}`", f"Tables discovered: **{len(tables)}**", "",
        "| Capability | Tier | Status | Present | Missing |", "|---|---|---|---|---|",
    ]
    core_ready = True
    for capability, expected in CAPABILITIES.items():
        present = [name for name in expected if name in tables]
        missing = [name for name in expected if name not in tables]
        tier = "Core" if capability in CORE else "Expansion"
        if capability in CORE and not present:
            core_ready = False
        status = "READY" if not missing else ("PARTIAL" if present else "MISSING")
        lines.append(f"| {capability} | {tier} | {status} | {', '.join(present) or '—'} | {', '.join(missing) or '—'} |")
    lines += ["", f"Core deployment readiness: **{'READY' if core_ready else 'BLOCKED'}**", "", "## Discovered tables", ""]
    for name in sorted(tables):
        lines.append(f"- `{name}` — {tables[name]['columns']} columns")
    text = "\n".join(lines) + "\n"
    if args.output:
        Path(args.output).write_text(text)
        print(args.output)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
