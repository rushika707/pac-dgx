import re
import argparse
from pathlib import Path
from database import get_connection, init_db
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
from policy.policy_mapper import (
    semantic_concept,
    dataset_columns_for_concept,
)
from policy.policy_loader import load_policy
import json
from datetime import datetime
from database import get_connection, init_db
from policy.policy_mapper import map_policy
# ============================================================
# PATHS
# ============================================================

BASE = Path(__file__).resolve().parent

INPUT = BASE / "generated_data" / "synthetic_data.xlsx"
OUTPUT = BASE / "policy-dashboard" / "public" / "policy_results.xlsx"
DEFAULT_POLICY_FILE = BASE / "policy" / "policy.json"

parser = argparse.ArgumentParser()
parser.add_argument(
    "--policy",
    type=Path,
    default=DEFAULT_POLICY_FILE,
)
args = parser.parse_args()

POLICY_FILE = args.policy


# ============================================================
# LOAD POLICY
# ============================================================

policy = load_policy(POLICY_FILE)
import re


def contains_personal_identifier(text, record):
    if not text:
        return False

    text = str(text).lower()

    # Check values from mapped PII fields
    pii_fields = [
        "customer_name",
        "email",
        "phone",
        "address",
        "passport_number",
        "ni_number",
        "credit_card_number",
        "bank_account",
        "employee_id",
        "customer_id",
    ]

    for field in pii_fields:
        value = record.get(field)

        if value is None:
            continue

        value = str(value).strip()

        if value and value.lower() in text:
            return True

    return False

# ============================================================
# GENERIC POLICY EXTRACTION
# ============================================================

def extract_rules(policy):
    rules = {}

    def walk(value):
        if isinstance(value, dict):

            rule_id = (
                value.get("rule_id")
                or value.get("Rule ID")
                or value.get("ID")
            )

            if rule_id and not str(rule_id).startswith("DP-"):
                rules[str(rule_id)] = value

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(policy)

    return rules


def extract_decisions(policy):
    decisions = {}

    def walk(value):
        if isinstance(value, dict):

            for key in ("Decision", "decision"):
                if key in value:
                    decision = str(value[key]).strip()
                    decisions[decision] = value

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(policy)

    return decisions


RULES = extract_rules(policy)
DECISIONS = extract_decisions(policy)

print(f"Loaded executable rules: {len(RULES)}")

print("Loaded decisions:")
for decision in DECISIONS:
    print(f"  {decision}")


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(value):
    value = str(value).lower().strip()
    value = value.replace("_", " ")
    value = value.replace("-", " ")
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_column_name(value):
    return normalize_text(value)


# ============================================================
# GENERIC CONCEPT ALIASES
#
# These are semantic vocabulary mappings, NOT policy-rule
# mappings. They allow policy concepts to resolve to dataset
# columns without modifying policy.json.
# ============================================================
CONCEPT_ALIASES = {
    "full name": [
        "full name",
        "customer name",
        "customer_name",
        "name",
        "person name",
        "client name",
    ],

    "date of birth": [
        "date of birth",
        "dob",
        "birth date",
        "birthdate",
    ],

    "personal email address": [
        "personal email address",
        "personal email",
        "email address",
        "email",
        "contact email",
    ],

    "phone number": [
        "phone number",
        "phone",
        "mobile",
        "mobile number",
        "telephone",
        "telephone number",
    ],

    "postal address": [
        "postal address",
        "postal/home address",
        "home address",
        "address",
        "street address",
    ],

    "postcode": [
        "postcode",
        "postal code",
        "zip code",
        "zip",
    ],

    "gender": [
        "gender",
        "sex",
    ],

    "employee id": [
        "employee id",
        "employee identifier",
        "employee number",
    ],

    "department": [
        "department",
        "business unit",
        "team",
    ],

    "role": [
        "role",
        "job role",
        "job_role",
        "job title",
        "position",
    ],

    "customer id": [
        "customer id",
        "customer identifier",
        "client id",
        "client identifier",
        "user id",
        "user identifier",
    ],

    "account event details": [
        "account event details",
        "account event",
        "transaction details",
        "account activity",
        "account details",
    ],

    "free text": [
        "free text",
        "free-text",
        "comments",
        "comment",
        "notes",
        "feedback",
        "description",
        "text",
    ],
}


