
import re
from decimal import Decimal, InvalidOperation
from core.column_layout import detect_column_order

NUMBER_PATTERN = r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w.])"

TOTAL_LABEL_PATTERN = (
    r"(?:PO\s+Total|Invoice\s+Total|GRN\s+Total|"
    r"Grand\s+Total|Sub\s*Total|Total\s+Amount|Total)"
)


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def code_pattern(code):
    return re.compile(
        r"(?<![A-Za-z0-9])"
        + re.escape(str(code))
        + r"(?![A-Za-z0-9])",
        re.IGNORECASE
    )


def to_decimal(value):
    try:
        if value is None or isinstance(value, bool):
            return None
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError, TypeError):
        return None


def find_product_block(document_text, item_code, all_item_codes):
    lines = [
        line.strip()
        for line in document_text.splitlines()
        if line.strip()
    ]

    markers = []

    for line_index, line in enumerate(lines):
        for code in all_item_codes:
            match = code_pattern(code).search(line)

            if match:
                markers.append((
                    line_index,
                    match.start(),
                    match.end(),
                    code
                ))
                break

    markers.sort()

    target = str(item_code).lower()

    for position, marker in enumerate(markers):
        line_index, start, end, code = marker

        if str(code).lower() != target:
            continue

        next_marker = (
            markers[position + 1]
            if position + 1 < len(markers)
            else None
        )

        if next_marker and next_marker[0] == line_index:
            block = lines[line_index][start:next_marker[1]]
        else:
            end_line = (
                next_marker[0]
                if next_marker
                else len(lines)
            )

            block_lines = [
                lines[line_index][start:]
            ] + lines[line_index + 1:end_line]

            block = "\n".join(block_lines)

        # Remove total/footer sections from the product block
        block = re.split(
            rf"(?im)^\s*{TOTAL_LABEL_PATTERN}\b"
            rf"(?:\s*:\s*|\s+|$)",
            block,
            maxsplit=1
        )[0]

        block = re.split(
            r"(?im)^\s*Synthetic test document\b",
            block,
            maxsplit=1
        )[0]

        return block.strip()

    return None


def check_source_grounding(document_text, extracted_data):
    issues = []
    checks = []

    items = extracted_data.get("items", [])

    all_item_codes = [
        str(item["item_code"])
        for item in items
        if item.get("item_code")
    ]
    column_order = detect_column_order(
        document_text,
        all_item_codes[0] if all_item_codes else None
    )

    if column_order is None:
        issues.append(
            "Document column layout could not be identified reliably."
        )

    def record_check(field, value, supported, message):
        checks.append({
            "field": field,
            "value": value,
            "supported": bool(supported)
        })

        if not supported:
            issues.append(message)

    # Check document identifiers
    for field in ["document_number", "po_number"]:
        value = extracted_data.get(field)

        if not value:
            continue

        supported = bool(
            code_pattern(value).search(document_text)
        )

        record_check(
            field,
            value,
            supported,
            f"{field}: '{value}' was not found in the source."
        )

    # Check each product
    for index, item in enumerate(items, start=1):
        code = item.get("item_code")
        description = item.get("description")

        product_block = (
            find_product_block(
                document_text,
                code,
                all_item_codes
            )
            if code
            else None
        )

        record_check(
            f"items[{index}].item_code",
            code,
            product_block is not None,
            f"Item {index}: code '{code}' was not found in the source."
        )

        if product_block is None:
            continue

        # Remove the product code from the beginning
        remaining_text = code_pattern(code).sub(
            "",
            product_block,
            count=1
        ).strip()

        description_supported = bool(
            description
            and normalize_text(remaining_text).startswith(
                normalize_text(description)
            )
        )

        if description:
            record_check(
                f"items[{index}].description",
                description,
                description_supported,
                f"Item {index}: description '{description}' "
                "was not found in the matching product block."
            )

        # Remove the description BEFORE extracting numeric tokens.
        # This prevents "Monitor 24 inch" from contributing "24".
        if description_supported:
            normalized_remaining = re.sub(
                r"\s+",
                " ",
                remaining_text
            ).strip()

            numeric_section = normalized_remaining[
                len(str(description).strip()): 
            ].strip()
        else:
            numeric_section = ""

        numeric_tokens = re.findall(
            rf"(?<![\w.])(?:N/A|N\.A\.|NULL|NONE|{NUMBER_PATTERN})(?![\w.])",
            numeric_section,
            flags=re.IGNORECASE
        )

        has_price_fields = (
            item.get("unit_price") is not None
            and item.get("amount") is not None
        )

        expected_count = len(column_order) if column_order else (
            3 if has_price_fields else 1
        )

        positional_check_possible = (
            description_supported
            and len(numeric_tokens) == expected_count
        )

        for position, field in enumerate(
            column_order or ["quantity", "unit_price", "amount"]
        ):
            value = item.get(field)

            if value is None:
                continue

            supported = (
                positional_check_possible
                and position < len(numeric_tokens)
                and to_decimal(value)
                == to_decimal(numeric_tokens[position])
            )

            record_check(
                f"items[{index}].{field}",
                value,
                supported,
                f"Item {index}: {field} '{value}' "
                "could not be confirmed in the expected "
                "position of the product row."
            )

        quantity = to_decimal(item.get("quantity"))
        unit_price = to_decimal(item.get("unit_price"))
        amount = to_decimal(item.get("amount"))

        if all(
            value is not None
            for value in [quantity, unit_price, amount]
        ):
            supported = (
                abs(quantity * unit_price - amount)
                <= Decimal("0.01")
            )

            record_check(
                f"items[{index}].calculated_amount",
                item.get("amount"),
                supported,
                f"Item {index}: quantity \u00d7 unit price "
                "does not equal the extracted amount."
            )

    # Check the document total, including when it is on the next line
    total_amount = extracted_data.get("total_amount")

    if total_amount is not None:
        total_pattern = (
            rf"(?im)^\s*{TOTAL_LABEL_PATTERN}"
            rf"\s*:?\s*(?:INR|Rs\.?)?\s*"
            rf"({NUMBER_PATTERN})\s*$"
        )

        source_totals = re.findall(
            total_pattern,
            document_text
        )

        supported = any(
            to_decimal(value) == to_decimal(total_amount)
            for value in source_totals
        )

        record_check(
            "total_amount",
            total_amount,
            supported,
            f"Total amount '{total_amount}' "
            "was not confirmed on a labeled total line."
        )

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "checks": checks
    }
