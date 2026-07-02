"""Build static/data.js for the veeva836 tab from captured UC metadata.

Reads /tmp/veeva836_all.json (UC tables API dump) and emits:
  - DOMAINS: ordered list of {name, blurb, tables, mermaid}
  - TABLES:  {name: {cols, domain}}
Hub tables (object_type__v, country__v, application_profile__v) are kept as
entities in their home domain but their inbound edges are collapsed to keep
the diagrams readable.
"""
import json
import re
from collections import defaultdict

SRC = "/tmp/veeva836_all.json"
OUT = "static/data.js"

HUBS = {"object_type__v", "country__v", "application_profile__v"}
# user-style audit columns that don't correspond to tables in this schema
AUDIT_COLS = {"created_by__v", "modified_by__v", "ownerid__v"}

RULES = [
    ("Events Management", r"^(em_|event_attendee|business_event|medical_event|cvent_|events_management|expense)"),
    ("Multichannel & Cycle Plans", r"^(mc_|multichannel_|campaign|cycle_plan|message|messaging_|engage_|email_builder|approved_email|consent_|order_campaign)"),
    ("Calls & Activity", r"^(call2|activity|external_calendar|sync_tracking|tsf|unavailable_time)"),
    ("Accounts & People", r"^(account|address|affiliation|brick_|child_account|dcr_field|global_account|key_stakeholder|network_mapping|preferences)"),
    ("Content & Documents", r"^(approved_document|clm_|content_|doc_type|document_|html_report|index__v|key_message|keyword|myinsights|question|reference_document|survey|website)"),
    ("Products, Orders & Samples", r"^(assortment|contract|focus_area|formulary|goal|indication|inventory|lot_catalog|my_setup|opportunity|order|patient_journey|planogram|product|sales_transaction|sample|samples_)"),
    ("Territory & Alignment", r"^(agent_rule|align_|geography|implicit_filter|manual_territory|position|rep_roster|territory|user_role|user_territory)"),
    ("Medical Inquiries", r"^(medical_inquiry)"),
    ("Workflow, Audit & Platform", r"^(batch|child_event_rule|connection|data_grid|data_map|login_audit|metadata_|object_audit|object_type|outbound_package|pal_int|picklist|rule_|system_audit|vault_|workflow|xml_element)"),
    ("Settings & Admin", r".*"),
]

BLURBS = {
    "Accounts & People": "HCP/HCO master data, addresses, affiliations and account planning.",
    "Calls & Activity": "Call reporting (call2__v is the 233-column core fact), activity tracking and rep time.",
    "Events Management": "Speaker programs and events: budgets, sessions, attendees, expenses.",
    "Multichannel & Cycle Plans": "Approved email, consent, campaigns, engage, and MC cycle planning.",
    "Content & Documents": "CLM presentations, key messages, approved documents and surveys.",
    "Products, Orders & Samples": "Product master, order management, sampling and inventory.",
    "Territory & Alignment": "Territories, positions, roster and alignment rules.",
    "Medical Inquiries": "Medical information requests and fulfillment.",
    "Workflow, Audit & Platform": "Vault platform plumbing: workflows, audit trails, metadata and packaging.",
    "Settings & Admin": "Org-wide settings, configuration and admin objects.",
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

    # infer FK edges from Veeva naming: column foo__v -> table foo__v / foo_v__v
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

    fk_cols = defaultdict(set)  # table -> set of FK column names (incl. hub refs)
    for tgt, src, col in edges:
        fk_cols[src].add(col)

    col_types = {
        t["name"]: {c["name"]: c.get("type_name", "STRING").lower() for c in t.get("columns", [])}
        for t in tables
    }

    domains = defaultdict(list)
    for t in tables:
        domains[domain_of[t["name"]]].append(t["name"])

    # edges live in the child's domain; out-of-domain parents render as ghosts
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
        f.write("const VEEVA836 = ")
        json.dump(payload, f)
        f.write(";\n")
    print(f"{len(tables)} tables, {len(kept)} drawn edges, "
          f"{sum(hub_refs.values())} hub refs collapsed -> {OUT}")
    for d in out_domains:
        print(f"  {d['name']}: {len(d['tables'])} tables, {d['edges']} edges, {len(d['ghosts'])} ghosts")


if __name__ == "__main__":
    main()
