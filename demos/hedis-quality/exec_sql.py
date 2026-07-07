"""Execute a multi-statement SQL string (already var-substituted) via the Databricks
SQL Statement Execution API, one statement at a time. Reads SQL from stdin.

Env: DATABRICKS_PROFILE (for the CLI), WAREHOUSE_ID.
Usage:  envsubst < file.sql | python3 exec_sql.py
Exits non-zero if any statement fails.
"""
import json
import os
import re
import subprocess
import sys


def split_statements(sql: str):
    # strip full-line and trailing -- comments (no -- appears inside our string literals)
    lines = []
    for ln in sql.splitlines():
        i = ln.find("--")
        if i != -1:
            ln = ln[:i]
        lines.append(ln)
    cleaned = "\n".join(lines)
    return [s.strip() for s in cleaned.split(";") if s.strip()]


def run(stmt: str, warehouse: str, profile: str):
    payload = json.dumps({
        "warehouse_id": warehouse,
        "statement": stmt,
        "wait_timeout": "50s",
        "on_wait_timeout": "CANCEL",
    })
    out = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/sql/statements",
         "--profile", profile, "--json", payload],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        return "CLI_ERROR", out.stderr.strip()
    d = json.loads(out.stdout)
    st = d.get("status", {})
    return st.get("state", "?"), st.get("error", {}).get("message", "")


def main():
    profile = os.environ.get("DATABRICKS_PROFILE") or os.environ["PROFILE"]
    warehouse = os.environ["WAREHOUSE_ID"]
    sql = sys.stdin.read()
    stmts = split_statements(sql)
    print(f"      {len(stmts)} statement(s)")
    for i, stmt in enumerate(stmts, 1):
        state, err = run(stmt, warehouse, profile)
        head = " ".join(stmt.split())[:70]
        print(f"      [{i}/{len(stmts)}] {state:9} {head}")
        if state not in ("SUCCEEDED",):
            print(f"      ERROR: {err}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
