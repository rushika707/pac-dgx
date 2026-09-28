import re


SEMANTIC_ALIASES = {
    "full_name": [
        "full name", "customer name", "person name",
        "client name"
    ],

    "dob": [
        "date of birth", "dob", "birth date", "birthdate"
    ],

    "email": [
        "personal email", "personal email address",
        "email", "email address", "contact email"
    ],

    "phone": [
        "phone", "phone number", "mobile",
        "mobile number", "telephone", "telephone number"
    ],

    "address": [
        "postal address",
        "postal/home address",
        "home address",
        "street address",
        "residential address",
        "delivery address"
    ],

    "postcode": [
        "postcode", "postal code", "zip", "zip code"
    ],

    "gender": [
        "gender", "sex"
    ],

    "ni_number": [
        "ni number", "national insurance number", "nino"
    ],

    "passport_number": [
        "passport", "passport number"
    ],

    "driving_licence_number": [
        "driving licence", "driving licence number",
        "driving license", "driving license number",
        "licence number", "license number"
    ],

    "government_id": [
        "government issued identifier",
        "government-issued identifier",
        "government identifier",
        "national id", "national identifier",
        "tax id", "tax identifier"
    ],

    "bank_account": [
        "bank account", "bank account number",
        "bank account details"
    ],

    "account_number": [
        "account number", "customer account number",
        "customer account id", "customer account identifier"
    ],

    "credit_card_number": [
        "credit card", "credit card number",
        "debit card", "payment card", "card number"
    ],

    "payment_information": [
        "payment information", "payment token",
        "payment details"
    ],

    "ip_address": [
        "ip address", "ip_address",
        "internet protocol address"
    ],

    "device_id": [
        "device id", "device identifier",
        "device identification"
    ],

    "cookie_id": [
        "cookie id", "cookie identifier"
    ],

    "advertising_id": [
        "advertising id", "advertising identifier"
    ],

    "medical_condition": [
        "medical condition", "health",
        "health condition", "diagnosis", "treatment",
        "disability", "disability information"
    ],

    "financial_difficulty": [
        "financial difficulty", "financial hardship",
        "arrears status", "vulnerability flag",
        "financial vulnerability"
    ],

    "location_history": [
        "location history", "precise location history",
        "gps trace", "gps history",
        "precise coordinates", "exact location history"
    ],

    "authentication_secret": [
        "password", "security answer",
        "authentication secret", "authentication secrets",
        "security secret"
    ],

    "fraud_investigation": [
        "fraud investigation", "fraud investigation information",
        "fraud case notes", "investigation details",
        "suspicious activity notes"
    ],

    "biometric": [
        "biometric information", "biometric",
        "voiceprint", "face template",
        "faceprint", "fingerprint template",
        "fingerprint", "iris scan", "dna profile"
    ],

    "ethnicity": [
        "ethnicity", "race", "racial origin"
    ],

    "religion": [
        "religion", "religious belief", "belief"
    ],

    "political_view": [
        "political opinion", "political view",
        "party preference"
    ],

    "employee_id": [
        "employee id", "employee identifier",
        "employee number"
    ],

    "department": [
        "department", "business unit", "team"
    ],

    "job_role": [
        "job role", "job title", "position"
    ],

    "customer_id": [
        "customer id", "customer identifier",
        "client id", "client identifier",
        "user id", "user identifier"
    ],

    "account_balance": [
        "account balance"
    ],

    "account_event_details": [
        "account event", "account event details",
        "account activity", "transaction details",
        "transaction event", "transaction history"
    ],

    "complaint_support_case": [
        "complaint", "complaint details",
        "support case", "support case details",
        "customer support", "case details"
    ],

    "timestamp": [
        "timestamp", "time stamp", "date and time"
    ],

    "free_text": [
        "free text", "free-text", "comment",
        "comments", "notes", "feedback",
        "description"
    ],
}



