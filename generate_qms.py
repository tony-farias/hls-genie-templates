"""Build the QMSVEEVA data object for the Quality · QMS tab from captured UC metadata.

Mirrors generate_safety.py but for Veeva Vault QMS (ravivijay_catalog.`quality-qms-veeva`),
which also uses a `__qdm` object suffix in addition to `__v`/`__c`/`__sys`.
Reads /tmp/qms_all.json and writes `const QMSVEEVA = {...};` to OUT.
"""
import json
import re
from collections import defaultdict

SRC = "/tmp/qms_all.json"
OUT = "/tmp/qms_data.js"

HUBS = {"object_type__v", "department__v", "country__v", "organization_location__v", "business_function__v"}
AUDIT_COLS = {"created_by__v", "modified_by__v", "ownerid__v"}
SUF = r"__(v|c|sys|qdm)"

RULES = [
    ("Quality Events & Deviations", r"^(quality_event|quality_incident|deviation|lab_investigation|related_quality|related_lab|related_event)"),
    ("CAPA & Effectiveness", r"^(capa|effectiveness_check|root_cause|implementation_action|action_step|mitigation_action|qe_effectiveness|related_capa|medtech_capa)"),
    ("Complaints", r"^(complaint|mt_complaint|reported_product|health_hazard|related_complaint)"),
    ("Change Control & SCN", r"^(change_|document_change_control|supplier_change|scn_|regulatory_change|product_change|related_supplier)"),
    ("Audits, Findings & SCAR", r"^(audit|auditor|inspection|finding|scar|qms_scar|qms_audit|related_audit)"),
    ("Risk Management (QRM & FMEA)", r"^(risk_|qrm_|fmea|hazard|hazop|assessment_|severity|detectability|occurrence|criticality|safety_case|impact_assessment|template_risk)"),
    ("APQR & Periodic Review", r"^(apqr|periodic_report|periodic_review|management_review|batch_release)"),
    ("Continuous Improvement", r"^(continuous_improvement|cont_imp|product_continuous)"),
    ("Products, Assets & Materials", r"^(product|asset|part|material|batch|service|quality_batch|quality_material|quality_related|quality_unit|regional_product|qd_excipient)"),
    ("Organizations & Reference", r"^(organization|department|subdepartment|business_|country|health_authority|hospital|location|third_party|legacy_system|job_title|category|subcategory|code|reference_model|visual_hierarchy|study|impacted_country|required_qual|role_qual|val_|test_plan|regulatory_activity|reporting_decision)"),
    ("Platform, Workflow & Admin", r".*"),
]

BLURBS = {
    "Quality Events & Deviations": "Quality events, deviations, lab investigations and incidents — the core QMS event records and their related items.",
    "CAPA & Effectiveness": "Corrective & preventive actions, root-cause analysis, action steps and effectiveness checks.",
    "Complaints": "Product complaints and intake, complaint-linked batches/parts/CAPA and health hazard evaluation.",
    "Change Control & SCN": "Change controls, change actions, impacted items and supplier change notifications.",
    "Audits, Findings & SCAR": "Internal/external audits, audit programs, findings and supplier corrective action requests (SCAR).",
    "Risk Management (QRM & FMEA)": "Quality risk management: risk registers, matrices, FMEA, hazards and assessment scoring.",
    "APQR & Periodic Review": "Annual Product Quality Review, periodic reports/reviews, management review and batch release.",
    "Continuous Improvement": "Continuous improvement initiatives and their linked assets, batches, materials and risks.",
    "Products, Assets & Materials": "Product, asset, part, material, batch and service master data.",
    "Organizations & Reference": "Organizations, departments, countries, health authorities, studies and reference/config data.",
    "Platform, Workflow & Admin": "Vault platform plumbing: workflows, users/roles, audit trails, doc types, settings and packaging.",
}


def base_name(n):
    return re.sub(SUF + r"$", "", n)


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
            m = re.match(r"^(.*)" + SUF + r"$", cn)
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
        f.write("const QMSVEEVA = ")
        json.dump(payload, f)
        f.write(";\n")
    print(f"{len(tables)} tables, {len(kept)} drawn edges, "
          f"{sum(hub_refs.values())} hub refs collapsed -> {OUT}")
    for d in out_domains:
        print(f"  {d['name']}: {len(d['tables'])} tables, {d['edges']} edges, {len(d['ghosts'])} ghosts")


if __name__ == "__main__":
    main()
