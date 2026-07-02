"""Build the CTMSVEEVA data object for the Clinical (CTMS) tab from captured UC metadata.

Mirrors generate_qms.py but for Veeva Vault Clinical (ravivijay_catalog.`clinical-ctms-veeva`),
landed by the veeva-clinical Lakeflow Connect ingestion pipeline. Veeva Clinical objects use
__v / __c / __sys plus the clinical-specific __clin and __ctms suffixes.
Reads /tmp/ctms_all.json and writes `const CTMSVEEVA = {...};` to OUT.
"""
import json
import re
from collections import defaultdict

SRC = "/tmp/ctms_all.json"
OUT = "/tmp/ctms_data.js"

HUBS = {"object_type__v", "country__v", "picklist__sys", "jurisdiction__v"}
AUDIT_COLS = {"created_by__v", "modified_by__v", "ownerid__v"}
SUF = r"__(v|c|sys|clin|ctms)"

# First match wins — specific modules before the generic study/platform catch-alls.
RULES = [
    ("Studies & Protocols", r"^(study__v|study_arm|study_country__v|study_organization|study_product|study_critical|study_communication|study_cdms|study_migration|study_archival|study_team_role|study_startup|investigator_initiated_study|model__v|hierarchy__v)"),
    ("Sites & Site Management", r"^(site|study_site|monitored_study_site|sitevault|location__v)"),
    ("Investigators, Persons & Organizations", r"^(person|organization|selected_organization|contact_information|responsibility|team_role|study_person|study_responsibility|country__v|jurisdiction|role_dependency)"),
    ("Subjects & Enrollment", r"^(subject|monitored_subject|enrollment|global_subject|study_country_subject|study_product_subject|study_site_subject|unblinded_subject|repeat_instance)"),
    ("Informed Consent (eConsent)", r"^(informed_consent|subject_informed_consent|monitored_informed_consent|icf_|econsent)"),
    ("Visits & Procedures", r"^(visit|procedure|activity__v|event_schedule|story_event)"),
    ("Milestones & Timelines", r"^(milestone|global_milestone|selected_milestone|template_milestone|template_task)"),
    ("Monitoring & Trip Reports", r"^(monitoring|monitored|central_monitoring|standard_monitoring|trip_report|sdr_|study_sdr|review_summary)"),
    ("Risk Management (RBQM)", r"^(risk|study_risk|assigned_risk|qc_risk|critical_process|study_critical_process|study_critical_data|doc_type_risk|index_change|assessed_index)"),
    ("Issues, Deviations & Oversight", r"^(oversight_issue|monitored_issue|quality_issue|response_issue|pd_pv|pdv__|response__ctms)"),
    ("eTMF & Documents", r"^(edl|tmf_|doc_type|clinical_document|document_|subartifact|distribution_task|vault_component|xml_element)"),
    ("Forms & Assessments", r"^(form_|question|answer)"),
    ("Metrics & KPIs", r"^(metric|perf_stats|global_subject_metric|risk_rule_metrics)"),
    ("Safety Distribution", r"^(safety_dist|safety_distribution)"),
    ("CRM & Collaboration", r"^(crm_|discussion|agreement_transfer)"),
    ("Platform, Workflow & Admin", r".*"),
]

BLURBS = {
    "Studies & Protocols": "Study master records, arms, countries, products, organizations, critical data/process and startup — the core trial definitions.",
    "Sites & Site Management": "Investigator sites, site licenses, site packages, study-site plans and SiteVault signup.",
    "Investigators, Persons & Organizations": "People, organizations, study staff, responsibilities, team roles and the reference geography they hang off.",
    "Subjects & Enrollment": "Trial subjects, enrollment status, subject groups and per-subject metrics across study/country/site.",
    "Informed Consent (eConsent)": "Informed consent forms, ICF tracking, monitored consent and eConsent configuration.",
    "Visits & Procedures": "Visit schedules and definitions, procedures and procedure templates, and activity records.",
    "Milestones & Timelines": "Milestones, dependencies, templates and milestone sets that drive study timelines.",
    "Monitoring & Trip Reports": "Monitoring schedules/events, source data review, trip reports and review summaries.",
    "Risk Management (RBQM)": "Risk-based quality management: risks, mitigations, critical data/process, QC risk rules and assessments.",
    "Issues, Deviations & Oversight": "Oversight and monitored issues, quality issues, protocol deviations (PD/PV) and their responses.",
    "eTMF & Documents": "Trial Master File: expected document lists (EDL), TMF index, document types, artifacts and distribution.",
    "Forms & Assessments": "Forms, questions, answers and answer sets used for assessments and questionnaires.",
    "Metrics & KPIs": "Operational metrics, performance stats and subject-metric enablement across the program.",
    "Safety Distribution": "Safety document distribution defaults, types and mapping for the study network.",
    "CRM & Collaboration": "Veeva CRM integration objects, discussions/attendees and agreement transfers.",
    "Platform, Workflow & Admin": "Vault platform plumbing: workflows, users/roles, audit trails, picklists, CDX and settings.",
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
        f.write("const CTMSVEEVA = ")
        json.dump(payload, f)
        f.write(";\n")
    print(f"{len(tables)} tables, {len(kept)} drawn edges, "
          f"{sum(hub_refs.values())} hub refs collapsed -> {OUT}")
    for d in out_domains:
        print(f"  {d['name']}: {len(d['tables'])} tables, {d['edges']} edges, {len(d['ghosts'])} ghosts")


if __name__ == "__main__":
    main()
