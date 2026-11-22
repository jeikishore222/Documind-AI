
from core.extraction_checker import check_extraction


def make_data(quantity=10, unit_price=800, amount=8000):
    return {
        "document_type": "Purchase Order",
        "document_number": "PO-001",
        "items": [
            {
                "item_code": "KB-101",
                "description": "USB Keyboard",
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": amount,
            }
        ],
    }


def test_layout_a_correct_extraction():
    text = """
Purchase Order PO-001
Item Code Description Quantity Unit Price Line Total
KB-101 USB Keyboard 10 800.00 8000.00
"""
    assert check_extraction(text, make_data()) == []


def test_layout_b_correct_extraction():
    text = """
Purchase Order PO-001
SKU Product Price Each Billed Units Line Amount
KB-101 USB Keyboard 800.00 10 8000.00
"""
    assert check_extraction(text, make_data()) == []


def test_layout_b_wrong_quantity():
    text = """
Purchase Order PO-001
SKU Product Price Each Billed Units Line Amount
KB-101 USB Keyboard 800.00 10 8000.00
"""
    errors = check_extraction(text, make_data(quantity=8))
    assert any("KB-101" in error for error in errors)


def test_layout_b_wrong_price():
    text = """
Purchase Order PO-001
SKU Product Price Each Billed Units Line Amount
KB-101 USB Keyboard 800.00 10 8000.00
"""
    errors = check_extraction(text, make_data(unit_price=900))
    assert any("KB-101" in error for error in errors)


def test_missing_headers_rejected():
    text = """
Purchase Order PO-001
KB-101 USB Keyboard 10 800.00 8000.00
"""
    errors = check_extraction(text, make_data())
    assert any("column layout" in error.lower() for error in errors)


def test_wrong_document_number_rejected():
    text = """
Purchase Order PO-001
Item Code Description Quantity Unit Price Line Total
KB-101 USB Keyboard 10 800.00 8000.00
"""
    data = make_data()
    data["document_number"] = "PO-999"
    errors = check_extraction(text, data)
    assert any("document number" in error.lower() for error in errors)


def test_duplicate_product_codes_rejected():
    text = """
Purchase Order PO-001
Item Code Description Quantity Unit Price Line Total
KB-101 USB Keyboard 10 800.00 8000.00
"""
    data = make_data()
    data["items"].append(data["items"][0].copy())
    errors = check_extraction(text, data)
    assert any("repeated item codes" in error.lower() for error in errors)
