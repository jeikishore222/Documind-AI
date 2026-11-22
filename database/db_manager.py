
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone


DB_PATH = Path(__file__).resolve().parent / "documind.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                po_number TEXT,
                invoice_number TEXT,
                grn_number TEXT,
                total_items INTEGER,
                matched_items INTEGER,
                mismatched_items INTEGER,
                total_invoice_value REAL,
                financial_difference REAL,
                results_json TEXT NOT NULL
            )
        """)


def save_verification(
    po_data,
    invoice_data,
    grn_data,
    verification_results
):
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

    financial_difference = sum(
        item["financial_difference"] or 0
        for item in verification_results
    )

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO verifications (
                created_at,
                po_number,
                invoice_number,
                grn_number,
                total_items,
                matched_items,
                mismatched_items,
                total_invoice_value,
                financial_difference,
                results_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            po_data.get("document_number"),
            invoice_data.get("document_number"),
            grn_data.get("document_number"),
            total_items,
            matched_items,
            mismatched_items,
            total_invoice_value,
            financial_difference,
            json.dumps(verification_results)
        ))

        return cursor.lastrowid


def get_verification_history():
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT *
            FROM verifications
            ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]

def check_duplicate_invoice(invoice_number):
    if not invoice_number:
        return False

    with get_connection() as conn:
        result = conn.execute(
            """
            SELECT id
            FROM verifications
            WHERE invoice_number = ?
            LIMIT 1
            """,
            (invoice_number,)
        ).fetchone()

        return result is not None
