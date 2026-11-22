
import re
from decimal import Decimal, InvalidOperation

from core.column_layout import detect_column_order


def normalize_number(value):
    """Convert formatted numeric values into comparable decimals."""
    if value is None or isinstance(value, bool):
        return None

    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError, TypeError):
        return None


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

    # Detect the numeric column order from table headers.
    column_order = detect_column_order(
        document_text,
        first_item_code
    )

    if column_order is None:
        errors.append(
            "Document column layout could not be identified reliably."
        )

    # Validate document number.
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

    # Validate product rows using the detected column order.
    number_pattern = r"-?\d[\d,]*(?:\.\d+)?"

    for item in items:
        code = str(item.get("item_code") or "").strip()
        description = str(item.get("description") or "").strip()

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

        # Never approve numeric values without a known layout.
        if column_order is None:
            continue

        row_pattern = re.compile(
            rf"(?<!\w){re.escape(code)}(?!\w)"
            rf"\s+{re.escape(description)}"
            + "".join(
                rf"\s+({number_pattern})"
                for _ in column_order
            )
            + rf"(?=\s|$)",
            re.IGNORECASE
        )

        match = row_pattern.search(text)

        if not match:
            errors.append(
                f"Product details do not match PDF: {code}"
            )
            continue

        for position, field in enumerate(column_order, start=1):
            extracted_value = normalize_number(item.get(field))
            pdf_value = normalize_number(match.group(position))

            if (
                extracted_value is None
                or pdf_value != extracted_value
            ):
                errors.append(
                    f"Product details do not match PDF: {code}"
                )
                break

    # Detect duplicate product codes.
    codes = [
        str(item.get("item_code") or "").strip().lower()
        for item in items
    ]

    if len(codes) != len(set(codes)):
        errors.append("Repeated item codes require review")

    return errors
