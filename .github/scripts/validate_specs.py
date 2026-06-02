#!/usr/bin/env python3
"""Validate crtx spec schemas and example documents.

For every specs/v<N>/ directory:
  1. envelope.schema.json and events.schema.json must be parseable JSON
     Schema 2020-12 documents.
  2. specs/v<N>/examples/*.json (top-level, non-recursive) must validate
     against envelope.schema.json.
  3. specs/v<N>/examples/events/*.json must validate against the
     corresponding $defs entry in events.schema.json. The mapping is
     filename-stem snake_case -> PascalCase + "Payload"
     (e.g. user_received.json -> UserReceivedPayload).

Fails on the first error per file but continues across files so one CI run
reports every problem.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]


def stem_to_def_name(stem: str) -> str:
    """user_received -> UserReceivedPayload."""
    return "".join(part.capitalize() for part in stem.split("_")) + "Payload"


def validate_schema(path: Path) -> list[str]:
    errs: list[str] = []
    try:
        schema = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [f"{path}: invalid JSON: {e}"]
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as e:  # noqa: BLE001 — surface any schema-meta error
        errs.append(f"{path}: not a valid Draft 2020-12 schema: {e}")
    return errs


def validate_doc(doc_path: Path, schema: dict, label: str) -> list[str]:
    errs: list[str] = []
    try:
        doc = json.loads(doc_path.read_text())
    except json.JSONDecodeError as e:
        return [f"{doc_path}: invalid JSON: {e}"]
    validator = Draft202012Validator(schema)
    for err in validator.iter_errors(doc):
        path = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errs.append(f"{doc_path} vs {label} at {path}: {err.message}")
    return errs


def main() -> int:
    spec_dirs = sorted((REPO_ROOT / "specs").glob("v*"))
    if not spec_dirs:
        print(f"no specs/v*/ dirs under {REPO_ROOT}", file=sys.stderr)
        return 1

    all_errs: list[str] = []
    for vdir in spec_dirs:
        print(f"=== {vdir.relative_to(REPO_ROOT)} ===")
        env_schema_path = vdir / "envelope.schema.json"
        evt_schema_path = vdir / "events.schema.json"

        for sp in (env_schema_path, evt_schema_path):
            if not sp.exists():
                all_errs.append(f"missing schema: {sp}")
                print(f"  MISS {sp.name}")
                continue
            schema_errs = validate_schema(sp)
            if schema_errs:
                all_errs.extend(schema_errs)
                print(f"  FAIL schema {sp.name}")
            else:
                print(f"  OK   schema {sp.name}")

        # Envelope examples (non-recursive)
        if env_schema_path.exists():
            env_schema = json.loads(env_schema_path.read_text())
            for ex in sorted((vdir / "examples").glob("*.json")):
                ex_errs = validate_doc(ex, env_schema, "envelope.schema.json")
                if ex_errs:
                    all_errs.extend(ex_errs)
                    print(f"  FAIL envelope {ex.relative_to(vdir)}")
                else:
                    print(f"  OK   envelope {ex.relative_to(vdir)}")

        # Event examples: events/*.json -> $defs/<PascalCase>Payload
        if evt_schema_path.exists():
            evt_schema = json.loads(evt_schema_path.read_text())
            evt_defs = evt_schema.get("$defs", {})
            for ex in sorted((vdir / "examples" / "events").glob("*.json")):
                def_name = stem_to_def_name(ex.stem)
                if def_name not in evt_defs:
                    all_errs.append(
                        f"{ex}: no $defs/{def_name} in events.schema.json"
                    )
                    print(f"  FAIL event {ex.relative_to(vdir)} (no def {def_name})")
                    continue
                sub_schema = {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$ref": f"#/$defs/{def_name}",
                    "$defs": evt_defs,
                }
                ex_errs = validate_doc(ex, sub_schema, def_name)
                if ex_errs:
                    all_errs.extend(ex_errs)
                    print(f"  FAIL event {ex.relative_to(vdir)} vs {def_name}")
                else:
                    print(f"  OK   event {ex.relative_to(vdir)} vs {def_name}")

    if all_errs:
        print(f"\n{len(all_errs)} error(s):", file=sys.stderr)
        for e in all_errs:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("\nall validations passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