def build_dataset_columns(row):
    return {
        normalize_column_name(column): column
        for column in row.index
    }


def resolve_concept_columns(concept, row):
    """
    Resolve any policy concept to actual dataset columns
    through semantic meaning.
    """

    concept = str(concept).strip()

    # First map policy wording → semantic concept
    semantic = semantic_concept(concept)

    if semantic:
        candidates = dataset_columns_for_concept(semantic)

        # Keep only columns that actually exist
        return [
            column
            for column in candidates
            if column in row.index
        ]

    # Unknown concept:
    # allow direct dataset-column matching
    normalized = normalize_column_name(concept)

    for column in row.index:
        if normalize_column_name(column) == normalized:
            return [column]

    return []


# ============================================================
# RULE NORMALIZATION
# ============================================================

def get_rule_description(rule):
    for key in (
        "description",
        "Description",
        "PII type",
        "Sensitive data type",
        "Combination rule",
        "Policy statement",
    ):
        value = rule.get(key)

        if value:
            return str(value).strip()

    return ""


def get_rule_outcome(rule):
    for key in (
        "outcome",
        "Outcome",
        "Required outcome",
        "Required policy outcome",
    ):
        value = rule.get(key)

        if value:
            return str(value).strip()

    return ""


def get_examples(rule):
    value = (
        rule.get("examples")
        or rule.get("Examples")
        or []
    )

    if isinstance(value, str):
        return [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]

    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    return []


def normalize_rule(rule_id, rule):

    description = get_rule_description(rule)
    examples = get_examples(rule)

    execution = rule.get("execution", {})

    normalized = {
        "rule_id": rule_id,
        "description": description,
        "examples": examples,
        "outcome": get_rule_outcome(rule),
        "execution": execution,
        "raw": rule,
        "type": "unknown",
    }

    # Existing execution supplied by policy extraction
    if isinstance(execution, dict) and execution.get("type"):
        normalized["type"] = execution["type"]
        return normalized

    description_lower = description.lower()

    # Combination rules are identified from their structure,
    # not from their rule ID.
    if "+" in description:
        normalized["type"] = "combination"
        return normalized

    # Text rules
    if any(
        phrase in description_lower
        for phrase in (
            "free-text",
            "free text",
            "comments containing",
            "text containing",
            "notes containing",
        )
    ):
        normalized["type"] = "text"
        return normalized

    # Example-based field rule
    if examples:
        normalized["type"] = "field"
        return normalized

    return normalized


NORMALIZED_RULES = {
    rule_id: normalize_rule(rule_id, rule)
    for rule_id, rule in RULES.items()
}
def load_policy_for_evaluation(policy_file):
    global policy
    global RULES
    global NORMALIZED_RULES
    global DECISIONS

    policy = load_policy(Path(policy_file))

    RULES = extract_rules(policy)

    NORMALIZED_RULES = {
        rule_id: normalize_rule(rule_id, rule)
        for rule_id, rule in RULES.items()
    }

    DECISIONS = extract_decisions(policy)

# ============================================================
# VALUE CHECK
# ============================================================

def has_value(row, column):
    if column not in row.index:
        return False

    value = row[column]

    if pd.isna(value):
        return False

    return bool(str(value).strip())


# ============================================================
# EXECUTION DEFINED BY POLICY JSON
# ============================================================