def normalize(text):
    text = str(text).lower()
    text = text.replace("_", " ")
    text = text.replace("-", " ")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def semantic_concept(text):
    """
    Map policy wording to a semantic concept.
    Uses exact word-boundary matching and avoids generic
    substring matches.
    """

    normalized = normalize(text)
    matches = []

    for concept, aliases in SEMANTIC_ALIASES.items():

        for alias in [concept] + aliases:

            alias = normalize(alias)

            if not alias:
                continue

            pattern = (
                r"(?<!\\w)"
                + re.escape(alias)
                + r"(?!\\w)"
            )

            if not re.search(pattern, normalized):
                continue

            # Generic "address" must not be inferred from
            # phrases such as "email address".
            if concept == "address":
                if not any(
                    phrase in normalized
                    for phrase in [
                        "postal address",
                        "postal home address",
                        "home address",
                        "street address",
                        "residential address",
                        "delivery address",
                    ]
                ):
                    continue

            matches.append(
                (len(alias), concept)
            )

    if not matches:
        return None

    matches.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return matches[0][1]


def map_fields(fields):
    """
    Convert arbitrary policy fields into semantic concepts.
    """

    mapped = []

    for field in fields:
        if not isinstance(field, str):
            continue

        concept = semantic_concept(field)

        mapped.append({
            "original": field,
            "semantic": concept,
        })

    return mapped


def dataset_columns_for_concept(concept):
    """
    Map semantic meaning to the current synthetic dataset.
    """

    mapping = {
        "full_name": ["customer_name"],
        "dob": ["dob"],
        "email": ["email"],
        "phone": ["phone"],
        "address": ["address"],
        "postcode": [],
        "gender": ["gender"],

        "ni_number": ["ni_number"],
        "passport_number": ["passport_number"],
        "driving_licence_number": [],
        "government_id": [],

        "bank_account": ["bank_account"],
        "account_number": [],
        "credit_card_number": ["credit_card_number"],
        "payment_information": [],

        "ip_address": ["ip_address"],
        "device_id": [],
        "cookie_id": [],
        "advertising_id": [],

        "medical_condition": ["medical_condition"],
        "financial_difficulty": [],
        "location_history": [],
        "authentication_secret": [],
        "fraud_investigation": [],
        "biometric": [],

        "ethnicity": ["ethnicity"],
        "religion": ["religion"],
        "political_view": ["political_view"],

        "employee_id": ["employee_id"],
        "department": ["department"],
        "job_role": ["job_role"],
        "customer_id": ["customer_id"],

        "account_balance": [],
        "account_event_details": [],
        "complaint_support_case": [],
        "timestamp": [],

        "free_text": ["feedback"],
    }

    return mapping.get(concept, [])

