"""Build the NETSUITE_GTN model const for the Oracle NetSuite Gross-to-Net tab.

Unlike the Veeva/SF generators (which pull live UC metadata), this is a curated,
representative model of how a pharma/life-sciences gross-to-net process is modeled
in Oracle NetSuite (ERP transactions + GTN custom records). It emits the same
payload shape as generate_data.py so index.html renders it identically:

  { domains:[{name,blurb,tables,ghosts,edges,mermaid}], tables:{name:{cols,domain}},
    hubRefs:{}, totals:{tables,edges} }

FK edges are inferred from columns named `<target_table>_id`.
Writes the const to netsuite_gtn.js (appended to static/data.js at deploy time).
"""
import json
from collections import defaultdict

OUT = "netsuite_gtn.js"

# Cross-cutting reference tables: kept as entities in their home domain, but their
# (very many) inbound edges are collapsed so diagrams stay readable.
HUBS = {"item", "customer", "accounting_period", "subsidiary",
        "gl_account", "currency", "deduction_category", "customer_class"}

BLURBS = {
    "Master Data & Setup": "NetSuite setup records — subsidiaries, customers (payers/wholesalers/GPOs), drug items, NDCs, GL accounts, periods and price levels.",
    "Gross Sales — NetSuite Transactions": "Order-to-invoice transactions that produce gross sales: sales orders, fulfillments, invoices and the gross-sales fact.",
    "Contracts & Pricing": "Customer/class contracts, WAC and contract price levels, chargeback eligibility and formulary tiers that drive deductions.",
    "GTN Deductions & Accruals": "The heart of gross-to-net: accruals by deduction category — chargebacks, commercial/Medicaid/Medicare rebates, fees, prompt-pay, returns, shelf-stock and copay assistance.",
    "Settlements & Claims": "Actuals that true-up the accruals: rebate and chargeback claims, credit memos and vendor payments to payers.",
    "Ledger & Net Sales": "Accounting close: journal entries/lines, accrual reversals, GTN rate %, reconciliation and the net_sales_summary (gross − deductions = net).",
}

# domain -> list of (table_name, total_col_count, [fk columns named <target>_id])
MODEL = {
    "Master Data & Setup": [
        ("subsidiary",         18, []),
        ("customer",           64, ["subsidiary_id", "customer_class_id"]),
        ("customer_class",     12, []),
        ("item",               88, ["product_family_id", "subsidiary_id"]),
        ("product_family",     14, []),
        ("ndc_code",           16, ["item_id"]),
        ("currency",            9, []),
        ("accounting_period",  15, []),
        ("gl_account",         22, []),
        ("price_level",        11, []),
        ("vendor",             40, ["subsidiary_id"]),
    ],
    "Gross Sales — NetSuite Transactions": [
        ("sales_order",        52, ["customer_id", "subsidiary_id", "currency_id"]),
        ("sales_order_line",   30, ["sales_order_id", "item_id"]),
        ("invoice",            58, ["customer_id", "sales_order_id", "accounting_period_id", "currency_id"]),
        ("invoice_line",       34, ["invoice_id", "item_id", "gl_account_id", "price_level_id"]),
        ("item_fulfillment",   26, ["sales_order_id", "item_id", "customer_id"]),
        ("gross_sales_fact",   20, ["invoice_line_id", "item_id", "customer_id", "accounting_period_id"]),
    ],
    "Contracts & Pricing": [
        ("contract",           36, ["customer_id", "customer_class_id", "subsidiary_id"]),
        ("contract_line",      22, ["contract_id", "item_id", "price_level_id"]),
        ("price_list",         14, ["price_level_id"]),
        ("wac_price",          10, ["item_id"]),
        ("chargeback_eligibility", 16, ["contract_id", "item_id"]),
        ("formulary_tier",     12, ["customer_id", "item_id"]),
    ],
    "GTN Deductions & Accruals": [
        ("deduction_category",  8, []),
        ("gtn_accrual",        30, ["item_id", "customer_class_id", "accounting_period_id", "deduction_category_id", "gl_account_id"]),
        ("chargeback",         28, ["invoice_line_id", "contract_id", "item_id", "customer_id"]),
        ("commercial_rebate",  26, ["contract_id", "item_id", "customer_id", "accounting_period_id"]),
        ("medicaid_rebate",    24, ["item_id", "ndc_code_id", "accounting_period_id", "government_program_id"]),
        ("medicare_rebate",    22, ["item_id", "accounting_period_id", "government_program_id"]),
        ("government_program", 12, []),
        ("distribution_fee",   18, ["contract_id", "customer_id", "item_id"]),
        ("prompt_pay_discount",14, ["invoice_id", "customer_id"]),
        ("returns_reserve",    16, ["item_id", "accounting_period_id"]),
        ("shelf_stock_adjustment", 14, ["item_id", "customer_id"]),
        ("copay_assistance",   20, ["item_id", "accounting_period_id", "copay_program_id"]),
        ("copay_program",      12, []),
    ],
    "Settlements & Claims": [
        ("rebate_agreement",   28, ["contract_id", "customer_id", "customer_class_id"]),
        ("rebate_claim",       24, ["rebate_agreement_id", "item_id", "accounting_period_id"]),
        ("rebate_claim_line",  18, ["rebate_claim_id", "item_id"]),
        ("chargeback_claim",   22, ["customer_id", "contract_id"]),
        ("chargeback_claim_line", 18, ["chargeback_claim_id", "invoice_line_id", "item_id"]),
        ("credit_memo",        30, ["customer_id", "invoice_id", "accounting_period_id"]),
        ("credit_memo_line",   20, ["credit_memo_id", "item_id", "gl_account_id"]),
        ("vendor_payment",     24, ["vendor_id", "accounting_period_id"]),
        ("claim_validation",   10, []),
    ],
    "Ledger & Net Sales": [
        ("journal_entry",      26, ["accounting_period_id", "subsidiary_id"]),
        ("journal_line",       20, ["journal_entry_id", "gl_account_id", "gtn_accrual_id"]),
        ("accrual_reversal",   14, ["gtn_accrual_id", "accounting_period_id"]),
        ("net_sales_summary",  24, ["item_id", "customer_class_id", "accounting_period_id", "subsidiary_id"]),
        ("gtn_reconciliation", 18, ["accounting_period_id", "item_id", "deduction_category_id"]),
        ("gtn_rate",           12, ["item_id", "deduction_category_id", "accounting_period_id"]),
    ],
}

DOMAIN_ORDER = list(MODEL.keys())


def main():
    domain_of, cols_of, fks_of = {}, {}, {}
    for dname, rows in MODEL.items():
        for name, ncols, fks in rows:
            domain_of[name] = dname
            cols_of[name] = ncols
            fks_of[name] = fks
    names = set(domain_of)

    # infer edges: column <target>_id -> table <target>
    edges = set()
    for src, fks in fks_of.items():
        for fc in fks:
            tgt = fc[:-3] if fc.endswith("_id") else None
            if tgt in names and tgt != src:
                edges.add((tgt, src, fc))

    hub_refs = defaultdict(int)
    kept = []
    for tgt, src, col in sorted(edges):
        if tgt in HUBS:
            hub_refs[tgt] += 1
        else:
            kept.append((tgt, src, col))

    fk_cols = defaultdict(set)
    for tgt, src, col in edges:
        fk_cols[src].add(col)

    domains = defaultdict(list)
    for n in names:
        domains[domain_of[n]].append(n)

    domain_edges = defaultdict(list)
    for tgt, src, col in kept:
        domain_edges[domain_of[src]].append((tgt, src, col))

    def entity_block(name, ghost=False):
        lines = [f"  {name} {{"]
        if ghost:
            lines.append('    bigint id PK "defined in its own section"')
        else:
            ncols = cols_of[name]
            lines.append("    bigint id PK")
            for fc in sorted(fk_cols.get(name, set())):
                lines.append(f"    bigint {fc} FK")
            shown = len(lines) - 1
            if ncols > shown:
                lines.append(f'    string note "{ncols} columns total"')
        lines.append("  }")
        return "\n".join(lines)

    out_domains = []
    for dname in DOMAIN_ORDER:
        members = sorted(domains[dname])
        es = domain_edges.get(dname, [])
        ghosts = sorted({tgt for tgt, _, _ in es if domain_of[tgt] != dname})
        src_lines = ["erDiagram"]
        for tgt, src, col in es:
            src_lines.append(f'  {tgt} ||--o{{ {src} : "{col}"')
        for n in members:
            src_lines.append(entity_block(n))
        for g in ghosts:
            src_lines.append(entity_block(g, ghost=True))
        out_domains.append({
            "name": dname,
            "blurb": BLURBS.get(dname, ""),
            "tables": members,
            "ghosts": ghosts,
            "edges": len(es),
            "mermaid": "\n".join(src_lines),
        })

    table_meta = {n: {"cols": cols_of[n], "domain": domain_of[n]} for n in names}
    payload = {
        "domains": out_domains,
        "tables": table_meta,
        "hubRefs": dict(hub_refs),
        "totals": {"tables": len(names), "edges": len(kept)},
    }
    with open(OUT, "w") as f:
        f.write("const NETSUITE_GTN = ")
        json.dump(payload, f)
        f.write(";\n")
    print(f"{len(names)} tables, {len(kept)} drawn edges, "
          f"{sum(hub_refs.values())} hub refs collapsed -> {OUT}")
    for d in out_domains:
        print(f"  {d['name']}: {len(d['tables'])} tables, {d['edges']} edges, {len(d['ghosts'])} ghosts")


if __name__ == "__main__":
    main()
