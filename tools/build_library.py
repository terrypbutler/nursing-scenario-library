"""Validate YAML scenarios and build the JSON library consumed by the app."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator
import yaml


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = ROOT / "scenarios"
SCHEMA_PATH = ROOT / "schema" / "scenario.schema.json"
DIST_DIR = ROOT / "dist"
CASE_ID = re.compile(r"^PAT-\d{3}$")
FORBIDDEN_IDENTITY_KEYS = {
    "date_of_birth",
    "dob",
    "nhs_number",
    "hospital_number",
    "address",
    "postcode",
}
REQUIRED_AI_PROHIBITIONS = {"observations", "diagnosis", "treatment", "judgement"}


def safety_errors(case: dict, source: Path) -> list[str]:
    errors: list[str] = []
    case_id = str(case.get("case_id", ""))
    prefix = source.name
    if not CASE_ID.fullmatch(case_id):
        errors.append(f"{prefix}: case_id must look like PAT-005")
    if source.stem != case_id:
        errors.append(f"{prefix}: filename must match case_id ({case_id}.yaml)")
    if case.get("synthetic_data_notice") != "Entirely fictional training case":
        errors.append(f"{prefix}: the fictional-data notice must not be changed")
    patient = case.get("patient", {})
    forbidden = {str(key).casefold() for key in patient} & FORBIDDEN_IDENTITY_KEYS
    if forbidden:
        errors.append(f"{prefix}: direct identity fields are forbidden: {sorted(forbidden)}")

    actions = case.get("allowed_actions", [])
    action_ids = [item.get("action_id") for item in actions]
    if len(action_ids) != len(set(action_ids)):
        errors.append(f"{prefix}: action_id values must be unique")
    responses = case.get("dialogue", {}).get("action_responses", {})
    missing_responses = set(action_ids) - set(responses)
    if missing_responses:
        errors.append(
            f"{prefix}: missing dialogue responses for {sorted(missing_responses)}"
        )

    for item in case.get("clinical", {}).get("prescribed_items", []):
        if set(item) != {"order_id", "display_text", "dose_source"}:
            errors.append(f"{prefix}: prescription fixtures may not contain dose fields")
        if "simulated prescription chart" not in str(
            item.get("dose_source", "")
        ).casefold():
            errors.append(
                f"{prefix}: dose_source must refer to the simulated prescription chart"
            )

    prohibited = " ".join(
        str(item) for item in case.get("ai_contract", {}).get("must_not_generate", [])
    ).casefold()
    for concept in REQUIRED_AI_PROHIBITIONS:
        if concept not in prohibited:
            errors.append(f"{prefix}: AI prohibition must mention {concept}")
    if case.get("debrief", {}).get("automatic_competence_decision") is not False:
        errors.append(f"{prefix}: automatic competence decisions must be false")
    return errors


def load_cases(approved_only: bool) -> list[dict]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    cases: list[dict] = []
    errors: list[str] = []
    for source in sorted(SCENARIO_DIR.glob("PAT-*.yaml")):
        try:
            case = yaml.safe_load(source.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{source.name}: invalid YAML: {exc}")
            continue
        if not isinstance(case, dict):
            errors.append(f"{source.name}: scenario must be a YAML object")
            continue
        for issue in validator.iter_errors(case):
            location = ".".join(str(part) for part in issue.absolute_path) or "root"
            errors.append(f"{source.name}:{location}: {issue.message}")
        errors.extend(safety_errors(case, source))
        if not approved_only or case.get("publication_status") == "approved":
            cases.append(case)

    ids = [case.get("case_id") for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("case_id values must be unique across the library")
    if not cases:
        errors.append("the selected library contains no scenarios")
    if errors:
        print("Scenario library validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    return cases


def build(approved_only: bool) -> None:
    cases = load_cases(approved_only)
    DIST_DIR.mkdir(exist_ok=True)
    scenario_dist = DIST_DIR / "scenarios"
    scenario_dist.mkdir(exist_ok=True)
    for old_file in scenario_dist.glob("PAT-*.json"):
        old_file.unlink()
    for case in cases:
        target = scenario_dist / f"{case['case_id']}.json"
        target.write_text(
            json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    library = {
        "schema_version": "0.2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cases": cases,
    }
    (DIST_DIR / "library.json").write_text(
        json.dumps(library, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Built {len(cases)} validated scenario(s) in {DIST_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--approved-only",
        action="store_true",
        help="Publish only scenarios whose publication_status is approved.",
    )
    args = parser.parse_args()
    build(args.approved_only)