def map_policy(policy, dataset_columns):
    """
    Convert policy rules into an execution-ready intermediate
    representation.

    The original policy is not modified.

    Semantics preserved:
        A + B       -> AND
        A or B      -> OR
        direct field -> field
        free-text   -> text
    """

    def resolve_group(group):
        concepts = []
        columns = []

        for phrase in group:

            phrase = str(phrase).strip()

            if not phrase:
                continue

            concept = semantic_concept(phrase)

            if concept:
                concepts.append(concept)

                resolved_columns = [
                    column
                    for column in dataset_columns_for_concept(
                        concept
                    )
                    if column in dataset_columns
                ]

                columns.extend(resolved_columns)

            else:
                concepts.append(phrase)

        return (
            concepts,
            sorted(set(columns))
        )

    def build_rule(rule):

        if not isinstance(rule, dict):
            return rule

        rule_id = (
            rule.get("rule_id")
            or rule.get("Rule ID")
            or rule.get("ID")
        )

        if not rule_id:
            return rule

        description = (
            rule.get("description")
            or rule.get("Description")
            or rule.get("PII type")
            or rule.get("Sensitive data type")
            or rule.get("Combination rule")
            or rule.get("Policy statement")
            or ""
        )

        examples = (
            rule.get("examples")
            or rule.get("Examples")
            or []
        )

        if isinstance(examples, str):
            examples = [examples]

        description_text = str(description)

        normalized_description = normalize(
            description_text
        )

        # ----------------------------------------------------
        # Free-text rule
        # ----------------------------------------------------

        is_free_text = any(
            keyword in normalized_description
            for keyword in [
                "free text",
                "free-text",
                "comments",
                "notes",
                "feedback",
                "personal identifiers"
            ]
        )

        if is_free_text:

            feedback_fields = [
                column
                for column in dataset_columns_for_concept(
                    "free_text"
                )
                if column in dataset_columns
            ]

            return {
                "rule_id": rule_id,
                "description": description_text,
                "outcome": rule.get(
                    "outcome",
                    rule.get("Outcome", "")
                ),
                "mappings": [
                    {
                        "type": "text",
                        "concept_groups": [
                            ["free_text"]
                        ],
                        "dataset_field_groups": [
                            sorted(set(feedback_fields))
                        ]
                    }
                ]
            }

        # ----------------------------------------------------
        # Build semantic groups
        # ----------------------------------------------------

        mappings = []

        for example in examples:

            example = str(example).strip()

            if not example:
                continue

            # -----------------------------------------------
            # AND
            # -----------------------------------------------

            if "+" in example:

                parts = [
                    p.strip()
                    for p in re.split(
                        r"\s*\+\s*",
                        example
                    )
                    if p.strip()
                ]

                concept_groups = []
                dataset_field_groups = []

                for part in parts:

                    concepts, fields = resolve_group(
                        [part]
                    )

                    concept_groups.append(
                        concepts
                    )

                    dataset_field_groups.append(
                        fields
                    )

                mappings.append({
                    "type": "combination",
                    "concept_groups": concept_groups,
                    "dataset_field_groups":
                        dataset_field_groups
                })

            # -----------------------------------------------
            # OR
            # -----------------------------------------------

            elif re.search(
                r"\s+or\s+",
                example,
                flags=re.IGNORECASE
            ):

                parts = [
                    p.strip()
                    for p in re.split(
                        r"\s+or\s+",
                        example,
                        flags=re.IGNORECASE
                    )
                    if p.strip()
                ]

                concepts, fields = resolve_group(
                    parts
                )

                mappings.append({
                    "type": "combination",
                    "concept_groups": [
                        concepts
                    ],
                    "dataset_field_groups": [
                        fields
                    ]
                })

            # -----------------------------------------------
            # Direct field
            # -----------------------------------------------

            else:

                concepts, fields = resolve_group(
                    [example]
                )

                mappings.append({
                    "type": "field",
                    "concept_groups": [
                        concepts
                    ],
                    "dataset_field_groups": [
                        fields
                    ]
                })

        return {
            "rule_id": rule_id,
            "description": description_text,
            "outcome": rule.get(
                "outcome",
                rule.get("Outcome", "")
            ),
            "mappings": mappings
        }

    # --------------------------------------------------------
    # Extract policy metadata
    # --------------------------------------------------------

    if isinstance(policy, dict):

        policies = policy.get(
            "policies",
            []
        )

        if policies:

            source_policy = policies[0]

            metadata = source_policy.get(
                "policy_metadata",
                {}
            )

            rules = source_policy.get(
                "rules",
                []
            )

            return {
                "policy_id": metadata.get(
                    "policy_id"
                ),
                "policy_name": metadata.get(
                    "policy_name"
                ),
                "policy_version": metadata.get(
                    "policy_version"
                ),
                "effective_date": metadata.get(
                    "effective_date"
                ),
                "rules": [
                    build_rule(rule)
                    for rule in rules
                ]
            }

    return policy
if __name__ == "__main__":

    import json
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent

    POLICY_FILE = BASE_DIR / "policy" / "policy.json"
    OUTPUT_FILE = BASE_DIR / "policy" / "mapped_policy.json"

    with open(
        POLICY_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        policy = json.load(f)

    # Current synthetic dataset columns
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
        "feedback"
    ]

    mapped_policy = map_policy(
        policy,
        dataset_columns
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            mapped_policy,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"Mapped policy written to: {OUTPUT_FILE}"
    )

    print(
        f"Rules mapped: {len(mapped_policy.get('rules', []))}"
    )