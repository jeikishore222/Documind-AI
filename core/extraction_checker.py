
import re
from decimal import Decimal, InvalidOperation

from core.column_layout import detect_column_order


NUMBER_PATTERN = r"-?\d[\d,]*(?:\.\d+)?"
MISSING_PATTERN = r"N/A|N\.A\.|NULL|NONE"
VALUE_PATTERN = rf"(?:{MISSING_PATTERN}|{NUMBER_PATTERN})"


def normalize_number(value):
    """Convert numeric values into comparable decimals."""
    if value is None or isinstance(value, bool):
        return None

    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError, TypeError):
        return None


def is_missing_value(value):
    if value is None:
        return True

    return str(value).strip().upper() in {
        "N/A", "N.A.", "NULL", "NONE"
    }


def check_extraction(document_text, extracted_data):
    errors = []
    text = " ".join(document_text.split())

    items = extracted_data.get("items", [])

    first_item_code = next(
        (
            str(item["item_code"])
            for item in items
            if item.get("item_code")
        ),
        None
    )

    column_order = detect_column_order(
        document_text,
        first_item_code
    )

    if column_order is None:
        errors.append(
            "Document column layout could not be identified reliably."
        )

    doc_number = extracted_data.get("document_number")

    if not doc_number or str(doc_number) not in text:
        errors.append(
            f"Missing or unsupported document number: {doc_number}"
        )

    doc_type = str(
        extracted_data.get("document_type") or ""
    ).lower()

    if "invoice" in doc_type:
        expected_prefix = "INV-"
    elif "goods receipt" in doc_type or "grn" in doc_type:
        expected_prefix = "GRN-"
    elif "purchase order" in doc_type:
        expected_prefix = "PO-"
    else:
        expected_prefix = None

    if expected_prefix and (
        not doc_number
        or not str(doc_number).upper().startswith(expected_prefix)
    ):
        errors.append(
            f"Incorrect document number for {doc_type}: {doc_number}"
        )

    for item in items:
        code = str(item.get("item_code") or "").strip()
        description = str(
            item.get("description") or ""
        ).strip()

        if not code or not re.search(
            rf"(?<!\w){re.escape(code)}(?!\w)",
            text,
            re.IGNORECASE
        ):
            errors.append(f"Product code not found: {code}")
            continue

        if not description:
            errors.append(
                f"Product details do not match PDF: {code}"
            )
            continue

        if column_order is None:
            continue

        row_pattern = re.compile(
            rf"(?<!\w){re.escape(code)}(?!\w)"
            rf"\s+{re.escape(description)}"
            + "".join(
                rf"\s+({VALUE_PATTERN})"
                for _ in column_order
            )
            + r"(?=\s|$)",
            re.IGNORECASE
        )

        match = row_pattern.search(text)

        if not match:
            errors.append(
                f"Product details do not match PDF: {code}"
            )
            continue

        for position, field in enumerate(
            column_order, start=1
        ):
            extracted_value = item.get(field)
            pdf_value = match.group(position)

            if is_missing_value(pdf_value):
                valid = is_missing_value(extracted_value)
            else:
                valid = (
                    normalize_number(extracted_value)
                    is not None
                    and normalize_number(extracted_value)
                    == normalize_number(pdf_value)
                )

            if not valid:
                errors.append(
                    f"Product details do not match PDF: {code}"
                )
                break

    codes = [
        str(item.get("item_code") or "").strip().lower()
        for item in items
    ]

    if len(codes) != len(set(codes)):
        errors.append(
            "Repeated item codes require review"
        )

    return errors
