import argparse
import subprocess
import sys
from pathlib import Path
import json
from policy.policy_mapper import map_policy

BASE = Path(__file__).resolve().parent


def run_step(name, command):
    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    result = subprocess.run(
        command,
        cwd=BASE,
        text=True
    )

    if result.returncode != 0:
        print()
        print(f"FAILED: {name}")
        sys.exit(result.returncode)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--policy-dir",
        type=Path,
        required=True,
        help="Directory containing policy.json and mapped_policy.json"
    )

    args = parser.parse_args()

    policy_dir = args.policy_dir.resolve()

    policy_file = policy_dir / "policy.json"
    mapped_file = policy_dir / "mapped_policy.json"
    rego_file = policy_dir / "generated_policy.rego"
    validation_file = policy_dir / "opa_validation_results.xlsx"

    if not policy_file.exists():
        raise FileNotFoundError(policy_file)

    # Generate mapped_policy.json from the selected policy.json
    with open(policy_file, "r", encoding="utf-8") as f:
        policy_data = json.load(f)

    dataset_columns = [
        "record_id",
        "customer_name",
        "email",
        "phone",
        "address",
        "dob",
        "gender",
        "passport_number",
        "ni_number",
        "credit_card_number",
        "bank_account",
        "medical_condition",
        "ethnicity",
        "religion",
        "political_view",
        "employee_id",
        "department",
        "job_role",
        "customer_id",
        "ip_address",
        "feedback",
    ]

    mapped_policy = map_policy(
        policy_data,
        dataset_columns
    )

    with open(mapped_file, "w", encoding="utf-8") as f:
        json.dump(mapped_policy, f, indent=2, ensure_ascii=False)

    print(f"Generated mapped policy: {mapped_file}")

    # 1. Python policy evaluation
    run_step(
        "PYTHON POLICY ENGINE",
        [
            sys.executable,
            "policy_engine.py",
            "--policy",
            str(policy_file),
        ]
    )

    # 2. Rego generation
    run_step(
        "REGO GENERATION",
        [
            sys.executable,
            "opa/rego_generator.py",
            "--policy",
            str(policy_file),
            "--mapped",
            str(mapped_file),
            "--output",
            str(rego_file),
        ]
    )

    # 3. OPA syntax check
    run_step(
        "OPA SYNTAX CHECK",
        [
            "opa",
            "check",
            str(rego_file),
        ]
    )

    # 4. Python vs OPA validation
    run_step(
    "OPA VALIDATION",
    [
        sys.executable,
        "-c",
        "from opa.opa_validator import evaluate; "
        f"evaluate(policy_file=r'{policy_file}', "
        f"mapped_file=r'{mapped_file}', "
        f"rego_file=r'{rego_file}', "
        f"output_file=r'{validation_file}')"
    ]
)

    print()
    print("=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"Policy: {policy_file}")
    print(f"Rego:   {rego_file}")
    print(f"Validation: {validation_file}")


if __name__ == "__main__":
    main()