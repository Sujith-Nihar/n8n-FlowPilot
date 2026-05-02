#!/usr/bin/env python3
"""
load_registry.py
----------------
Reads your 3 local JSON files and loads them into Supabase.

Files it reads:
  - n8n-registry-extractor/output/n8n_registry_normalized.json  → n8n_node_registry + n8n_credential_registry
  - n8n-registry-extractor/output/n8n_operation_index.json      → n8n_operation_index

Usage:
  pip install supabase python-dotenv
  python load_registry.py

Make sure you have a .env file with:
  SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
  SUPABASE_SERVICE_KEY=eyJ...
"""

import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# ─── Load env ────────────────────────────────────────────────────────────────

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env file")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── File Paths ───────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
NORMALIZED_PATH = BASE_DIR / "n8n-registry-extractor" / "output" / "n8n_registry_normalized.json"
OPERATION_INDEX_PATH = BASE_DIR / "n8n-registry-extractor" / "output" / "n8n_operation_index.json"

# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_json(path: Path, label: str) -> dict:
    if not path.exists():
        print(f"ERROR: {label} not found at: {path}")
        sys.exit(1)
    print(f"  Loading {label}...")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def chunk(lst: list, size: int):
    """Split a list into chunks of given size."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]

def insert_batch(table: str, rows: list, batch_size: int = 100):
    """
    Insert rows in batches. Uses upsert to handle re-runs gracefully.
    """
    total = len(rows)
    inserted = 0
    errors = 0

    for batch in chunk(rows, batch_size):
        try:
            supabase.table(table).upsert(batch).execute()
            inserted += len(batch)
            print(f"    ✔  {inserted}/{total} rows inserted into {table}", end="\r")
            time.sleep(0.1)  # Be gentle on free tier rate limits
        except Exception as e:
            errors += 1
            print(f"\n    ✘  Batch error in {table}: {e}")

    print(f"    ✔  {inserted}/{total} rows inserted into {table}  ({errors} batch errors)")
    return inserted, errors

# ─── Loaders ─────────────────────────────────────────────────────────────────

def load_node_registry(data: dict):
    """
    Load normalized nodes → n8n_node_registry table.
    Deduplicates by node_type before inserting.
    """
    print("\n[1/3] Loading node registry...")
    nodes = data.get("nodes", [])
    print(f"  Found {len(nodes)} nodes in source")

    rows = []
    seen_node_types = set()  # Track duplicates

    for node in nodes:
        node_type = node.get("node_type")

        # Skip rows with no node_type
        if not node_type:
            continue

        # Skip duplicate node_types — keep first occurrence only
        if node_type in seen_node_types:
            continue
        seen_node_types.add(node_type)

        inputs_raw = node.get("inputs", [])
        outputs_raw = node.get("outputs", [])

        row = {
            "node_type":               node_type,
            "node_name":               node.get("node_name") or node_type.split(".")[-1],
            "display_name":            node.get("display_name"),
            "description":             node.get("description"),
            "versions":                json.dumps(node.get("versions", [])),
            "default_version":         float(node.get("default_version") or 1),
            "group_name":              json.dumps(node.get("group", [])),
            "inputs":                  json.dumps(inputs_raw),
            "outputs":                 json.dumps(outputs_raw),
            "credentials":             json.dumps(node.get("credentials", [])),
            "properties":              json.dumps(node.get("properties", [])),
            "defaults":                json.dumps(node.get("defaults", {})),
            "resources":               json.dumps(node.get("resources", [])),
            "operations":              json.dumps(node.get("operations", [])),
            "required_fields":         json.dumps(node.get("required_fields", [])),
            "search_text":             node.get("search_text", ""),
            "is_valid_for_generation": node.get("is_valid_for_generation", True),
            "issues":                  json.dumps(node.get("issues", [])),
            "source_package":          node.get("source_package"),
            "source_file":             node.get("source_file"),
        }
        rows.append(row)

    print(f"  After dedup: {len(rows)} unique nodes to insert")
    return insert_batch("n8n_node_registry", rows)


def load_credential_registry(data: dict):
    """
    Load credentials → n8n_credential_registry table.
    Deduplicates by credential_name before inserting.
    """
    print("\n[2/3] Loading credential registry...")
    credentials = data.get("credentials", [])
    print(f"  Found {len(credentials)} credentials in source")

    rows = []
    seen_cred_names = set()

    for cred in credentials:
        credential_name = cred.get("credential_name") or cred.get("name")
        if not credential_name:
            continue

        if credential_name in seen_cred_names:
            continue
        seen_cred_names.add(credential_name)

        row = {
            "credential_name":   credential_name,
            "display_name":      cred.get("display_name") or cred.get("displayName"),
            "documentation_url": cred.get("documentation_url") or cred.get("documentationUrl"),
            "properties":        json.dumps(cred.get("properties", [])),
            "source_package":    cred.get("source_package"),
            "source_file":       cred.get("source_file"),
        }
        rows.append(row)

    print(f"  After dedup: {len(rows)} unique credentials to insert")
    return insert_batch("n8n_credential_registry", rows)


def load_operation_index(data: dict):
    """
    Load operation index → n8n_operation_index table.
    """
    print("\n[3/3] Loading operation index...")
    operations = data.get("operations", [])
    print(f"  Found {len(operations)} operations to insert")

    rows = []

    for op in operations:
        if not op.get("node_type"):
            continue

        row = {
            "node_type":       op.get("node_type"),
            "node_name":       op.get("node_name"),
            "display_name":    op.get("display_name"),
            "default_version": float(op.get("default_version") or 1),
            "resource":        op.get("resource"),
            "resource_name":   op.get("resource_name"),
            "operation":       op.get("operation"),
            "operation_name":  op.get("operation_name"),
            "action":          op.get("action", ""),
            "description":     op.get("description", ""),
            "credentials":     json.dumps(op.get("credentials", [])),
            "required_fields": json.dumps(op.get("required_fields", [])),
            "search_text":     op.get("search_text", ""),
        }
        rows.append(row)

    return insert_batch("n8n_operation_index", rows)

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  n8n Registry Loader → Supabase")
    print("=" * 60)
    print(f"  URL: {SUPABASE_URL}")
    print()

    # Load JSON files
    normalized_data = load_json(NORMALIZED_PATH, "n8n_registry_normalized.json")
    operation_data  = load_json(OPERATION_INDEX_PATH, "n8n_operation_index.json")

    print(f"  Registry:  {normalized_data.get('normalized_node_count', '?')} nodes,  {normalized_data.get('credential_count', '?')} credentials")
    print(f"  Ops Index: {operation_data.get('operation_count', '?')} operations")

    start = time.time()

    # Run all 3 loaders
    n_inserted,  n_errors  = load_node_registry(normalized_data)
    c_inserted,  c_errors  = load_credential_registry(normalized_data)
    op_inserted, op_errors = load_operation_index(operation_data)

    elapsed = round(time.time() - start, 1)

    # Summary
    print("\n" + "=" * 60)
    print("  LOAD COMPLETE")
    print("=" * 60)
    print(f"  n8n_node_registry:       {n_inserted} rows  ({n_errors} errors)")
    print(f"  n8n_credential_registry: {c_inserted} rows  ({c_errors} errors)")
    print(f"  n8n_operation_index:     {op_inserted} rows  ({op_errors} errors)")
    print(f"  Total time:              {elapsed}s")
    print()

    if n_errors + c_errors + op_errors == 0:
        print("  ✔  All data loaded successfully. Ready for FastAPI backend.")
    else:
        print("  ⚠  Some batches had errors. Check output above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
