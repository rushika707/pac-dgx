import json
import re
import sys
import argparse
from pathlib import Path


sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent)
)

from pathlib import Path
from policy.policy_mapper import (
    semantic_concept,
    dataset_columns_for_concept,
)


BASE = Path(__file__).resolve().parent.parent
POLICY_FILE = BASE / "policy" / "policy.json"
OUTPUT_FILE = BASE / "opa" / "generated_policy.rego"


# ============================================================
# LOAD POLICY
# ============================================================

def load_policy():
    with open(POLICY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# EXTRACT RULES
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


# ============================================================
# DESCRIPTION
# ============================================================

def get_description(rule):

    for key in (
        "description",
        "Description",
        "PII type",
        "Sensitive data type",
        "Combination rule",
    ):

        value = rule.get(key)

        if value:
            return str(value).strip()

    return ""


# ============================================================
# OUTCOME
# ============================================================

def extract_outcome(rule):

    text = str(
        rule.get("Required policy outcome")
        or rule.get("Required outcome")
        or rule.get("outcome")
        or rule.get("Outcome")
        or ""
    ).upper()

    if "EXCEPTION APPROVED" in text:
        return "EXCEPTION APPROVED"

    if "BLOCK" in text:
        return "BLOCK"

    if "FLAG" in text:
        return "FLAG"

    if "PASS" in text:
        return "PASS"

    return "FLAG"


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value):

    value = str(value).lower().strip()
    value = value.replace("_", " ")
    value = value.replace("-", " ")
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


# ============================================================
# POLICY CONCEPT VOCABULARY
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
        "worker id",
        "worker identifier",
        "worker number",
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
        "free form text",
        "free-form text",
        "comments",
        "comment",
        "notes",
        "feedback",
        "description",
        "text",
    ],
}


# ============================================================
# RESOLVE CONCEPT FIELDS
# ============================================================

def resolve_concept_fields(concept, rule_mapping=None):

    concept = str(concept).strip()

    semantic = semantic_concept(concept)

    if rule_mapping and semantic:

        return rule_mapping.get(
            "dataset_columns",
            {}
        ).get(
            semantic,
            []
        )

    if semantic:
        return dataset_columns_for_concept(
            semantic
        )

    return []


# ============================================================
# REGO HELPERS
# ============================================================

def generate_helpers(lines):

    lines.extend([

        "# ==================================================",
        "# Generic helpers",
        "# ==================================================",
        "",

        "has_value(field) if {",
        '    value := object.get(input.record, field, "")',
        "    value != null",
        '    value != ""',
        "}",
        "",

        "has_any(fields) if {",
        "    some i",
        "    field := fields[i]",
        "    has_value(field)",
        "}",
        "",

        "all_groups_present(groups) if {",
        "    every group in groups {",
        "        some i",
        "        field := group[i]",
        "        has_value(field)",
        "    }",
        "}",
        "",

        # --------------------------------------------------
        # Regex-based text detection
        # --------------------------------------------------

        "text_matches(fields, patterns) if {",
        "    some i",
        "    some j",
        "    field := fields[i]",
        "    pattern := patterns[j]",
        '    value := object.get(input.record, field, "")',
        "    value != null",
        '    value != ""',
        "    regex.match(pattern, value)",
        "}",
        "",

        # --------------------------------------------------
        # Generic record-PII detection
        # --------------------------------------------------



        # --------------------------------------------------
        # Structured identifier detection inside text
        # --------------------------------------------------

        "contains_record_pii(field) if {",
        '    value := object.get(input.record, field, "")',
        '    value != ""',

        "    patterns := [",
        r'        `(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}`,',
        r'        `(?i)\b(?:\+44|0)\d{9,10}\b`,',
        r'        `\b(?:\d[ -]?){13,19}\b`,',
        r'        `\b[A-Z]{2}\d{6}[A-Z]?\b`,',
        "    ]",

        "    some i",
        "    regex.match(patterns[i], value)",
        "}",
        "",
    ])


# ============================================================
# FIELD CONDITION
# ============================================================

def generate_field_condition(
    fields,
    rule_mapping=None
):

    resolved = []

    for field in fields:

        if isinstance(field, str):

            resolved.extend(
                resolve_concept_fields(
                    field,
                    rule_mapping
                )
            )

    resolved = sorted(
        set(resolved)
    )

    if not resolved:
        return "false"

    return (
        f"has_any({json.dumps(resolved)})"
    )


