
import csv
import io
import json
from datetime import datetime, timezone
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether
)


def generate_json_report(po_data, invoice_data, grn_data, results):
    report = {
        "report_type": "Three-Way Document Verification",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purchase_order": po_data["document_number"],
        "supplier_invoice": invoice_data["document_number"],
        "goods_receipt_note": grn_data["document_number"],
        "total_items": len(results),
        "matched_items": sum(
            1 for item in results
            if item["status"] == "Matched"
        ),
        "mismatched_items": sum(
            1 for item in results
            if item["status"] == "Mismatch"
        ),
        "results": results
    }

    return json.dumps(report, indent=4).encode("utf-8")


def generate_csv_report(results):
    output = io.StringIO(newline="")

    fieldnames = [
        "item_code",
        "description",
        "ordered_qty",
        "invoiced_qty",
        "received_qty",
        "po_unit_price",
        "invoice_unit_price",
        "invoice_value",
        "received_value_at_po_price",
        "financial_difference",
        "excess_billed_qty",
        "excess_billed_value",
        "status",
        "issues"
    ]

    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        extrasaction="ignore"
    )

    writer.writeheader()

    for item in results:
        row = item.copy()
        row["issues"] = "; ".join(item["issues"])
        writer.writerow(row)

    return output.getvalue().encode("utf-8-sig")


def create_status_chart(results):
    matched = sum(
        1 for item in results
        if item["status"] == "Matched"
    )

    mismatched = sum(
        1 for item in results
        if item["status"] == "Mismatch"
    )

    fig, ax = plt.subplots(figsize=(5, 3.5))

    values = []
    labels = []
    chart_colors = []

    if matched:
        values.append(matched)
        labels.append("Matched")
        chart_colors.append("#22c55e")

    if mismatched:
        values.append(mismatched)
        labels.append("Mismatched")
        chart_colors.append("#ef4444")

    if values:
        ax.pie(
            values,
            labels=labels,
            colors=chart_colors,
            autopct="%1.1f%%",
            startangle=90
        )
        ax.axis("equal")
    else:
        ax.text(
            0.5,
            0.5,
            "No verification data",
            ha="center",
            va="center",
            transform=ax.transAxes
        )
        ax.axis("off")

    ax.set_title("Product Verification Status")

    buffer = io.BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)
    buffer.seek(0)

    return buffer


def create_financial_chart(results):
    product_codes = [
        str(item["item_code"])
        for item in results
    ]

    differences = [
        item["financial_difference"] or 0
        for item in results
    ]

    chart_height = max(3.5, min(9, len(results) * 0.45 + 2))

    fig, ax = plt.subplots(
        figsize=(7, chart_height)
    )

    if product_codes:
        positions = list(range(len(product_codes)))

        bar_colors = [
            "#ef4444" if value > 0
            else "#22c55e" if value == 0
            else "#3b82f6"
            for value in differences
        ]

        ax.barh(
            positions,
            differences,
            color=bar_colors
        )

        ax.set_yticks(positions)
        ax.set_yticklabels(product_codes)
        ax.invert_yaxis()

        ax.axvline(
            x=0,
            color="#555555",
            linewidth=0.8
        )

        ax.set_xlabel("Financial Difference (INR)")
    else:
        ax.text(
            0.5,
            0.5,
            "No financial data",
            ha="center",
            va="center",
            transform=ax.transAxes
        )

    ax.set_title("Financial Difference by Product")
    ax.grid(axis="x", alpha=0.2)

    fig.tight_layout()

    buffer = io.BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)
    buffer.seek(0)

    return buffer


