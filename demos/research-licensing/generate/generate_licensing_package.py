"""Generate a sanitized, fully-fictional in-licensing due-diligence package.

Mirrors the real translational-research scenario: a pharma's BD&L team receives a
data-room package on a pre-clinical asset, and Research must do scientific due
diligence. The package is the messy mix that lands in a SharePoint data room:
Word/PDF-style docs, Excel/CSV tables, and folder structure.

Everything here is INVENTED — fictional company, compound, target, people.
No real pharma brands, molecules, or deals. stdlib only, deterministic (seed=42).

Output layout (under OUT_DIR), a SharePoint-style data room:
  data_room/
    01_Corporate/            company overview, term sheet (md)
    02_Scientific/           target rationale, MoA memo, IND-readiness memo (md)
    03_Nonclinical/          tox summary (md) + assay/PKPD/tox tables (csv)
    04_CMC/                  formulation + stability tables (csv)
    05_IP/                   patent family table (csv), FTO memo (md)
    manifest.csv             one row per document (the data-room index)

The docs are Markdown (stand-ins for Word/PDF); the pipeline treats .md/.txt as
"unstructured" and .csv as "structured", exactly like a real mixed data room.
"""
import csv
import os
import random
import textwrap
from datetime import date, timedelta

SEED = 42
OUT_DIR = os.environ.get("LICENSING_OUT_DIR", "/tmp/licensing_demo")
random.seed(SEED)

# ---- fictional program identity (INVENTED) --------------------------------- #
ASSET = "AXL-2207"                       # fictional compound code
PROGRAM = "Project Meridian"             # internal deal codename
TARGET = "C5aR2"                         # a real receptor name is generic biology, not a brand
INDICATION = "autoimmune nephritis"
LICENSOR = "Helios Biosciences, Inc."    # fictional biotech (licensor)
LICENSEE = "Northwind Therapeutics"      # fictional acquirer (our stand-in)
MODALITY = "small-molecule antagonist"

PEOPLE = [  # all fictional
    ("Dr. Lena Ortiz", "CSO, Helios Biosciences"),
    ("Dr. Raymond Poole", "VP Nonclinical, Helios Biosciences"),
    ("Dr. Anika Rao", "Head of Translational DS, Northwind"),
    ("Marcus Feld", "BD&L Director, Northwind"),
]

TODAY = date(2026, 5, 1)