# ============================================================
# COMBINATION DESCRIPTION
# ============================================================

def split_combination_description(
    description
):

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


def generate_combination_condition(
    description,
    rule_mapping=None,
):

    concepts = split_combination_description(
        description
    )

    if not concepts:
        return "false"

    groups = []

    for concept in concepts:

        alternatives = re.split(
            r"\s+\bor\b\s+",
            concept,
            flags=re.IGNORECASE,
        )

        group = []

        for alternative in alternatives:

            alternative = alternative.strip()

            if not alternative:
                continue

            group.extend(
                resolve_concept_fields(
                    alternative,
                    rule_mapping
                )
            )

        group = sorted(
            set(group)
        )

        # Required concept has no dataset representation
        if not group:
            return "false"

        groups.append(group)

    return (
        "all_groups_present("
        + json.dumps(groups)
        + ")"
    )


# ============================================================
# TEXT CONDITION
# ============================================================

def generate_text_condition(
    rule,
    rule_mapping=None
):

    execution = rule.get(
        "execution",
        {}
    )

    fields = execution.get(
        "fields",
        []
    )

    patterns = execution.get(
        "patterns",
        []
    )

    resolved_fields = []

    for group in fields:

        if isinstance(group, str):
            group = [group]

        for field in group:

            resolved_fields.extend(
                resolve_concept_fields(
                    field,
                    rule_mapping
                )
            )

    resolved_fields = sorted(
        set(resolved_fields)
    )

    if not resolved_fields:

        # Generic free-text rule.
        #
        # CPII-08 uses the dataset's feedback column.
        #
        # Detection is performed by the generic
        # contains_record_pii() helper.

        return 'contains_record_pii("feedback")'

    return (
        "text_matches("
        + json.dumps(resolved_fields)
        + ", "
        + json.dumps(patterns)
        + ")"
    )


# ============================================================
# RULE CONDITION
# ============================================================

def generate_condition(
    rule,
    rule_mapping=None
):

    execution = rule.get(
        "execution",
        {}
    )

    execution_type = execution.get(
        "type"
    )

    # --------------------------------------------------------
    # Policy-defined execution
    # --------------------------------------------------------

    if execution_type == "field":

        return generate_field_condition(
            execution.get("fields", []),
            rule_mapping
        )

    if execution_type == "combination":

        fields = execution.get(
            "fields",
            []
        )

        if fields:

            groups = []

            for group in fields:

                if isinstance(group, str):
                    group = [group]

                resolved_group = []

                for field in group:

                    resolved_group.extend(
                        resolve_concept_fields(
                            field,
                            rule_mapping
                        )
                    )

                groups.append(
                    sorted(set(resolved_group))
                )

            # A required group has no dataset representation
            if any(
                not group
                for group in groups
            ):
                return "false"

            return (
                "all_groups_present("
                + json.dumps(groups)
                + ")"
            )

        # No machine-readable execution.
        # Fall back to policy description.

        return generate_combination_condition(
            get_description(rule),
            rule_mapping
        )

    if execution_type == "text":

        return generate_text_condition(
            rule,
            rule_mapping
        )

    # --------------------------------------------------------
    # Description-based combination
    # --------------------------------------------------------

    description = get_description(
        rule
    )

    if "+" in description:

        return generate_combination_condition(
            description
        )

    # --------------------------------------------------------
    # Example-based field rule
    # --------------------------------------------------------

    examples = (
        rule.get("Examples")
        or rule.get("examples")
        or []
    )

    if isinstance(examples, str):

        examples = [
            x.strip()
            for x in examples.split(",")
            if x.strip()
        ]

    if examples:

        return generate_field_condition(
            examples
        )

    # --------------------------------------------------------
    # Free-text policy rule
    # --------------------------------------------------------

    normalized_description = normalize_text(
        description
    )

    if (
        "free text" in normalized_description
        or "free form text" in normalized_description
        or "comments" in normalized_description
        or "notes" in normalized_description
        or "feedback" in normalized_description
        or "personal identifiers" in normalized_description
    ):

        return 'contains_record_pii("feedback")'

    # --------------------------------------------------------
    # No executable representation
    # --------------------------------------------------------

    return "false"


# ============================================================
# EXTRACT RULE MAPPING
# ============================================================

