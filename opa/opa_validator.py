import json
import subprocess
import sys
from pathlib import Path
import argparse
import pandas as pd


BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from policy_engine import check_record


INPUT_FILE = BASE / "generated_data" / "synthetic_data.xlsx"
REGO_FILE = BASE / "opa" / "generated_policy.rego"
TEMP_INPUT = BASE / "opa" / "_opa_input.json"
OUTPUT_FILE = BASE / "opa" / "opa_validation_results.xlsx"



def run_opa(record):
    input_data = {
        "record": record
    }

    with open(TEMP_INPUT, "w", encoding="utf-8") as f:
        json.dump(input_data, f, indent=2, default=str)

    process = subprocess.run(
        [
            "opa",
            "eval",
            "-d",
            str(REGO_FILE),
            "-i",
            str(TEMP_INPUT),
            "data.generated_policy.result",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
    )

    if process.returncode != 0:
        raise RuntimeError(process.stderr)

    result = json.loads(process.stdout)

    return result["result"][0]["expressions"][0]["value"]


def normalize_rules(value):
    if not value:
        return []

    if isinstance(value, list):
        return sorted(str(x).strip() for x in value)

    return sorted(
        x.strip()
        for x in str(value).split(";")
        if x.strip()
    )


def evaluate(
    policy_file=None,
    mapped_file=None,
    rego_file=None,
    output_file=None,
):
    global REGO_FILE, OUTPUT_FILE

    if rego_file:
        REGO_FILE = Path(rego_file)

    if output_file:
        OUTPUT_FILE = Path(output_file)

    mapped_policy = None

    if mapped_file:
        with open(mapped_file, "r", encoding="utf-8") as f:
            mapped_policy = json.load(f)

    df = pd.read_excel(INPUT_FILE)

    results = []

    print(f"Records loaded: {len(df)}")
    print("Running OPA validation...")

    for index, row in df.iterrows():

        record = row.to_dict()

        for key, value in record.items():
            if pd.isna(value):
                record[key] = ""

        opa_result = run_opa(record)

        python_result = check_record(
            row,
            mapped_policy=mapped_policy,
        )

        python_decision = str(
            python_result.get("expected_outcome", "")
        ).strip()

        python_rules = normalize_rules(
            python_result.get("expected_rule_triggers", "")
        )

        opa_decision = str(
            opa_result.get("decision", "")
        ).strip()

        opa_rules = normalize_rules(
            opa_result.get("triggered_rules", [])
        )

        decision_match = (
            python_decision == opa_decision
        )

        rule_match = (
            python_rules == opa_rules
        )

        results.append({
            "record_id": row.get("record_id", ""),
            "python_decision": python_decision,
            "opa_decision": opa_decision,
            "decision_match": decision_match,
            "python_rules": "; ".join(python_rules),
            "opa_rules": "; ".join(opa_rules),
            "rule_match": rule_match,
            "validation_status": (
                "MATCH"
                if decision_match and rule_match
                else "MISMATCH"
            ),
        })

        if (index + 1) % 10 == 0:
            print(f"Validated {index + 1}/{len(df)} records")

    result_df = pd.DataFrame(results)

    result_df.to_excel(
        OUTPUT_FILE,
        index=False
    )

    total = len(result_df)

    decision_matches = int(
        result_df["decision_match"].sum()
    )

    rule_matches = int(
        result_df["rule_match"].sum()
    )

    mismatches = int(
        (result_df["validation_status"] == "MISMATCH").sum()
    )

    print()
    print("========================================")
    print("OPA VALIDATION")
    print("========================================")
    print(f"Records tested:       {total}")
    print(f"Decision matches:     {decision_matches}")
    print(f"Decision mismatches:  {total - decision_matches}")
    print(f"Rule matches:         {rule_matches}")
    print(f"Rule mismatches:      {total - rule_matches}")
    print(f"Total mismatches:     {mismatches}")
    print()

    if mismatches == 0:
        print("STATUS: VALID")
    else:
        print("STATUS: MISMATCHES FOUND")

    print()
    print(f"Output: {OUTPUT_FILE}")

    if TEMP_INPUT.exists():
        TEMP_INPUT.unlink()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--mapped",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--rego",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    args = parser.parse_args()

    evaluate(
        policy_file=args.policy,
        mapped_file=args.mapped,
        rego_file=args.rego,
        output_file=args.output,
    )