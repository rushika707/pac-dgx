from pathlib import Path

from pdf_reader import extract_text
from policy_extractor import extract_policy


BASE = Path(__file__).resolve().parent.parent

PDF_FILE = BASE / "input" / "policy.pdf"
OUTPUT_FILE = BASE / "policy" / "policy.json"


def main():

    print()
    print("=" * 70)
    print("POLICY EXTRACTION")
    print("=" * 70)

    print()
    print(f"Policy PDF:")
    print(f"  {PDF_FILE}")

    print()
    print("Reading PDF...")

    pdf_text = extract_text(str(PDF_FILE))

    if not pdf_text.strip():
        raise ValueError("No text extracted from policy PDF.")

    print(
        f"Extracted {len(pdf_text):,} characters."
    )

    print()
    print("Sending policy document to Qwen...")

    extract_policy(
        pdf_text,
        str(OUTPUT_FILE)
    )

    print()
    print("=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()