def evaluate_execution(row, rule):

    execution = rule.get("execution")

    if not isinstance(execution, dict):
        return None

    execution_type = execution.get("type")

    # --------------------------------------------------------
    # FIELD
    # --------------------------------------------------------

    if execution_type == "field":

        fields = execution.get("fields", [])

        for group in fields:

            if isinstance(group, str):
                group = [group]

            for field in group:

                resolved = resolve_concept_columns(
                    field,
                    row,
                )

                if any(
                    has_value(row, column)
                    for column in resolved
                ):
                    return True

        return False

    # --------------------------------------------------------
    # COMBINATION
    # --------------------------------------------------------

    if execution_type == "combination":

        groups = execution.get("fields", [])

        if not groups:
            return False

        for group in groups:

            if isinstance(group, str):
                group = [group]

            group_found = False

            for field in group:

                resolved = resolve_concept_columns(
                    field,
                    row,
                )

                if any(
                    has_value(row, column)
                    for column in resolved
                ):
                    group_found = True
                    break

            if not group_found:
                return False

        return True

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    if execution_type == "text":

        fields = execution.get("fields", [])
        patterns = execution.get("patterns", [])

        for group in fields:

            if isinstance(group, str):
                group = [group]

            for field in group:

                resolved = resolve_concept_columns(
                    field,
                    row,
                )

                for column in resolved:

                    if not has_value(row, column):
                        continue

                    value = str(row[column])

                    for pattern in patterns:

                        try:
                            if re.search(
                                pattern,
                                value,
                                flags=re.IGNORECASE,
                            ):
                                return True

                        except re.error as error:
                            print(
                                f"Invalid regex in "
                                f"{rule['rule_id']}: {error}"
                            )

        return False

    return None


# ============================================================
# GENERIC DESCRIPTION PARSER FOR COMBINATION RULES
# ============================================================

def split_combination_description(description):
    """
    Extract the required concepts from a policy combination
    description while ignoring qualifying text.
    """

    description = re.sub(
        r"\s+where\s+.*$",
        "",
        description,
        flags=re.IGNORECASE,
    )

    parts = re.split(
        r"\s*\+\s*",
        description,
    )

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]
def concept_present(row, concept, rule_mapping=None):

    alternatives = re.split(
        r"\s+\bor\b\s+",
        concept,
        flags=re.IGNORECASE,
    )

    for alternative in alternatives:

        alternative = alternative.strip()

        if not alternative:
            continue

        # Use mapper output first
        if rule_mapping:
            semantic = semantic_concept(alternative)

            columns = (
                rule_mapping
                .get("dataset_columns", {})
                .get(semantic, [])
            )

        else:
            columns = resolve_concept_columns(
                alternative,
                row,
            )

        if any(
            has_value(row, column)
            for column in columns
        ):
            return True

    return False
def evaluate_description_combination(
    row,
    description,
    rule_mapping=None,
):

    concepts = split_combination_description(
        description
    )

    if not concepts:
        return False

    for concept in concepts:

        if not concept_present(
            row,
            concept,
            rule_mapping,
        ):
            return False

    return True