def generate_pdf_report(po_data, invoice_data, grn_data, results):
    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elements = []

    matched_items = sum(
        1 for item in results
        if item["status"] == "Matched"
    )

    mismatched_items = sum(
        1 for item in results
        if item["status"] == "Mismatch"
    )

    total_invoice_value = sum(
        item["invoice_value"] or 0
        for item in results
    )

    total_financial_difference = sum(
        item["financial_difference"] or 0
        for item in results
    )

    total_excess_billed_value = sum(
        item["excess_billed_value"] or 0
        for item in results
    )

    elements.append(
        Paragraph("DocuMind AI", styles["Title"])
    )

    elements.append(
        Paragraph(
            "Three-Way Document Verification Report",
            styles["Heading2"]
        )
    )

    elements.append(
        Paragraph(
            "Generated: "
            + datetime.now(timezone.utc).strftime(
                "%d %B %Y, %H:%M UTC"
            ),
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 16))

    document_details = [
        ["Purchase Order", str(po_data["document_number"])],
        ["Supplier Invoice", str(invoice_data["document_number"])],
        ["Goods Receipt Note", str(grn_data["document_number"])],
        ["Total Products", str(len(results))],
        ["Matched Products", str(matched_items)],
        ["Mismatched Products", str(mismatched_items)]
    ]

    details_table = Table(
        document_details,
        colWidths=[160, 300]
    )

    details_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
    ]))

    elements.append(details_table)
    elements.append(Spacer(1, 18))

    elements.append(
        Paragraph("Financial Summary", styles["Heading2"])
    )

    financial_details = [
        [
            "Total Invoice Value",
            f"INR {total_invoice_value:,.2f}"
        ],
        [
            "Net Financial Difference",
            f"INR {total_financial_difference:,.2f}"
        ],
        [
            "Excess Billed Value",
            f"INR {total_excess_billed_value:,.2f}"
        ]
    ]

    financial_table = Table(
        financial_details,
        colWidths=[230, 230]
    )

    financial_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
    ]))

    elements.append(financial_table)
    elements.append(Spacer(1, 18))

    elements.append(
        Paragraph(
            "Verification Analytics",
            styles["Heading2"]
        )
    )

    status_chart = create_status_chart(results)

    elements.append(
        Image(
            status_chart,
            width=350,
            height=245
        )
    )

    elements.append(Spacer(1, 12))

    financial_chart = create_financial_chart(results)

    elements.append(
        Image(
            financial_chart,
            width=460,
            height=260
        )
    )

    elements.append(Spacer(1, 18))

    elements.append(
        Paragraph(
            "Detailed Verification Results",
            styles["Heading2"]
        )
    )

    for item in results:
        item_elements = []

        description = escape(str(item["description"]))
        item_code = escape(str(item["item_code"]))
        status = escape(str(item["status"]))

        item_elements.append(
            Paragraph(
                f"<b>{description} ({item_code})</b>",
                styles["Heading3"]
            )
        )

        item_elements.append(
            Paragraph(
                f"Status: {status}",
                styles["Normal"]
            )
        )

        item_elements.append(
            Paragraph(
                f"Ordered: {item['ordered_qty']} | "
                f"Invoiced: {item['invoiced_qty']} | "
                f"Received: {item['received_qty']}",
                styles["Normal"]
            )
        )

        if item["financial_difference"] is not None:
            item_elements.append(
                Paragraph(
                    "Financial Difference: INR "
                    f"{item['financial_difference']:,.2f}",
                    styles["Normal"]
                )
            )

        if item["excess_billed_value"] is not None:
            item_elements.append(
                Paragraph(
                    "Excess Billed Value: INR "
                    f"{item['excess_billed_value']:,.2f}",
                    styles["Normal"]
                )
            )

        if item["issues"]:
            item_elements.append(
                Paragraph(
                    "<b>Discrepancies:</b>",
                    styles["Normal"]
                )
            )

            for issue in item["issues"]:
                item_elements.append(
                    Paragraph(
                        "&#8226; "+ escape(str(issue)),
                        styles["Normal"]
                    )
                )
                item_elements.append(Spacer(1, 5))

        else:
            item_elements.append(
                Paragraph(
                    "No discrepancies detected.",
                    styles["Normal"]
                )
            )

        item_elements.append(Spacer(1, 12))

        elements.append(
            KeepTogether(item_elements)
        )

    elements.append(Spacer(1, 12))

    elements.append(
        Paragraph(
            "Note: Financial differences are comparison "
            "metrics, not confirmed losses or final payable "
            "amounts. Taxes, discounts and contractual "
            "adjustments are not included.",
            styles["Italic"]
        )
    )

    document.build(elements)

    return buffer.getvalue()
