"""Generate synthetic HEDIS demo source data as raw *files* + Data Cloud seed tables.

Two provenance groups, matching the demo story:

  1. HEDIS files  (ingested via Auto Loader in the Lakeflow pipeline)
       claims/claims_*.csv        - medical claims with ICD-10 / CPT codes + paid amounts
       enrollment/enrollment_*.csv- member-month enrollment spans (denominator eligibility)

  2. Salesforce Data Cloud dimensions (seeded into UC tables, read as dims)
       datacloud/member.csv       - member demographics + chronic conditions
       datacloud/provider.csv     - provider NPI / specialty

  3. Reference (small, static)
       reference/measure.csv      - 18 HEDIS/CMS quality measures
       reference/county.csv       - county FIPS reference

Deterministic (seed=42), Python stdlib only, mirrors the repo's other generators.
Files are written under OUT_DIR; run_demo.sh uploads groups (1) to the UC Volume
landing zone and (2)/(3) are loaded into tables by 10_datacloud_dims.sql.
"""
import csv
import os
import random
from datetime import date, timedelta

SEED = 42
OUT_DIR = os.environ.get("HEDIS_OUT_DIR", "/tmp/hedis_demo")

N_MEMBERS = 1000
N_PROVIDERS = 120
N_CLAIMS = 10000
MEASURE_YEAR = 2025
CLAIM_FILE_SHARDS = 4  # split claims across files so Auto Loader shows incremental ingest

random.seed(SEED)

# 18 HEDIS/CMS-style quality measures (fictional-safe: standard measure abbreviations)
MEASURES = [
    ("CBP", "Controlling High Blood Pressure", "cardiovascular", 0.70, "higher", 1, 1),
    ("CDC-HbA1c", "Comprehensive Diabetes Care: HbA1c Testing", "diabetes", 0.85, "higher", 1, 1),
    ("CDC-Eye", "Comprehensive Diabetes Care: Eye Exam", "diabetes", 0.60, "higher", 1, 1),
    ("CDC-Neph", "Diabetes: Kidney Health Evaluation", "diabetes", 0.65, "higher", 0, 1),
    ("BCS", "Breast Cancer Screening", "preventive", 0.75, "higher", 1, 1),
    ("COL", "Colorectal Cancer Screening", "preventive", 0.70, "higher", 1, 1),
    ("CIS", "Childhood Immunization Status", "preventive", 0.80, "higher", 0, 1),
    ("AWC", "Adolescent Well-Care Visits", "preventive", 0.55, "higher", 0, 0),
    ("SPD", "Statin Therapy for Cardiovascular Disease", "cardiovascular", 0.80, "higher", 0, 1),
    ("AMR", "Asthma Medication Ratio", "respiratory", 0.65, "higher", 0, 1),
    ("FUH", "Follow-Up After Hospitalization for Mental Illness", "behavioral", 0.55, "higher", 1, 1),
    ("AMM", "Antidepressant Medication Management", "behavioral", 0.60, "higher", 0, 1),
    ("IET", "Initiation & Engagement of SUD Treatment", "behavioral", 0.45, "higher", 0, 0),
    ("PPC-Pre", "Prenatal Care Timeliness", "maternal", 0.80, "higher", 0, 1),
    ("PPC-Post", "Postpartum Care", "maternal", 0.75, "higher", 0, 1),
    ("MPM", "Medication Monitoring for Long-Term Meds", "safety", 0.85, "higher", 0, 1),
    ("PCR", "Plan All-Cause Readmissions", "utilization", 0.12, "lower", 1, 1),
    ("AAB", "Avoidance of Antibiotic Tx for Bronchitis", "utilization", 0.30, "higher", 0, 0),
]

CHRONIC = ["diabetes", "hypertension", "asthma", "chf", "copd", "depression", "ckd", "none"]
AID_CATEGORY = ["TANF", "Aged", "Blind/Disabled", "Expansion", "CHIP"]
STATES = ["MA", "NC", "CA", "TX", "NY", "OH", "GA", "PA", "IL", "FL"]
SPECIALTIES = ["Family Medicine", "Internal Medicine", "Cardiology", "Endocrinology",
               "OB/GYN", "Pediatrics", "Behavioral Health", "Nephrology", "Oncology"]
ICD10 = ["E11.9", "I10", "J45.909", "I50.9", "J44.9", "F32.9", "N18.3", "Z00.00",
         "E78.5", "M54.5", "R51", "K21.9"]
CPT = ["99213", "99214", "83036", "82947", "77067", "45378", "80061", "93000",
       "90471", "36415", "99385", "99396"]


