"""Build the Salesforce Health Cloud **Benefits Verification** data model as
`const PATIENTSERVICES = {...}` for the ERD app.

This mirrors the official Salesforce Health Cloud "Benefits Verification" ERD:
one model, 11 objects, color-split into Health Cloud (purple) vs Salesforce
Standard (grey) objects. Output structure matches the other generators so
buildTab() renders it; each table also carries a `kind` for two-tone coloring.
"""
import json

OUT = "/tmp/patient_services_data.js"

# name -> (kind, [fk (col, target) ...], total_cols)
# kind: "hc" = Health Cloud object, "std" = Salesforce standard object
OBJECTS = {
    "PersonAccount":            ("std", [], 42),
    "Account":                  ("std", [], 38),   # Business Account (Payer)
    "Case":                     ("std", [], 36),   # Investigation
    "MemberPlan":               ("hc",  [("MemberId", "PersonAccount"), ("PurchaserPlanId", "PurchaserPlan")], 31),
    "CareBenefitVerifyRequest": ("hc",  [("MemberPlanId", "MemberPlan"), ("CaseId", "Case")], 27),
    "CoverageBenefit":          ("hc",  [("MemberPlanId", "MemberPlan"), ("CareBenefitVerifyRequestId", "CareBenefitVerifyRequest")], 24),
    "CoverageBenefitItem":      ("hc",  [("CoverageBenefitId", "CoverageBenefit"), ("CodeSetId", "CodeSet")], 19),
    "CoverageBenefitItemLimit": ("hc",  [("CoverageBenefitItemId", "CoverageBenefitItem"), ("CareLimitTypeId", "CareLimitType")], 14),
    "PurchaserPlan":            ("hc",  [("PayerId", "Account")], 18),
    "CodeSet":                  ("hc",  [], 12),
    "CareLimitType":            ("hc",  [], 10),
}

# Display labels matching the Salesforce diagram (shown under the API name)
LABELS = {
    "PersonAccount": "Person Account (Member)",
    "Account": "Business Account (Payer)",
    "Case": "Case (Investigation)",
    "MemberPlan": "Member Plan",
    "CareBenefitVerifyRequest": "Care Benefit Verify Request",
    "CoverageBenefit": "Coverage Benefit",
    "CoverageBenefitItem": "Coverage Benefit Item",
    "CoverageBenefitItemLimit": "Coverage Benefit Item Limit",
    "PurchaserPlan": "Purchaser Plan",
    "CodeSet": "Code Set",
    "CareLimitType": "CareLimitType (Tooling API)",
}

DOMAIN = "Benefits Verification"
BLURB = ("Salesforce Health Cloud Benefits Verification model — verifies a member's insurance "
         "coverage. A Member Plan (the patient's insurance) drives a Care Benefit Verify Request, "
         "which resolves into Coverage Benefits, Items and Item Limits, tied to payers, code sets "
         "and care limit types. Purple = Health Cloud object, grey = Salesforce standard object.")


def main():
    names = list(OBJECTS)

    # edges: parent ||--o{ child labeled by the FK column on the child
    edges = []  # (parent, child, col)
    for child, (_, fks, _) in OBJECTS.items():
        for col, parent in fks:
            edges.append((parent, child, col))

    def entity_block(name):
        kind, fks, ncols = OBJECTS[name]
        lines = [f"  {name} {{", "    string Id PK"]
        for col, _ in fks:
            lines.append(f"    string {col} FK")
        shown = len(lines) - 1
        if ncols > shown:
            lines.append(f'    string note "{ncols} columns total"')
        lines.append("  }")
        return "\n".join(lines)

    src = ["erDiagram"]
    for parent, child, col in edges:
        src.append(f'  {parent} ||--o{{ {child} : "{col}"')
    for n in names:
        src.append(entity_block(n))

    domain = {
        "name": DOMAIN,
        "blurb": BLURB,
        "tables": sorted(names),
        "ghosts": [],
        "edges": len(edges),
        "mermaid": "\n".join(src),
    }
    table_meta = {
        n: {"cols": OBJECTS[n][2], "domain": DOMAIN, "kind": OBJECTS[n][0], "label": LABELS[n]}
        for n in names
    }
    payload = {
        "domains": [domain],
        "tables": table_meta,
        "hubRefs": {},
        "totals": {"tables": len(names), "edges": len(edges)},
    }
    with open(OUT, "w") as f:
        f.write("const PATIENTSERVICES = ")
        json.dump(payload, f)
        f.write(";\n")
    print(f"{len(names)} objects, {len(edges)} relationships -> {OUT}")
    for n in sorted(names):
        print(f"  {OBJECTS[n][0]:3}  {n}")


if __name__ == "__main__":
    main()
