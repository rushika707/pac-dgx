package generated_policy

default decision := "PASS"

# ==================================================
# Generic helpers
# ==================================================

has_value(field) if {
    value := object.get(input.record, field, "")
    value != null
    value != ""
}

has_any(fields) if {
    some i
    field := fields[i]
    has_value(field)
}

all_groups_present(groups) if {
    every group in groups {
        some i
        field := group[i]
        has_value(field)
    }
}

text_matches(fields, patterns) if {
    some i
    some j
    field := fields[i]
    pattern := patterns[j]
    value := object.get(input.record, field, "")
    value != null
    value != ""
    regex.match(pattern, value)
}

contains_record_pii(field) if {
    value := object.get(input.record, field, "")
    value != ""
    patterns := [
        `(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}`,
        `(?i)\b(?:\+44|0)\d{9,10}\b`,
        `\b(?:\d[ -]?){13,19}\b`,
        `\b[A-Z]{2}\d{6}[A-Z]?\b`,
    ]
    some i
    regex.match(patterns[i], value)
}

# ==================================================
# Rule triggers
# ==================================================

trigger_PII_01 if {
    has_any(["customer_name"])
}

trigger_PII_02 if {
    has_any(["email"])
}

trigger_PII_03 if {
    has_any(["phone"])
}

trigger_PII_04 if {
    has_any(["address"])
}

trigger_PII_05 if {
    false
}

trigger_PII_06 if {
    has_any(["passport_number"])
}

trigger_PII_07 if {
    false
}

trigger_PII_08 if {
    has_any(["bank_account", "credit_card_number"])
}

trigger_PII_09 if {
    has_any(["customer_id", "ip_address"])
}

trigger_SPII_01 if {
    has_any(["medical_condition"])
}

trigger_SPII_02 if {
    has_any(["ethnicity"])
}

trigger_SPII_03 if {
    has_any(["religion"])
}

trigger_SPII_04 if {
    has_any(["political_view"])
}

trigger_SPII_05 if {
    false
}

trigger_SPII_06 if {
    false
}

trigger_CPII_01 if {
    all_groups_present([["customer_name"], ["dob"]])
}

trigger_CPII_02 if {
    all_groups_present([["customer_name"], ["address"]])
}

trigger_CPII_03 if {
    all_groups_present([["customer_name"], ["phone"]])
}

trigger_CPII_04 if {
    all_groups_present([["customer_name"], ["email"]])
}

trigger_CPII_05 if {
    false
}

trigger_CPII_06 if {
    all_groups_present([["employee_id"], ["department"], ["job_role"]])
}

trigger_CPII_07 if {
    false
}

trigger_CPII_08 if {
    contains_record_pii("feedback")
}

# ==================================================
# Triggered rules
# ==================================================

triggered_rules contains "PII-01" if {
    trigger_PII_01
}

triggered_rules contains "PII-02" if {
    trigger_PII_02
}

triggered_rules contains "PII-03" if {
    trigger_PII_03
}

triggered_rules contains "PII-04" if {
    trigger_PII_04
}

triggered_rules contains "PII-05" if {
    trigger_PII_05
}

triggered_rules contains "PII-06" if {
    trigger_PII_06
}

triggered_rules contains "PII-07" if {
    trigger_PII_07
}

triggered_rules contains "PII-08" if {
    trigger_PII_08
}

triggered_rules contains "PII-09" if {
    trigger_PII_09
}

triggered_rules contains "SPII-01" if {
    trigger_SPII_01
}

triggered_rules contains "SPII-02" if {
    trigger_SPII_02
}

triggered_rules contains "SPII-03" if {
    trigger_SPII_03
}

triggered_rules contains "SPII-04" if {
    trigger_SPII_04
}

triggered_rules contains "SPII-05" if {
    trigger_SPII_05
}

triggered_rules contains "SPII-06" if {
    trigger_SPII_06
}

triggered_rules contains "CPII-01" if {
    trigger_CPII_01
}

triggered_rules contains "CPII-02" if {
    trigger_CPII_02
}

triggered_rules contains "CPII-03" if {
    trigger_CPII_03
}

triggered_rules contains "CPII-04" if {
    trigger_CPII_04
}

triggered_rules contains "CPII-05" if {
    trigger_CPII_05
}

triggered_rules contains "CPII-06" if {
    trigger_CPII_06
}

triggered_rules contains "CPII-07" if {
    trigger_CPII_07
}

triggered_rules contains "CPII-08" if {
    trigger_CPII_08
}

# ==================================================
# Outcome flags
# ==================================================

default has_block := false
default has_flag := false
default has_exception := false

has_flag if {
    trigger_PII_01
}

has_flag if {
    trigger_PII_02
}

has_flag if {
    trigger_PII_03
}

has_flag if {
    trigger_PII_04
}

has_block if {
    trigger_PII_05
}

has_block if {
    trigger_PII_06
}

has_block if {
    trigger_PII_07
}

has_block if {
    trigger_PII_08
}

has_flag if {
    trigger_PII_09
}

has_block if {
    trigger_SPII_01
}

has_block if {
    trigger_SPII_02
}

has_block if {
    trigger_SPII_03
}

has_block if {
    trigger_SPII_04
}

has_block if {
    trigger_SPII_05
}

has_block if {
    trigger_SPII_06
}

has_flag if {
    trigger_CPII_01
}

has_flag if {
    trigger_CPII_02
}

has_flag if {
    trigger_CPII_03
}

has_flag if {
    trigger_CPII_04
}

has_flag if {
    trigger_CPII_05
}

has_flag if {
    trigger_CPII_06
}

has_flag if {
    trigger_CPII_07
}

has_flag if {
    trigger_CPII_08
}

# ==================================================
# Final decision
# ==================================================

decision := "BLOCK" if {
    has_block
}

decision := "FLAG" if {
    not has_block
    has_flag
}

decision := "EXCEPTION APPROVED" if {
    not has_block
    not has_flag
    has_exception
}

# ==================================================
# Final result
# ==================================================

result := {
    "decision": decision,
    "triggered_rules": [rule | triggered_rules[rule]]
}