def _w(path, header, rows):
    full = os.path.join(OUT_DIR, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return full, len(rows)


def gen_members():
    rows = []
    for i in range(1, N_MEMBERS + 1):
        mid = f"M{i:06d}"
        birth = date(random.randint(1945, 2018), random.randint(1, 12), random.randint(1, 28))
        conds = random.sample(CHRONIC, k=random.randint(0, 3))
        rows.append([
            mid, birth.isoformat(),
            random.choice(["F", "M"]),
            random.choice(STATES),
            f"{random.randint(1001, 56045):05d}",  # county_fips
            random.choice(AID_CATEGORY),
            "|".join(sorted(set(conds))) or "none",
            random.choice(["EN", "ES", "PT", "ZH", "VI"]),
        ])
    return _w("datacloud/member.csv",
              ["member_id", "birth_date", "sex", "state", "county_fips",
               "aid_category", "chronic_conditions", "preferred_language"], rows)


def gen_providers():
    rows = []
    for i in range(1, N_PROVIDERS + 1):
        rows.append([
            f"{1000000000 + i}",  # provider_npi (10-digit)
            random.choice(SPECIALTIES),
            random.choice(["PCP", "Specialist", "Facility"]),
            random.choice(STATES),
            random.choice(["Y", "N"]),  # in_network
        ])
    return _w("datacloud/provider.csv",
              ["provider_npi", "specialty", "provider_type", "state", "in_network"], rows)


def gen_measures():
    rows = [[m[0], m[1], m[2], m[3], m[4], m[5], m[6], MEASURE_YEAR] for m in MEASURES]
    return _w("reference/measure.csv",
              ["measure_id", "measure_name", "domain", "regulatory_threshold",
               "reporting_direction", "star_rating_flag", "high_priority_flag",
               "measurement_year"], rows)


def gen_county():
    rows = []
    seen = set()
    for _ in range(300):
        fips = f"{random.randint(1001, 56045):05d}"
        if fips in seen:
            continue
        seen.add(fips)
        rows.append([fips, random.choice(STATES),
                     random.choice(["Urban", "Suburban", "Rural"]),
                     random.choice(["Northeast", "South", "Midwest", "West"])])
    return _w("reference/county.csv",
              ["county_fips", "state", "rurality", "region"], rows)


def gen_enrollment():
    """One row per member-month for MEASURE_YEAR (continuous-enrollment denominator)."""
    rows = []
    for i in range(1, N_MEMBERS + 1):
        mid = f"M{i:06d}"
        # most members enrolled all 12 months; some partial
        start_m = 1 if random.random() < 0.85 else random.randint(1, 6)
        end_m = 12 if random.random() < 0.9 else random.randint(7, 12)
        for m in range(start_m, end_m + 1):
            rows.append([mid, f"{MEASURE_YEAR}-{m:02d}", "ENROLLED",
                         random.choice(AID_CATEGORY)])
    return _w("enrollment/enrollment_2025.csv",
              ["member_id", "month", "enrollment_status", "aid_category"], rows)


def gen_claims():
    """Medical claims split across shard files to demonstrate incremental Auto Loader."""
    provider_npis = [f"{1000000000 + i}" for i in range(1, N_PROVIDERS + 1)]
    all_rows = []
    for c in range(1, N_CLAIMS + 1):
        mid = f"M{random.randint(1, N_MEMBERS):06d}"
        svc = date(MEASURE_YEAR, random.randint(1, 12), random.randint(1, 28))
        ndx = random.randint(1, 3)
        nproc = random.randint(1, 3)
        all_rows.append([
            f"CLM{c:08d}", mid, random.choice(provider_npis), svc.isoformat(),
            random.choice(["Professional", "Institutional", "Pharmacy"]),
            "|".join(random.sample(ICD10, ndx)),
            "|".join(random.sample(CPT, nproc)),
            round(random.uniform(45, 4200), 2),   # billed_amount
            round(random.uniform(20, 2600), 2),   # paid_amount
            random.choice(["PAID", "PAID", "PAID", "DENIED"]),
        ])
    header = ["claim_id", "member_id", "provider_npi", "service_date", "claim_type",
              "dx_codes", "proc_codes", "billed_amount", "paid_amount", "claim_status"]
    written = []
    shard_size = len(all_rows) // CLAIM_FILE_SHARDS
    for s in range(CLAIM_FILE_SHARDS):
        lo = s * shard_size
        hi = len(all_rows) if s == CLAIM_FILE_SHARDS - 1 else (s + 1) * shard_size
        written.append(_w(f"claims/claims_{MEASURE_YEAR}_{s + 1:02d}.csv", header, all_rows[lo:hi]))
    return written


def main():
    print(f"Generating HEDIS demo data -> {OUT_DIR} (seed={SEED})")
    results = [gen_members(), gen_providers(), gen_measures(), gen_county(), gen_enrollment()]
    results.extend(gen_claims())
    print("\nWrote:")
    for path, n in results:
        rel = os.path.relpath(path, OUT_DIR)
        print(f"  {rel:40s} {n:>7,} rows")
    print("\nGroups:")
    print("  HEDIS files (Auto Loader landing) : claims/, enrollment/")
    print("  Salesforce Data Cloud dims        : datacloud/")
    print("  Reference                         : reference/")


if __name__ == "__main__":
    main()