def _wtext(relpath, text):
    full = os.path.join(OUT_DIR, "data_room", relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(textwrap.dedent(text).strip() + "\n")
    return relpath, "doc", len(text)


def _wcsv(relpath, header, rows):
    full = os.path.join(OUT_DIR, "data_room", relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return relpath, "table", len(rows)


# ---- 01 Corporate ---------------------------------------------------------- #
def corporate():
    out = []
    out.append(_wtext("01_Corporate/company_overview.md", f"""
    # {LICENSOR} — Company Overview
    **Confidential — prepared for {LICENSEE} due diligence · {TODAY:%B %Y}**

    {LICENSOR} is a privately held, clinical-stage biotech focused on complement-pathway
    biology in immune-mediated disease. Lead asset **{ASSET}** ({MODALITY} of **{TARGET}**)
    is being offered for in-license under codename **{PROGRAM}**.

    - Founded 2019, Bay Area. ~40 FTEs.
    - Platform: structure-based design against complement receptors.
    - Financials, cap table, and prior raises are in the secure data room (not included here).
    """))
    out.append(_wtext("01_Corporate/term_sheet.md", f"""
    # {PROGRAM} — Non-Binding Term Sheet (DRAFT)
    Between **{LICENSOR}** ("Licensor") and **{LICENSEE}** ("Licensee").

    | Term | Value |
    |------|-------|
    | Asset | {ASSET} ({TARGET} {MODALITY}) |
    | Territory | Worldwide |
    | Upfront | $22M (illustrative, fictional) |
    | Development milestones | up to $180M |
    | Royalties | tiered, low-double-digit |
    | Diligence period | 60 days |

    Scientific due diligence to be led by {PEOPLE[2][0]} ({PEOPLE[2][1]}).
    This document is a fictional sample and not a real offer.
    """))
    return out


# ---- 02 Scientific --------------------------------------------------------- #
def scientific():
    out = []
    out.append(_wtext("02_Scientific/target_rationale.md", f"""
    # Target Rationale — {TARGET} in {INDICATION}
    **{PROGRAM} · Scientific Due Diligence**

    {TARGET} is implicated in complement-driven inflammation. {ASSET} is a selective
    {MODALITY} designed to reduce downstream chemotaxis without blocking the primary
    anaphylatoxin axis. Hypothesis: selective {TARGET} antagonism dampens tissue
    inflammation in {INDICATION} while sparing host defense.

    Key questions for Northwind Research diligence:
    - Strength of target-disease linkage (human genetics, patient tissue).
    - Selectivity vs. related receptors.
    - Translatability of the preclinical model to human {INDICATION}.
    """))
    out.append(_wtext("02_Scientific/moa_memo.md", f"""
    # Mechanism of Action Memo — {ASSET}
    {ASSET} binds the {TARGET} orthosteric pocket (Kd ~3.1 nM, fictional) and blocks
    ligand-induced receptor internalization. In vitro, it reduces neutrophil chemotaxis
    by ~70% at 100 nM (see 03_Nonclinical/assay_results.csv). No meaningful activity
    against the paralog receptor up to 10 µM (selectivity > 3000x).
    """))
    out.append(_wtext("02_Scientific/ind_readiness_memo.md", f"""
    # IND-Readiness Assessment — {ASSET} ({PROGRAM})
    **Prepared {TODAY:%Y-%m-%d} · FICTIONAL SAMPLE**

    | Domain | Status | Notes |
    |--------|--------|-------|
    | Pharmacology (primary) | Complete | in vitro + rodent efficacy |
    | Safety pharmacology | Partial | hERG done; CNS/respiratory pending |
    | GLP tox (rodent) | Complete | 28-day, NOAEL established |
    | GLP tox (non-rodent) | Planned | not started |
    | CMC | Early | GMP campaign not initiated |
    | Regulatory | Pre-IND | no FDA interaction yet |

    **Diligence verdict placeholder:** asset is late-discovery / early-preclinical; a
    non-rodent GLP tox and CMC scale-up are the gating items before IND. Recommend the
    Research team validate the {TARGET} target-disease linkage independently.
    """))
    return out


# ---- 03 Nonclinical (tables) ----------------------------------------------- #
def nonclinical():
    out = []
    # in vitro assay results
    assays = ["Binding Kd (nM)", "Functional IC50 (nM)", "Chemotaxis inhibition (%)",
              "Selectivity vs paralog (fold)", "hERG IC50 (µM)", "Plasma protein binding (%)"]
    rows = []
    for i, a in enumerate(assays):
        for rep in range(1, 4):
            val = {
                0: round(random.uniform(2.5, 4.0), 2),
                1: round(random.uniform(8, 25), 1),
                2: round(random.uniform(60, 80), 1),
                3: random.randint(2000, 4000),
                4: round(random.uniform(12, 30), 1),
                5: round(random.uniform(88, 97), 1),
            }[i]
            rows.append([ASSET, a, rep, val, "fictional"])
    out.append(_wcsv("03_Nonclinical/assay_results.csv",
                     ["compound", "assay", "replicate", "value", "note"], rows))

    # PK/PD (rodent)
    rows = []
    for sp in ["mouse", "rat"]:
        for dose in [1, 3, 10, 30]:
            rows.append([ASSET, sp, dose,
                         round(random.uniform(0.5, 6.0), 2),   # Cmax uM
                         round(random.uniform(1.0, 8.0), 2),   # AUC
                         round(random.uniform(1.5, 5.0), 1),   # t1/2 h
                         round(random.uniform(20, 60), 1)])    # F%
    out.append(_wcsv("03_Nonclinical/pk_pd.csv",
                     ["compound", "species", "dose_mpk", "cmax_uM", "auc", "t_half_h", "bioavail_pct"], rows))

    # tox summary (28-day GLP rodent)
    rows = []
    for sp in ["rat", "rat", "rat"]:
        for dose in [10, 30, 100]:
            rows.append([ASSET, sp, "28-day", dose,
                         random.choice(["NOAEL", "NOAEL", "adverse"]),
                         random.choice(["none", "mild ALT elevation", "reversible"])])
    out.append(_wcsv("03_Nonclinical/tox_summary.csv",
                     ["compound", "species", "study", "dose_mpk", "finding", "histopath"], rows))

    out.append(_wtext("03_Nonclinical/tox_narrative.md", f"""
    # 28-Day GLP Tox Narrative — {ASSET} (rat)
    NOAEL established at 30 mg/kg/day. At 100 mg/kg, mild, reversible ALT elevation
    observed without histopathological correlate. No CNS or cardiovascular signals in the
    rodent study. Non-rodent GLP tox not yet performed. (Fictional sample data.)
    """))
    return out


# ---- 04 CMC ---------------------------------------------------------------- #
def cmc():
    out = []
    rows = []
    for month in [0, 1, 3, 6, 12]:
        for cond in ["25C/60RH", "40C/75RH"]:
            purity = round(99.5 - month * (0.05 if cond.startswith("25") else 0.18)
                           - random.uniform(0, 0.1), 2)
            rows.append([ASSET, "API", cond, month, purity, round(100 - purity, 2)])
    out.append(_wcsv("04_CMC/stability.csv",
                     ["compound", "material", "condition", "timepoint_month", "purity_pct", "total_impurities_pct"], rows))
    out.append(_wtext("04_CMC/formulation_note.md", f"""
    # CMC / Formulation Note — {ASSET}
    Current material is research-grade; no GMP campaign initiated. Salt form selected
    (fictional). Solubility supports oral dosing. Scale-up and GMP are gating items for
    IND per the readiness memo.
    """))
    return out


# ---- 05 IP ----------------------------------------------------------------- #
def ip():
    out = []
    rows = [
        ["US2024-XXXX01", "composition of matter", "2024-02-11", "pending", "priority"],
        ["WO2024-XXXX02", "method of use", "2024-08-03", "pending", "PCT"],
        ["US2025-XXXX03", "formulation", "2025-01-20", "pending", "continuation"],
    ]
    out.append(_wcsv("05_IP/patent_family.csv",
                     ["application_no", "type", "filing_date", "status", "note"], rows))
    out.append(_wtext("05_IP/fto_memo.md", f"""
    # Freedom-to-Operate Summary — {PROGRAM} (FICTIONAL)
    Composition-of-matter application pending; no blocking third-party art identified in
    this sample. A full FTO opinion is out of scope for this data-room sample.
    """))
    return out


def main():
    print(f"Generating fictional licensing package '{PROGRAM}' ({ASSET}) -> {OUT_DIR}")
    manifest = []
    for group in (corporate, scientific, nonclinical, cmc, ip):
        manifest.extend(group())

    # data-room index / manifest
    mpath = os.path.join(OUT_DIR, "data_room", "manifest.csv")
    with open(mpath, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "content_kind", "size_or_rows", "program", "asset"])
        for relpath, kind, n in manifest:
            w.writerow([relpath, kind, n, PROGRAM, ASSET])

    docs = sum(1 for _, k, _ in manifest if k == "doc")
    tables = sum(1 for _, k, _ in manifest if k == "table")
    print(f"\nWrote {len(manifest)} data-room artifacts: {docs} docs + {tables} tables")
    for relpath, kind, n in manifest:
        print(f"  [{kind:5}] {relpath}")
    print(f"\nManifest: data_room/manifest.csv")
    print("All names/values are fictional (no real pharma brands).")


if __name__ == "__main__":
    main()