def extract_rule_mapping(
    mapped_policy,
    rule_id
):

    def walk(value):

        if isinstance(value, dict):

            current_id = (
                value.get("rule_id")
                or value.get("Rule ID")
                or value.get("ID")
            )

            if str(current_id) == str(rule_id):

                return value.get(
                    "_mapping",
                    {}
                )

            for child in value.values():

                result = walk(child)

                if result is not None:
                    return result

        elif isinstance(value, list):

            for child in value:

                result = walk(child)

                if result is not None:
                    return result

        return None

    return walk(mapped_policy) or {}


# ============================================================
# GENERATE REGO
# ============================================================

def generate(
    policy,
    mapped_policy=None
):

    rules = extract_rules(
        policy
    )

    lines = [
        "package generated_policy",
        "",
        'default decision := "PASS"',
        "",
    ]

    generate_helpers(
        lines
    )

    lines.extend([
        "# ==================================================",
        "# Rule triggers",
        "# ==================================================",
        "",
    ])

    generated_rules = []

    for rule_id, rule in rules.items():

        safe_id = re.sub(
            r"[^A-Za-z0-9_]",
            "_",
            rule_id
        )

        rule_mapping = extract_rule_mapping(
            mapped_policy,
            rule_id
        )

        condition = generate_condition(
            rule,
            rule_mapping
        )

        outcome = extract_outcome(
            rule
        )

        generated_rules.append({
            "id": rule_id,
            "safe_id": safe_id,
            "outcome": outcome,
        })

        lines.extend([
            f"trigger_{safe_id} if {{",
            f"    {condition}",
            "}",
            "",
        ])

    # ========================================================
    # Triggered rules
    # ========================================================

    lines.extend([
        "# ==================================================",
        "# Triggered rules",
        "# ==================================================",
        "",
    ])

    for rule in generated_rules:

        lines.extend([
            (
                f'triggered_rules contains '
                f'{json.dumps(rule["id"])} if {{'
            ),
            f'    trigger_{rule["safe_id"]}',
            "}",
            "",
        ])

    # ========================================================
    # Outcome flags
    # ========================================================

    lines.extend([
        "# ==================================================",
        "# Outcome flags",
        "# ==================================================",
        "",
        "default has_block := false",
        "default has_flag := false",
        "default has_exception := false",
        "",
    ])

    for rule in generated_rules:

        if rule["outcome"] == "BLOCK":

            lines.extend([
                "has_block if {",
                f'    trigger_{rule["safe_id"]}',
                "}",
                "",
            ])

        elif rule["outcome"] == "FLAG":

            lines.extend([
                "has_flag if {",
                f'    trigger_{rule["safe_id"]}',
                "}",
                "",
            ])

        elif rule["outcome"] == "EXCEPTION APPROVED":

            lines.extend([
                "has_exception if {",
                f'    trigger_{rule["safe_id"]}',
                "}",
                "",
            ])

    # ========================================================
    # Final decision
    # ========================================================

    lines.extend([
        "# ==================================================",
        "# Final decision",
        "# ==================================================",
        "",
        'decision := "BLOCK" if {',
        "    has_block",
        "}",
        "",
        'decision := "FLAG" if {',
        "    not has_block",
        "    has_flag",
        "}",
        "",
        'decision := "EXCEPTION APPROVED" if {',
        "    not has_block",
        "    not has_flag",
        "    has_exception",
        "}",
        "",
    ])

    # ========================================================
    # Final result
    # ========================================================

    lines.extend([
        "# ==================================================",
        "# Final result",
        "# ==================================================",
        "",
        "result := {",
        '    "decision": decision,',
        (
            '    "triggered_rules": '
            '[rule | triggered_rules[rule]]'
        ),
        "}",
    ])

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--policy",
        type=Path,
        default=POLICY_FILE,
    )

    parser.add_argument(
        "--mapped",
        type=Path,
        default=BASE / "policy" / "mapped_policy.json",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_FILE,
    )

    args = parser.parse_args()

    with open(
        args.policy,
        "r",
        encoding="utf-8"
    ) as f:

        policy = json.load(f)

    mapped_policy = None

    if args.mapped.exists():

        with open(
            args.mapped,
            "r",
            encoding="utf-8"
        ) as f:

            mapped_policy = json.load(f)

    generated = generate(
        policy,
        mapped_policy
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        args.output,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(generated)

    print(
        f"Generated: {args.output}"
    )