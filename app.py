
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from core.ocr_processor import extract_pdf_text
from core.llm_extractor import extract_document_data
from core.extraction_checker import check_extraction
from core.source_grounding import check_source_grounding
from core.verifier import verify_documents

from database.db_manager import (
    initialize_database,
    save_verification,
    get_verification_history,
    check_duplicate_invoice
)

from reports.report_generator import (
    generate_pdf_report,
    generate_csv_report,
    generate_json_report
)


st.set_page_config(
    page_title="DocuMind AI",
    page_icon="📄",
    layout="wide"
)

initialize_database()

st.title("📄 DocuMind AI")
st.subheader("AI-Powered Three-Way Document Verification")

st.write(
    "Upload your Purchase Order, Supplier Invoice, "
    "and Goods Receipt Note to begin verification."
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📋 Purchase Order")
    po_file = st.file_uploader(
        "Upload Purchase Order",
        type=["pdf"],
        key="po"
    )

with col2:
    st.subheader("🧾 Supplier Invoice")
    invoice_file = st.file_uploader(
        "Upload Supplier Invoice",
        type=["pdf"],
        key="invoice"
    )

with col3:
    st.subheader("📦 Goods Receipt Note")
    grn_file = st.file_uploader(
        "Upload Goods Receipt Note",
        type=["pdf"],
        key="grn"
    )

st.divider()

if st.button("Verify Documents", type="primary"):

    if not all([po_file, invoice_file, grn_file]):
        st.warning("Please upload all three PDF documents.")

    else:
        try:
            po_text = extract_pdf_text(po_file)
            invoice_text = extract_pdf_text(invoice_file)
            grn_text = extract_pdf_text(grn_file)

            if not all([
                po_text.strip(),
                invoice_text.strip(),
                grn_text.strip()
            ]):
                st.error(
                    "One or more PDFs contain no readable text."
                )
                st.stop()

            st.success("All three PDFs processed successfully!")

            st.subheader("Extracted Document Text")

            with st.expander("Purchase Order Text"):
                st.text(po_text)

            with st.expander("Supplier Invoice Text"):
                st.text(invoice_text)

            with st.expander("Goods Receipt Note Text"):
                st.text(grn_text)

            with st.spinner(
                "AI is extracting document information..."
            ):
                po_data = extract_document_data(po_text)
                invoice_data = extract_document_data(invoice_text)
                grn_data = extract_document_data(grn_text)

            st.subheader("AI Extracted Information")

            with st.expander("Purchase Order JSON"):
                st.json(po_data)

            with st.expander("Supplier Invoice JSON"):
                st.json(invoice_data)

            with st.expander("Goods Receipt Note JSON"):
                st.json(grn_data)

            documents = [
                ("Purchase Order", po_text, po_data),
                ("Supplier Invoice", invoice_text, invoice_data),
                ("Goods Receipt Note", grn_text, grn_data)
            ]

            st.subheader("Extraction Accuracy Check")

            all_errors = []

            for name, original_text, extracted_data in documents:
                errors = check_extraction(
                    original_text,
                    extracted_data
                )

                if errors:
                    st.error(
                        f"{name}: {len(errors)} issue(s) detected"
                    )

                    all_errors.extend(errors)

                    for error in errors:
                        st.write(f"• {error}")

                else:
                    st.success(
                        f"{name}: No issues detected by basic checks"
                    )

            st.divider()
            st.subheader("AI Source Grounding Check")

            grounding_warnings = []

            for name, original_text, extracted_data in documents:
                result = check_source_grounding(
                    original_text,
                    extracted_data
                )

                if result["passed"]:
                    st.success(
                        f"{name}: Source Grounding Passed"
                    )

                else:
                    st.warning(
                        f"{name}: Source Grounding Warning — "
                        f"{len(result['issues'])} unsupported value(s)"
                    )

                    for issue in result["issues"]:
                        st.write(f"• {issue}")

                    grounding_warnings.extend(
                        f"{name}: {issue}"
                        for issue in result["issues"]
                    )

                with st.expander(f"{name} Grounding Details"):
                    st.json(result["checks"])

            if all_errors:
                st.warning(
                    "Verification stopped because extraction "
                    "issues require review."
                )

            elif grounding_warnings:
                st.warning(
                    "Verification stopped because source grounding "
                    "warnings require manual review. "
                    "Some warnings may be caused by OCR or formatting."
                )

            else:
                st.divider()
                st.subheader("Three-Way Verification Results")

                try:
                    verification_results = verify_documents(
                        po_data,
                        invoice_data,
                        grn_data
                    )

                except ValueError as error:
                    st.error(f"Document Verification Failed: {error}")
                    st.stop()
                invoice_number = invoice_data.get(
                    "document_number"
                )

                if check_duplicate_invoice(invoice_number):
                    st.warning(
                        f"Duplicate Invoice Warning: {invoice_number} "
                        "has already been verified and saved. "
                        "This verification will not be saved again."
                    )

                else:
                    verification_id = save_verification(
                        po_data,
                        invoice_data,
                        grn_data,
                        verification_results
                    )

                    st.success(
                        f"Verification #{verification_id} "
                        "saved to database!"
                    )

                total_items = len(verification_results)

                matched_items = sum(
                    1 for item in verification_results
                    if item["status"] == "Matched"
                )

                mismatched_items = total_items - matched_items

                total_invoice_value = sum(
                    item["invoice_value"] or 0
                    for item in verification_results
                )

                total_financial_difference = sum(
                    item["financial_difference"] or 0
                    for item in verification_results
                )

                st.subheader("Verification Summary")

                col1, col2, col3 = st.columns(3)

                col1.metric("Total Products", total_items)
                col2.metric("Matched", matched_items)
                col3.metric("Mismatched", mismatched_items)

                col4, col5 = st.columns(2)

                col4.metric(
                    "Total Invoice Value",
                    f"₹{total_invoice_value:,.2f}"
                )

                col5.metric(
                    "Net Financial Difference",
                    f"₹{total_financial_difference:,.2f}"
                )

                if mismatched_items == 0:
                    st.success("Verification Passed")
                else:
                    st.error(
                        "Verification Failed — Discrepancies Found"
                    )

                # ---------------------------------
                # VERIFICATION ANALYTICS DASHBOARD
                # ---------------------------------

                st.divider()
                st.subheader("📊 Verification Analytics Dashboard")

                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:
                    st.markdown(
                        "#### Product Verification Status"
                    )

                    if total_items > 0:
                        fig, ax = plt.subplots(
                            figsize=(5, 4)
                        )

                        ax.pie(
                            [matched_items, mismatched_items],
                            labels=["Matched", "Mismatched"],
                            autopct="%1.1f%%",
                            startangle=90,
                            colors=["#22c55e", "#ef4444"]
                        )

                        ax.axis("equal")

                        st.pyplot(fig)
                        plt.close(fig)

                    else:
                        st.info(
                            "No products available for charting."
                        )

                with chart_col2:
                    st.markdown(
                        "#### Financial Difference by Product"
                    )

                    chart_data = pd.DataFrame([
                        {
                            "Product": item["item_code"],
                            "Financial Difference": (
                                item["financial_difference"] or 0
                            )
                        }
                        for item in verification_results
                    ])

                    if not chart_data.empty:
                        st.bar_chart(
                            chart_data.set_index("Product"),
                            y="Financial Difference"
                        )
                    else:
                        st.info(
                            "No financial data available."
                        )

                # ---------------------------------
                # INDIVIDUAL VERIFICATION RESULTS
                # ---------------------------------

                st.divider()
                st.subheader("Product Verification Details")

                for item in verification_results:
                    if item["status"] == "Matched":
                        st.success(
                            f"{item['description']} "
                            f"({item['item_code']}): Matched"
                        )

                    else:
                        st.error(
                            f"{item['description']} "
                            f"({item['item_code']}): Mismatch"
                        )

                        for issue in item["issues"]:
                            st.write(f"• {issue}")

                st.divider()
                st.subheader("Financial Discrepancy Analysis")

                for item in verification_results:
                    with st.expander(
                        f"{item['description']} ({item['item_code']})"
                    ):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            invoice_value = item["invoice_value"]

                            st.metric(
                                "Invoice Value",
                                f"₹{invoice_value:,.2f}"
                                if invoice_value is not None
                                else "N/A"
                            )

                        with col2:
                            received_value = item[
                                "received_value_at_po_price"
                            ]

                            st.metric(
                                "Received Value at PO Price",
                                f"₹{received_value:,.2f}"
                                if received_value is not None
                                else "N/A"
                            )

                        with col3:
                            difference = item[
                                "financial_difference"
                            ]

                            st.metric(
                                "Financial Difference",
                                f"₹{difference:,.2f}"
                                if difference is not None
                                else "N/A"
                            )

                        st.write(
                            "Excess Billed Quantity:",
                            item["excess_billed_qty"]
                        )

                        excess_value = item[
                            "excess_billed_value"
                        ]

                        st.write(
                            "Excess Billed Value:",
                            f"₹{excess_value:,.2f}"
                            if excess_value is not None
                            else "N/A"
                        )

                st.caption(
                    "Financial differences are comparison metrics, "
                    "not final payable amounts. Taxes, discounts and "
                    "contractual adjustments are not yet included."
                )

                # ---------------------------------
                # DOWNLOAD REPORTS
                # ---------------------------------

                st.divider()
                st.subheader("📥 Download Verification Reports")

                pdf_report = generate_pdf_report(
                    po_data,
                    invoice_data,
                    grn_data,
                    verification_results
                )

                csv_report = generate_csv_report(
                    verification_results
                )

                json_report = generate_json_report(
                    po_data,
                    invoice_data,
                    grn_data,
                    verification_results
                )

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.download_button(
                        label="📄 Download PDF",
                        data=pdf_report,
                        file_name="documind_verification_report.pdf",
                        mime="application/pdf"
                    )

                with col2:
                    st.download_button(
                        label="📊 Download CSV",
                        data=csv_report,
                        file_name="documind_verification_report.csv",
                        mime="text/csv"
                    )

                with col3:
                    st.download_button(
                        label="📋 Download JSON",
                        data=json_report,
                        file_name="documind_verification_report.json",
                        mime="application/json"
                    )

        except Exception as error:
            st.error(f"Document processing failed: {error}")


# ---------------------------------
# VERIFICATION HISTORY
# ---------------------------------

st.divider()
st.subheader("📚 Verification History")

history = get_verification_history()

if history:
    for record in history:
        with st.expander(
            f"Verification #{record['id']} — "
            f"Invoice: {record['invoice_number']}"
        ):
            st.write("Date:", record["created_at"])
            st.write("PO Number:", record["po_number"])
            st.write("Invoice Number:", record["invoice_number"])
            st.write("GRN Number:", record["grn_number"])

            st.write("Total Products:", record["total_items"])
            st.write("Matched:", record["matched_items"])
            st.write("Mismatched:", record["mismatched_items"])

            st.metric(
                "Invoice Value",
                f"₹{record['total_invoice_value']:,.2f}"
            )

            st.metric(
                "Financial Difference",
                f"₹{record['financial_difference']:,.2f}"
            )

else:
    st.info("No previous verifications found.")
