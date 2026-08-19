"""
SQLite storage for triaged tickets.

Keeps it simple: one table, one file, automatic creation on first run.
No ORM, no migrations — just pure SQL that anyone can read.
"""

import sqlite3
import csv
from datetime import datetime
from pathlib import Path

DB_FILE = "triage.db"


def init_db():
    """
    Create the database and tickets table if they don't exist.
    Safe to call multiple times.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            email TEXT,
            raw_text TEXT NOT NULL,
            category TEXT,
            priority TEXT,
            summary TEXT,
            outcome TEXT NOT NULL,
            attempts INTEGER NOT NULL,
            last_error TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def save(record: dict) -> int:
    """
    Save a triaged ticket to the database.

    Args:
        record: A dict with:
            - email: (optional) Email of the person who submitted the ticket
            - raw_text: The original ticket message
            - category: (optional) The extracted category or None
            - priority: (optional) The extracted priority or None
            - summary: (optional) The extracted summary or None
            - outcome: "saved" or "needs_review"
            - attempts: How many attempts were made
            - last_error: (optional) The final validation error or empty string

    Returns:
        The inserted row's ID.
    """
    init_db()  # Ensure table exists.

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO tickets
        (created_at, email, raw_text, category, priority, summary, outcome, attempts, last_error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(),
            record.get("email", ""),
            record.get("raw_text", ""),
            record.get("category"),
            record.get("priority"),
            record.get("summary"),
            record.get("outcome", ""),
            record.get("attempts", 0),
            record.get("last_error", ""),
        ),
    )

    row_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return row_id


def list_recent(limit: int = 50) -> list[dict]:
    """
    Fetch the most recent triaged tickets.

    Args:
        limit: How many rows to return (default 50).

    Returns:
        A list of dicts, one per row, with keys:
        id, created_at, raw_text, category, priority, summary, outcome, attempts, last_error
    """
    init_db()

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Return rows as dicts.
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM tickets
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return rows


def export_csv() -> str:
    """
    Export all tickets to a CSV file.

    Returns:
        The path to the exported CSV file.
    """
    init_db()

    rows = list_recent(limit=99999)  # Get all rows.
    csv_path = Path("tickets_export.csv")

    if rows:
        # Write to CSV.
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    return str(csv_path)


def get_db_stats() -> dict:
    """
    Fetch basic statistics about the database.

    Returns:
        A dict with:
        - total_tickets: Total rows in the table
        - saved: Count where outcome="saved"
        - needs_review: Count where outcome="needs_review"
    """
    init_db()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tickets")
    total = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM tickets WHERE outcome = "saved"')
    saved = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM tickets WHERE outcome = "needs_review"')
    needs_review = cursor.fetchone()[0]

    conn.close()

    return {
        "total_tickets": total,
        "saved": saved,
        "needs_review": needs_review,
    }


def delete_ticket(ticket_id: int) -> bool:
    """
    Delete a single ticket by ID.

    Args:
        ticket_id: The ID of the ticket to delete

    Returns:
        True if deleted, False if not found
    """
    init_db()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted
