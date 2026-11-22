
from decimal import Decimal


def money(value):
    if value is None:
        return None
    return Decimal(str(value))


def verify_documents(po_data, invoice_data, grn_data):

    po_number = po_data.get("po_number")
    invoice_po_number = invoice_data.get("po_number")
    grn_po_number = grn_data.get("po_number")

    if not po_number:
        raise ValueError("Purchase Order number is missing")

    if invoice_po_number != po_number:
        raise ValueError(
            "PO Number Mismatch: Supplier Invoice "
            "does not match the Purchase Order"
        )

    if grn_po_number != po_number:
        raise ValueError(
            "PO Number Mismatch: Goods Receipt Note "
            "does not match the Purchase Order"
        )

    results = []
    po_items = {
        item["item_code"]: item
        for item in po_data["items"]
    }

    invoice_items = {
        item["item_code"]: item
        for item in invoice_data["items"]
    }

    grn_items = {
        item["item_code"]: item
        for item in grn_data["items"]
    }

    all_codes = set(po_items) | set(invoice_items) | set(grn_items)

    for code in sorted(all_codes):
        po = po_items.get(code)
        invoice = invoice_items.get(code)
        grn = grn_items.get(code)

        issues = []

        ordered_qty = po["quantity"] if po else None
        invoiced_qty = invoice["quantity"] if invoice else None
        received_qty = grn["quantity"] if grn else None

        po_price = money(po["unit_price"]) if po else None
        invoice_price = (
            money(invoice["unit_price"]) if invoice else None
        )

        if not po:
            issues.append("Item not found in Purchase Order")

        if not invoice:
            issues.append("Item missing from Supplier Invoice")

        if not grn:
            issues.append("Item missing from Goods Receipt Note")

        if po and invoice:
            if invoiced_qty > ordered_qty:
                issues.append(
                    "Invoice quantity exceeds ordered quantity"
                )

            if po_price != invoice_price:
                issues.append(
                    "Invoice unit price differs from PO"
                )

        if po and grn:
            if received_qty < ordered_qty:
                issues.append(
                    "Received quantity is less than ordered"
                )

            if received_qty > ordered_qty:
                issues.append(
                    "Received quantity exceeds ordered quantity"
                )

        if invoice and grn:
            if invoiced_qty > received_qty:
                issues.append(
                    "Invoice quantity exceeds received quantity"
                )

        # Financial calculations
        invoice_value = None
        received_value_at_po_price = None
        financial_difference = None
        excess_billed_qty = None
        excess_billed_value = None

        if invoice and invoice_price is not None:
            invoice_value = (
                Decimal(str(invoiced_qty)) * invoice_price
            )

        if grn and po_price is not None:
            received_value_at_po_price = (
                Decimal(str(received_qty)) * po_price
            )

        if (
            invoice_value is not None
            and received_value_at_po_price is not None
        ):
            financial_difference = (
                invoice_value - received_value_at_po_price
            )

        if invoice and grn:
            excess_billed_qty = max(
                Decimal("0"),
                Decimal(str(invoiced_qty))
                - Decimal(str(received_qty))
            )

            if invoice_price is not None:
                excess_billed_value = (
                    excess_billed_qty * invoice_price
                )

        results.append({
            "item_code": code,
            "description": (po or invoice or grn)["description"],
            "ordered_qty": ordered_qty,
            "invoiced_qty": invoiced_qty,
            "received_qty": received_qty,
            "po_unit_price": (
                float(po_price) if po_price is not None else None
            ),
            "invoice_unit_price": (
                float(invoice_price)
                if invoice_price is not None else None
            ),
            "invoice_value": (
                float(invoice_value)
                if invoice_value is not None else None
            ),
            "received_value_at_po_price": (
                float(received_value_at_po_price)
                if received_value_at_po_price is not None
                else None
            ),
            "financial_difference": (
                float(financial_difference)
                if financial_difference is not None else None
            ),
            "excess_billed_qty": (
                float(excess_billed_qty)
                if excess_billed_qty is not None else None
            ),
            "excess_billed_value": (
                float(excess_billed_value)
                if excess_billed_value is not None else None
            ),
            "status": "Mismatch" if issues else "Matched",
            "issues": issues
        })

    return results
