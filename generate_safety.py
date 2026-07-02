"""Build the SAFETYVAULT data object for the Safety tab from captured UC metadata.

Mirrors generate_data.py (commercial / veeva836) but with pharmacovigilance
domain groupings for the Veeva Vault Safety schema (ravivijay_catalog.`safety-vault`).
Reads /tmp/safety_vault_all.json and writes `const SAFETYVAULT = {...};` to OUT.
"""
import json
import re
from collections import defaultdict

SRC = "/tmp/safety_vault_all.json"
OUT = "/tmp/safety_data.js"

# Mega-hubs: pure cross-cutting reference/platform tables referenced by many
# objects. Kept as entities in their home domain; inbound edges collapsed.
HUBS = {"object_type__v", "organization__v", "country__v", "localization__v"}
AUDIT_COLS = {"created_by__v", "modified_by__v", "ownerid__v"}

# Ordered: first match wins.
RULES = [
    ("Case Processing", r"^(case|safety_investigation|narrative|followup|activity__v|checklist|answer_selection|form_|question_field|standard_question|device_code|source__v|reason_omitted)"),
    ("Aggregate Reporting & Submissions", r"^(aggregate|reporting_group|schedule|scheduled_event|transmission|site_report|distribution_jurisdiction|tabular|sequential_number)"),
    ("Signal Management", r"^(signal|significance_criteria|validation_criteria)"),
    ("Risk Management & PSMF", r"^(rmp_|core_rmp|local_rmp|psmf)"),
    ("PV Agreements", r"^(pva_|pv_agreement)"),
    ("Literature", r"^literature"),
    ("MedDRA & Dictionaries", r"^(meddra|dictionary|controlled_vocabulary|localized_controlled|edqm|watchlist)"),
    ("Products & Substances", r"^(product|substance|inactive_ingredient|datasheet|dose_form|route_of_administration|manufacturer_site|organization|reporting_family|market_segment|unit_of_measurement|agency_unit)"),
    ("Studies", r"^study"),
    ("Localization & Reference", r"^(localiz|language|country|region|translation|core_)"),
    ("Platform, Workflow & Admin", r".*"),
]

BLURBS = {
    "Case Processing": "ICSR intake to assessment: cases, adverse events, products, dosage, drug & medical history, narratives and follow-up.",
    "Aggregate Reporting & Submissions": "Aggregate reports (PSUR/PBRER/DSUR), reporting groups, schedules and transmission to health authorities.",
    "Signal Management": "Signal detection rules, product profiles, health-authority databases and significance/validation criteria.",
    "Risk Management & PSMF": "Risk management plans (core & local), risk measures and the Pharmacovigilance System Master File.",
    "PV Agreements": "Pharmacovigilance agreements (PVA/SDEA): obligations, activities, outlines and MAA scope.",
    "Literature": "Literature monitoring: articles, authors, databases, search terms and review workflow.",
    "MedDRA & Dictionaries": "MedDRA coding, queries (SMQs), controlled vocabularies, EDQM and watchlists.",
    "Products & Substances": "Product master, substances, families, dose forms, registrations, manufacturers and organizations.",
    "Studies": "Clinical study master, study products and aliases.",
    "Localization & Reference": "Localized reference data, languages, countries/regions and translation settings.",
    "Platform, Workflow & Admin": "Vault platform plumbing: safety rules, users/roles, workbench, audit trails, settings and packaging.",
}


def base_name(n):
    return re.sub(r"__(v|c|sys)$", "", n)


def main():
    tables = json.load(open(SRC))
    tables.sort(key=lambda t: t["name"])
    names = {t["name"] for t in tables}
    by_base = {base_name(n): n for n in names}

    domain_of = {}
    for t in tables:
        n = t["name"]
        for d, rx in RULES:
            if re.search(rx, n):
                domain_of[n] = d
                break

    edges = set()
    for t in tables:
        src = t["name"]
        for c in t.get("columns", []):
            cn = c["name"]
            if cn in AUDIT_COLS:
                continue
            m = re.match(r"^(.*)__(v|c|sys)$", cn)
            if not m:
                continue
            cb = m.group(1)
            tgt = by_base.get(cb) or (by_base.get(cb[:-2]) if cb.endswith("_v") else None)
            if tgt and tgt != src:
                edges.add((tgt, src, cn))

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

    col_types = {
        t["name"]: {c["name"]: c.get("type_name", "STRING").lower() for c in t.get("columns", [])}
        for t in tables
    }

    domains = defaultdict(list)
    for t in tables:
        domains[domain_of[t["name"]]].append(t["name"])

    domain_edges = defaultdict(list)
    for tgt, src, col in kept:
        domain_edges[domain_of[src]].append((tgt, src, col))

    def entity_block(name, ghost=False):
        lines = [f"  {name} {{"]
        if ghost:
            lines.append('    string id PK "defined in its own section"')
        else:
            types = col_types[name]
            ncols = len(types)
            if "id" in types:
                lines.append(f"    {types['id']} id PK")
            for fc in sorted(fk_cols.get(name, set())):
                lines.append(f"    {types.get(fc, 'string')} {fc} FK")
            shown = len(lines) - 1
            lines.append(f'    string note "{ncols} columns total"' if ncols > shown else "")
        lines.append("  }")
        return "\n".join(l for l in lines if l)

    out_domains = []
    for dname, _ in RULES:
        if dname not in domains:
            continue
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

    table_meta = {
        t["name"]: {"cols": len(t.get("columns", [])), "domain": domain_of[t["name"]]}
        for t in tables
    }

    payload = {
        "domains": out_domains,
        "tables": table_meta,
        "hubRefs": dict(hub_refs),
        "totals": {"tables": len(tables), "edges": len(kept)},
    }
    with open(OUT, "w") as f:
        f.write("const SAFETYVAULT = ")
        json.dump(payload, f)
        f.write(";\n")
    print(f"{len(tables)} tables, {len(kept)} drawn edges, "
          f"{sum(hub_refs.values())} hub refs collapsed -> {OUT}")
    for d in out_domains:
        print(f"  {d['name']}: {len(d['tables'])} tables, {d['edges']} edges, {len(d['ghosts'])} ghosts")


if __name__ == "__main__":
    main()
