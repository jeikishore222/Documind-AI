
import re


COLUMN_ALIASES = {
    "quantity": [
        "order quantity",
        "ordered quantity",
        "billed units",
        "received quantity",
        "received units",
        "qty ordered",
        "qty received",
        "invoice qty",
        "quantity",
        "qty",
        "units",
    ],
    "unit_price": [
        "unit price",
        "unit rate",
        "price each",
        "price per unit",
        "unit cost",
        "rate per unit",
        "rate",
    ],
    "amount": [
        "extended value",
        "line amount",
        "line total",
        "extended amount",
        "total price",
        "amount",
        "value",
    ],
}


def normalize_header(text):
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def detect_column_order(document_text, first_item_code=None):
    """
    Detect the order of numeric product columns from the
    document's table headers.

    Returns a list of field names or None if the layout
    cannot be identified reliably.
    """
    lines = [
        normalize_header(line)
        for line in document_text.splitlines()
        if line.strip()
    ]

    if first_item_code:
        first_code = str(first_item_code).lower()

        for index, line in enumerate(lines):
            if re.search(
                rf"(?<![a-z0-9]){re.escape(first_code)}(?![a-z0-9])",
                line
            ):
                lines = lines[:index]
                break

    # Look at the table header, not the product values.
    header_text = " ".join(lines[-25:])

    matches = []

    for field, aliases in COLUMN_ALIASES.items():
        found = []

        for alias in aliases:
            pattern = (
                rf"(?<![a-z0-9])"
                rf"{re.escape(alias)}"
                rf"(?![a-z0-9])"
            )

            for match in re.finditer(pattern, header_text):
                found.append((match.start(), match.end()))

        if found:
            # Prefer the longest matching header phrase.
            found.sort(key=lambda x: (-(x[1] - x[0]), x[0]))
            matches.append((found[0][0], field))

    fields = [field for _, field in sorted(matches)]

    if "quantity" not in fields:
        return None

    if "unit_price" in fields and "amount" in fields:
        return fields

    if fields == ["quantity"]:
        return fields

    return None
