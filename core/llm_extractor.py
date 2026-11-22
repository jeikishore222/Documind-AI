
import re
import json
import requests
from pydantic import ValidationError
from core.schemas import BusinessDocument


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"
MAX_RETRIES = 3


def find_field(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)

        if match:
            return match.group(1).strip()

    return None


def detect_document_type(text):
    if re.search(r"\b(goods\s+receipt\s+note|GRN)\b", text, re.IGNORECASE):
        return "Goods Receipt Note"

    if re.search(r"\b(supplier\s+invoice|tax\s+invoice|invoice)\b", text, re.IGNORECASE):
        return "Supplier Invoice"

    if re.search(r"\b(purchase\s+order|PO)\b", text, re.IGNORECASE):
        return "Purchase Order"

    return None


def correct_document_identifiers(data, document_text):
    document_type = detect_document_type(document_text)

    invoice_number = find_field(
        document_text,
        [
            r"^\s*(?:Invoice\s*(?:Number|No\.?|#))\s*[:#-]\s*([^\s,;]+)"
        ]
    )

    grn_number = find_field(
        document_text,
        [
            r"^\s*(?:GRN\s*(?:Number|No\.?|#))\s*[:#-]\s*([^\s,;]+)"
        ]
    )

    po_number = find_field(
        document_text,
        [
            r"^\s*(?:PO|P\.O\.|Purchase\s+Order)\s*(?:Number|No\.?|#)\s*[:#-]\s*([^\s,;]+)"
        ]
    )

    if document_type:
        data["document_type"] = document_type

    if document_type == "Supplier Invoice" and invoice_number:
        data["document_number"] = invoice_number

    elif document_type == "Goods Receipt Note" and grn_number:
        data["document_number"] = grn_number

    elif document_type == "Purchase Order" and po_number:
        data["document_number"] = po_number

    if po_number:
        data["po_number"] = po_number

    return data


def clean_items(data):
    items = data.get("items")

    if not isinstance(items, list):
        return data

    cleaned_items = []

    for item in items:
        if not isinstance(item, dict):
            continue

        if set(item.keys()) == {"total_amount"}:
            if data.get("total_amount") is None:
                data["total_amount"] = item["total_amount"]
            continue

        cleaned_items.append(item)

    data["items"] = cleaned_items

    return data


def extract_document_data(document_text):
    if not document_text or not document_text.strip():
        raise ValueError("The document contains no readable text.")

    base_prompt = f"""
You are a precise business document extraction system.

Extract information from the document below.

Return ONLY a valid JSON object.

Required fields:
document_type
document_number
po_number
buyer
supplier
items
total_amount

Each item must contain:
item_code
description
quantity
unit_price
amount

RULES:
1. Identify the document type from the document.
2. Extract only actual product rows.
3. Preserve item codes and descriptions exactly.
4. Do not duplicate products.
5. Never invent missing information.
6. Use null for missing values where appropriate.
7. Quantities, prices, and amounts must be numeric.
8. Never treat summary rows as products.
9. Never confuse total quantity with total amount.
10. total_amount must be a monetary amount or null.
11. For Purchase Orders, document_number is the PO number.
12. For Supplier Invoices, document_number is the invoice number.
13. For Goods Receipt Notes, document_number is the GRN number.
14. po_number is the purchase order reference.
15. Do not use the referenced PO number as an invoice or GRN number.
16. For GRNs, extract the actual received quantities.
17. Do not calculate or guess missing prices or amounts.
18. Include every required field, even if its value is null.
19. Return JSON only.

DOCUMENT:
{document_text}
"""

    last_error = None
    correction_feedback = ""

    for attempt in range(MAX_RETRIES):
        prompt = base_prompt + correction_feedback

        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0
                    }
                },
                timeout=180
            )

            response.raise_for_status()
            result = response.json()
            raw_output = result.get("response", "")

            extracted_data = json.loads(raw_output)

            if not isinstance(extracted_data, dict):
                raise ValueError("AI returned JSON that is not an object.")

            extracted_data = clean_items(extracted_data)

            extracted_data = correct_document_identifiers(
                extracted_data,
                document_text
            )

            validated_data = BusinessDocument.model_validate(
                extracted_data
            )

            return validated_data.model_dump()

        except (
            requests.RequestException,
            json.JSONDecodeError,
            ValidationError,
            ValueError,
            KeyError
        ) as error:
            last_error = error

            correction_feedback = f"""

The previous extraction failed.

ERROR:
{str(error)[:1200]}

Correct the extraction using the original document.
Return one complete valid JSON object.
Do not invent information.
"""

    raise ValueError(
        f"AI extraction failed after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )

