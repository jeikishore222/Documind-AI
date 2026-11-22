
import pytest

from core.verifier import verify_documents


PO_NUMBER = "PO-2026-1042"


def make_document(quantity, unit_price=None):
    return {
        "po_number": PO_NUMBER,
        "items": [
            {
                "item_code": "KB-101",
                "description": "USB Keyboard",
                "quantity": quantity,
                "unit_price": unit_price
            }
        ]
    }


def test_matching_documents():
    po = make_document(10, 800)
    invoice = make_document(10, 800)
    grn = make_document(10)

    results = verify_documents(po, invoice, grn)

    assert len(results) == 1
    assert results[0]["status"] == "Matched"
    assert results[0]["issues"] == []
    assert results[0]["financial_difference"] == 0


def test_invoice_quantity_exceeds_order():
    po = make_document(10, 800)
    invoice = make_document(12, 800)
    grn = make_document(10)

    results = verify_documents(po, invoice, grn)

    assert results[0]["status"] == "Mismatch"
    assert (
        "Invoice quantity exceeds ordered quantity"
        in results[0]["issues"]
    )
    assert (
        "Invoice quantity exceeds received quantity"
        in results[0]["issues"]
    )
    assert results[0]["excess_billed_qty"] == 2
    assert results[0]["excess_billed_value"] == 1600


def test_invoice_price_mismatch():
    po = make_document(10, 800)
    invoice = make_document(10, 900)
    grn = make_document(10)

    results = verify_documents(po, invoice, grn)

    assert results[0]["status"] == "Mismatch"
    assert (
        "Invoice unit price differs from PO"
        in results[0]["issues"]
    )
    assert results[0]["financial_difference"] == 1000


def test_received_quantity_shortage():
    po = make_document(10, 800)
    invoice = make_document(10, 800)
    grn = make_document(8)

    results = verify_documents(po, invoice, grn)

    assert results[0]["status"] == "Mismatch"
    assert (
        "Received quantity is less than ordered"
        in results[0]["issues"]
    )
    assert results[0]["excess_billed_qty"] == 2
    assert results[0]["excess_billed_value"] == 1600


def test_item_missing_from_invoice():
    po = make_document(10, 800)

    invoice = {
        "po_number": PO_NUMBER,
        "items": []
    }

    grn = make_document(10)

    results = verify_documents(po, invoice, grn)

    assert results[0]["status"] == "Mismatch"
    assert (
        "Item missing from Supplier Invoice"
        in results[0]["issues"]
    )


def test_item_missing_from_grn():
    po = make_document(10, 800)
    invoice = make_document(10, 800)

    grn = {
        "po_number": PO_NUMBER,
        "items": []
    }

    results = verify_documents(po, invoice, grn)

    assert results[0]["status"] == "Mismatch"
    assert (
        "Item missing from Goods Receipt Note"
        in results[0]["issues"]
    )


def test_item_not_found_in_purchase_order():
    po = {
        "po_number": PO_NUMBER,
        "items": []
    }

    invoice = make_document(10, 800)
    grn = make_document(10)

    results = verify_documents(po, invoice, grn)

    assert results[0]["status"] == "Mismatch"
    assert (
        "Item not found in Purchase Order"
        in results[0]["issues"]
    )


def test_multiple_products_with_mixed_results():
    po = {
        "po_number": PO_NUMBER,
        "items": [
            {
                "item_code": "KB-101",
                "description": "USB Keyboard",
                "quantity": 10,
                "unit_price": 800
            },
            {
                "item_code": "MS-202",
                "description": "Wireless Mouse",
                "quantity": 5,
                "unit_price": 500
            }
        ]
    }

    invoice = {
        "po_number": PO_NUMBER,
        "items": [
            {
                "item_code": "KB-101",
                "description": "USB Keyboard",
                "quantity": 10,
                "unit_price": 800
            },
            {
                "item_code": "MS-202",
                "description": "Wireless Mouse",
                "quantity": 7,
                "unit_price": 550
            }
        ]
    }

    grn = {
        "po_number": PO_NUMBER,
        "items": [
            {
                "item_code": "KB-101",
                "description": "USB Keyboard",
                "quantity": 10
            },
            {
                "item_code": "MS-202",
                "description": "Wireless Mouse",
                "quantity": 4
            }
        ]
    }

    results = verify_documents(po, invoice, grn)

    assert len(results) == 2

    by_code = {
        item["item_code"]: item
        for item in results
    }

    assert by_code["KB-101"]["status"] == "Matched"
    assert by_code["MS-202"]["status"] == "Mismatch"

    mouse = by_code["MS-202"]

    assert mouse["financial_difference"] == 1850
    assert mouse["excess_billed_qty"] == 3
    assert mouse["excess_billed_value"] == 1650


# -----------------------------------------
# NEW TESTS: PO NUMBER VALIDATION
# -----------------------------------------

def test_invoice_po_number_mismatch():
    po = make_document(10, 800)
    invoice = make_document(10, 800)
    grn = make_document(10)

    invoice["po_number"] = "PO-2026-9999"

    with pytest.raises(
        ValueError,
        match="PO Number Mismatch"
    ):
        verify_documents(po, invoice, grn)


def test_grn_po_number_mismatch():
    po = make_document(10, 800)
    invoice = make_document(10, 800)
    grn = make_document(10)

    grn["po_number"] = "PO-2026-9999"

    with pytest.raises(
        ValueError,
        match="PO Number Mismatch"
    ):
        verify_documents(po, invoice, grn)


def test_missing_purchase_order_number():
    po = make_document(10, 800)
    invoice = make_document(10, 800)
    grn = make_document(10)

    po.pop("po_number")

    with pytest.raises(
        ValueError,
        match="Purchase Order number is missing"
    ):
        verify_documents(po, invoice, grn)