# ============================================================
# GENERIC TEXT DETECTION
# ============================================================
def detect_personal_data_in_text(value):

    if value is None:
        return False

    text = str(value).strip()

    if not text:
        return False

    patterns = [
        # Email
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",

        # Phone
        r"\b(?:\+?\d[\d\s().-]{7,}\d)\b",

        # IP address
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",

        # NI number
        r"\b[A-CEGHJ-PR-TW-Z]{2}\s?\d{6}\s?[A-D]\b",

        # Passport
        r"\b[A-Z]{1,2}\d{6,9}\b",

        # Credit/debit card
        r"\b(?:\d[ -]?){13,19}\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True

    return False

def evaluate_text_rule(row, rule):

    description = rule.get(
        "description",
        "",
    ).lower()

    # Prefer explicitly declared execution fields.
    execution_result = evaluate_execution(
        row,
        rule,
    )

    if execution_result is not None:
        return execution_result

    # Otherwise inspect fields semantically mentioned by
    # the policy description.
    text_candidates = []

    for column in row.index:

        normalized_column = normalize_column_name(
            column
        )

        if any(
            token in normalized_column
            for token in (
                "feedback",
                "comment",
                "note",
                "description",
                "text",
            )
        ):
            text_candidates.append(column)

    # If policy says free-text/comments but the dataset has
    # no corresponding text field, it is not applicable.
    if not text_candidates:
        return False

    for column in text_candidates:

        if not has_value(row, column):
            continue

        if detect_personal_data_in_text(row[column]):
            return True

    return False


# ============================================================
# GENERIC RULE EVALUATION
# ============================================================

def evaluate_rule(
    row,
    rule,
    rule_mapping=None,
):

    # --------------------------------------------------------
    # Policy-defined execution
    # --------------------------------------------------------

    execution_result = evaluate_execution(
        row,
        rule,
    )

    if execution_result is not None:
        return execution_result

    # --------------------------------------------------------
    # Combination described directly in policy
    # --------------------------------------------------------

    if rule.get("type") == "combination":

        return evaluate_description_combination(
            row,
            rule.get("description", ""),
            rule_mapping,
        )

    # --------------------------------------------------------
    # Text rule
    # --------------------------------------------------------

    if rule.get("type") == "text":

        return evaluate_text_rule(
            row,
            rule,
        )

    # --------------------------------------------------------
    # Example-based field rule
    # --------------------------------------------------------

    if rule.get("type") == "field":

        for example in rule.get("examples", []):

            resolved_columns = resolve_concept_columns(
                example,
                row,
            )

            if any(
                has_value(row, column)
                for column in resolved_columns
            ):
                return True

        return False

    return False


# ============================================================
# OUTCOME
# ============================================================

def extract_outcome(outcome_text):

    if not outcome_text:
        return None

    text = str(
        outcome_text
    ).upper().strip()

    if "EXCEPTION APPROVED" in text:
        return "EXCEPTION APPROVED"

    if "BLOCK" in text:
        return "BLOCK"

    if "FLAG" in text:
        return "FLAG"

    if "PASS" in text:
        return "PASS"

    return "FLAG"

def load_policy_for_evaluation(policy_file):
    global policy
    global RULES
    global NORMALIZED_RULES
    global DECISIONS

    policy = load_policy(Path(policy_file))

    RULES = extract_rules(policy)
    NORMALIZED_RULES = {rule_id: normalize_rule(rule_id, rule) for rule_id, rule in RULES.items()}
    DECISIONS = extract_decisions(policy)

    print(f"Loaded executable rules: {len(RULES)}")
# ============================================================
# RECORD EVALUATION
# ============================================================
def check_record(row, mapped_policy=None):

    mapped_rules = {}

    def collect(value):
        if isinstance(value, dict):

            rule_id = (
                value.get("rule_id")
                or value.get("Rule ID")
                or value.get("ID")
            )

            if rule_id and "_mapping" in value:
                mapped_rules[str(rule_id)] = value["_mapping"]

            for child in value.values():
                collect(child)

        elif isinstance(value, list):
            for child in value:
                collect(child)

    if mapped_policy:
        collect(mapped_policy)

    triggered_rules = []
    triggered_outcomes = []

    # --------------------------------------------------------
    # Evaluate every executable rule
    # --------------------------------------------------------

    for rule_id, rule in NORMALIZED_RULES.items():

        rule_mapping = mapped_rules.get(
            str(rule_id),
            {}
        )

        semantic_columns = rule_mapping.get(
            "dataset_columns",
            {}
        )

        # Keep normal rule evaluation.
        triggered = evaluate_rule(
            row,
            rule,
            rule_mapping,
        )

        if triggered:

            triggered_rules.append(
                str(rule_id)
            )

            outcome = extract_outcome(
                rule.get("outcome", "")
            )

            if outcome:
                triggered_outcomes.append(
                    outcome
                )

    # --------------------------------------------------------
    # Determine final outcome
    # --------------------------------------------------------

    if "BLOCK" in triggered_outcomes:
        outcome = "BLOCK"

    elif "FLAG" in triggered_outcomes:
        outcome = "FLAG"

    elif "EXCEPTION APPROVED" in triggered_outcomes:
        outcome = "EXCEPTION APPROVED"

    else:
        outcome = "PASS"

    # --------------------------------------------------------
    # Reason
    # --------------------------------------------------------

    if triggered_rules:
        reason = (
            "Triggered rules: "
            + ", ".join(triggered_rules)
        )
    else:
        reason = "No policy rules triggered"

    # --------------------------------------------------------
    # Remediation
    # --------------------------------------------------------

    remediation = ""

    if outcome == "BLOCK":
        remediation = (
            "Remove the restricted personal data "
            "or obtain an approved exception."
        )

    elif outcome == "FLAG":
        remediation = (
            "Review the record for personal data "
            "and confirm whether its use is permitted."
        )

    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return {
        "expected_outcome": outcome,
        "expected_rule_triggers": ";".join(
            triggered_rules
        ),
        "expected_reason": reason,
        "suggested_remediation": remediation,
    }
# ============================================================
# DATABASE STORAGE
# ============================================================
def save_evaluations_to_database(
    df,
    execution_id=None,
    start_record=None,
    end_record=None
):
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    policy_metadata = policy["policies"][0].get(
        "policy_metadata", {}
    )

    policy_id = (
        policy_metadata.get("policy_id")
        or policy_metadata.get("Policy ID")
        or policy_metadata.get("id")
        or "POLICY-001"
    )

    policy_name = (
        policy_metadata.get("policy_name")
        or policy_metadata.get("Policy Name")
        or policy_metadata.get("name")
        or "Policy"
    )

    version = (
        policy_metadata.get("version")
        or policy_metadata.get("Version")
        or ""
    )

    # --------------------------------------------------------
    # Create policy record only if this execution does not
    # already have one
    # --------------------------------------------------------

    policy_row = cursor.execute(
        """
        SELECT id
        FROM policies
        WHERE policy_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (policy_id,)
    ).fetchone()

    if policy_row:
        db_policy_id = policy_row["id"]
    else:
        cursor.execute(
            """
            INSERT INTO policies
            (policy_id, policy_name, version)
            VALUES (?, ?, ?)
            """,
            (
                policy_id,
                policy_name,
                version,
            ),
        )

        db_policy_id = cursor.lastrowid

        # Store rules
        for rule_id, rule in NORMALIZED_RULES.items():
            cursor.execute(
                """
                INSERT INTO policy_rules
                (policy_id, rule_id, description, outcome)
                VALUES (?, ?, ?, ?)
                """,
                (
                    db_policy_id,
                    rule_id,
                    rule.get("description", ""),
                    rule.get("outcome", ""),
                ),
            )

    # --------------------------------------------------------
    # Create execution only when one was not supplied
    # --------------------------------------------------------

    if execution_id is None:

        batch_size = len(df)
        total_records = len(df)

        total_batches = 1

        started_at = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT INTO executions
            (
                policy_id,
                total_records,
                batch_size,
                total_batches,
                start_record,
                end_record,
                started_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                db_policy_id,
                total_records,
                batch_size,
                total_batches,
                start_record,
                end_record,
                started_at,
            ),
        )

        execution_id = cursor.lastrowid

    else:

        # Make sure supplied execution exists
        execution_row = cursor.execute(
            """
            SELECT id
            FROM executions
            WHERE id = ?
            """,
            (execution_id,)
        ).fetchone()

        if execution_row is None:
            conn.close()
            raise ValueError(
                f"Execution {execution_id} does not exist"
            )

    # --------------------------------------------------------
    # Store evaluations
    # --------------------------------------------------------

    for _, row in df.iterrows():

        input_data = {}

        for column in df.columns:

            if column in {
                "expected_outcome",
                "expected_rule_triggers",
                "expected_reason",
                "suggested_remediation",
            }:
                continue

            value = row.get(column, "")

            if pd.isna(value):
                value = ""

            input_data[column] = str(value)

        cursor.execute(
            """
            INSERT INTO evaluations
            (
                policy_id,
                execution_id,
                record_id,
                decision,
                reason,
                remediation,
                input_data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                db_policy_id,
                execution_id,
                str(row.get("record_id", "")),
                str(row.get("expected_outcome", "")),
                str(row.get("expected_reason", "")),
                str(row.get("suggested_remediation", "")),
                json.dumps(input_data),
            ),
        )

        evaluation_id = cursor.lastrowid

        rules = str(
            row.get("expected_rule_triggers", "")
        ).split(";")

        for rule_id in rules:

            rule_id = rule_id.strip()

            if not rule_id:
                continue

            cursor.execute(
                """
                INSERT INTO triggered_rules
                (evaluation_id, rule_id)
                VALUES (?, ?)
                """,
                (
                    evaluation_id,
                    rule_id,
                ),
            )

    # --------------------------------------------------------
    # Complete execution
    # --------------------------------------------------------

    completed_at = datetime.now().isoformat()

    cursor.execute(
        """
        UPDATE executions
        SET
            completed_at = ?,
            policy_id = ?
        WHERE id = ?
        """,
        (
            completed_at,
            db_policy_id,
            execution_id,
        ),
    )

    conn.commit()
    conn.close()

    print(
        f"Database updated: execution #{execution_id}, "
        f"{len(df)} records"
    )

    return execution_id
def evaluate_dataframe(df, mapped_policy=None):

    rows = []

    for _, row in df.iterrows():

        result = check_record(
            row,
            mapped_policy=mapped_policy
        )

        rows.append({
            "expected_outcome": result.get("expected_outcome"),
            "expected_rule_triggers": result.get(
                "expected_rule_triggers", []
            ),
            "expected_reason": result.get(
                "expected_reason", ""
            ),
            "suggested_remediation": result.get(
                "suggested_remediation", ""
            ),
        })

    results = pd.DataFrame(rows, index=df.index)

    df = df.copy()

    df["expected_outcome"] = results["expected_outcome"]
    df["expected_rule_triggers"] = results[
        "expected_rule_triggers"
    ]
    df["expected_reason"] = results[
        "expected_reason"
    ]
    df["suggested_remediation"] = results[
        "suggested_remediation"
    ]

    return df
# ============================================================
# MAIN
# ============================================================

def main():

    load_policy_for_evaluation(POLICY_FILE)

    print(f"Input dataset: {INPUT}")
    print(f"Policy file: {POLICY_FILE}")

    if not INPUT.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {INPUT}"
        )

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    df = pd.read_excel(INPUT)
    mapped_policy = map_policy(
        policy,
        df.columns.tolist()
    )

    print(f"Records loaded: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------

    df = evaluate_dataframe(
        df,
        mapped_policy
    )
    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_excel(
        OUTPUT,
        index=False,
    )

    # --------------------------------------------------------
    # Format Excel
    # --------------------------------------------------------

    workbook = load_workbook(OUTPUT)
    worksheet = workbook.active

    for cell in worksheet[1]:

        cell.font = Font(
            bold=True
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    for column in worksheet.columns:

        max_length = 0
        column_letter = (
            column[0].column_letter
        )

        for cell in column:

            if cell.value is not None:

                max_length = max(
                    max_length,
                    len(str(cell.value)),
                )

        worksheet.column_dimensions[
            column_letter
        ].width = min(
            max_length + 2,
            60,
        )

    workbook.save(OUTPUT)
    # --------------------------------------------------------
    # Save to database
    # --------------------------------------------------------

    save_evaluations_to_database(df)
    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("Policy evaluation complete!")
    print(f"Output: {OUTPUT}")

    print()
    print("Outcome summary:")

    print(
        df[
            "expected_outcome"
        ].value_counts()
    )

    # --------------------------------------------------------
    # Rule summary
    # --------------------------------------------------------

    rule_counts = {}

    for value in df[
        "expected_rule_triggers"
    ].dropna():

        if not str(value).strip():
            continue

        for rule_id in str(
            value
        ).split(";"):

            rule_id = rule_id.strip()

            if not rule_id:
                continue

            rule_counts[rule_id] = (
                rule_counts.get(
                    rule_id,
                    0,
                ) + 1
            )

    print()
    print("Rule summary:")

    if rule_counts:

        rule_summary = pd.Series(
            rule_counts
        ).sort_values(
            ascending=False
        )

        print(rule_summary)

    else:
        print("No rules triggered.")


if __name__ == "__main__":
    main()