
from core.source_grounding import check_source_grounding


def make_data(quantity=10, unit_price=800, amount=8000):
    return {
        "items": [
            {
                "item_code": "KB-101",
                "description": "USB Keyboard",
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": amount,
            }
        ],
        "total_amount": amount,
    }


def test_correct_product_data():
    text = """
PURCHASE ORDER
Item Code Description Quantity Unit Price Line Total
KB-101 USB Keyboard 10 800.00 8000.00
PO Total: INR 8000.00
"""
    result = check_source_grounding(text, make_data())

    assert result["passed"] is True
    assert result["issues"] == []


def test_incorrect_quantity():
    text = """
PURCHASE ORDER
Item Code Description Quantity Unit Price Line Total
KB-101 USB Keyboard 10 800.00 8000.00
PO Total: INR 8000.00
"""
    result = check_source_grounding(
        text, make_data(quantity=5)
    )

    assert result["passed"] is False
    assert any(
        "quantity" in issue.lower()
        for issue in result["issues"]
    )


def test_incorrect_financial_calculation():
    text = """
PURCHASE ORDER
Item Code Description Quantity Unit Price Line Total
KB-101 USB Keyboard 10 800.00 9000.00
PO Total: INR 9000.00
"""
    result = check_source_grounding(
        text, make_data(amount=9000)
    )

    assert result["passed"] is False
    assert any(
        "quantity × unit price" in issue
        for issue in result["issues"]
    )


def test_layout_a_quantity_first():
    text = """
PURCHASE ORDER
Item Code Description Quantity Unit Price Line Total
KB-101 USB Keyboard 10 800.00 8000.00
PO Total: INR 8000.00
"""
    result = check_source_grounding(text, make_data())

    assert result["passed"] is True


def test_layout_b_price_first():
    text = """
PURCHASE ORDER
SKU Product Price Each Billed Units Line Amount
KB-101 USB Keyboard 800.00 10 8000.00
PO Total: INR 8000.00
"""
    result = check_source_grounding(text, make_data())

    assert result["passed"] is True
    assert result["issues"] == []


def test_layout_b_wrong_quantity():
    text = """
PURCHASE ORDER
SKU Product Price Each Billed Units Line Amount
KB-101 USB Keyboard 800.00 10 8000.00
PO Total: INR 8000.00
"""
    result = check_source_grounding(
        text, make_data(quantity=8)
    )

    assert result["passed"] is False
    assert any(
        "quantity" in issue.lower()
        for issue in result["issues"]
    )


def test_layout_b_wrong_unit_price():
    text = """
PURCHASE ORDER
SKU Product Price Each Billed Units Line Amount
KB-101 USB Keyboard 800.00 10 8000.00
PO Total: INR 8000.00
"""
    result = check_source_grounding(
        text, make_data(unit_price=900)
    )

    assert result["passed"] is False
    assert any(
        "unit_price" in issue.lower()
        for issue in result["issues"]
    )


def test_missing_column_headers_rejected():
    text = """
KB-101 USB Keyboard 10 800.00 8000.00
PO Total: INR 8000.00
"""
    result = check_source_grounding(text, make_data())

    assert result["passed"] is False
    assert any(
        "column layout" in issue.lower()
        for issue in result["issues"]
    )


def test_swapped_quantity_and_price_rejected():
    text = """
PURCHASE ORDER
SKU Product Price Each Billed Units Line Amount
KB-101 USB Keyboard 800.00 10 8000.00
PO Total: INR 8000.00
"""
    result = check_source_grounding(
        text,
        make_data(quantity=800, unit_price=10)
    )

    assert result["passed"] is False
    assert any(
        "quantity" in issue.lower()
        or "unit_price" in issue.lower()
        for issue in result["issues"]
    )


def test_grn_with_missing_prices():
    document_text = """
GOODS RECEIPT NOTE
Item Code
Description
Quantity
Unit Price (INR)
Amount (INR)
KB-101
USB Keyboard
10
N/A
N/A
MS-202
Wireless Mouse
4
N/A
N/A
Total Units Received: INR 14
"""

    extracted_data = {
        "items": [
            {
                "item_code": "KB-101",
                "description": "USB Keyboard",
                "quantity": 10,
                "unit_price": None,
                "amount": None,
            },
            {
                "item_code": "MS-202",
                "description": "Wireless Mouse",
                "quantity": 4,
                "unit_price": None,
                "amount": None,
            },
        ],
        "total_amount": None,
    }

    result = check_source_grounding(
        document_text, extracted_data
    )

    assert result["passed"], result["issues"]


def test_grn_wrong_quantity_with_missing_prices():
    document_text = """
GOODS RECEIPT NOTE
Item Code
Description
Quantity
Unit Price (INR)
Amount (INR)
PR-501
Printer Paper
12
N/A
N/A
"""

    extracted_data = {
        "items": [
            {
                "item_code": "PR-501",
                "description": "Printer Paper",
                "quantity": 20,
                "unit_price": None,
                "amount": None,
            }
        ],
        "total_amount": None,
    }

    result = check_source_grounding(
        document_text, extracted_data
    )

    assert result["passed"] is False
    assert any(
        "quantity" in issue.lower()
        for issue in result["issues"]
    )
