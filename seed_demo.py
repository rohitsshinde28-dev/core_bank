"""
seed_demo.py  —  Populate Core-Bank with demo data for testing.
Run ONCE before launching core_bank.py to get pre-loaded accounts.

Demo Accounts:
  alice@corebank.io   / Password1
  bob@corebank.io     / Password2
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta

DB_FILE = "core_bank.db"


def hash_password(password):
    """Return a simple SHA-256 hash of the password (matches core_bank.py)."""
    return hashlib.sha256(password.encode()).hexdigest()


def seed():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # ── Users ──
    users = [
        ("Alice Sharma", "alice@corebank.io", hash_password("Password1")),
        ("Bob Mehta", "bob@corebank.io", hash_password("Password2")),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO Users (Name, Email, Hashed_Password) VALUES (?,?,?)", users
    )

    alice_id = cur.execute("SELECT User_ID FROM Users WHERE Email='alice@corebank.io'").fetchone()[0]
    bob_id = cur.execute("SELECT User_ID FROM Users WHERE Email='bob@corebank.io'").fetchone()[0]

    # ── Accounts ──
    accounts = [
        ("CBACC0001", alice_id, "Savings", 50000.00),
        ("CBACC0002", bob_id, "Current", 12500.00),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO Accounts (Account_Number, User_ID, Account_Type, Balance) VALUES (?,?,?,?)",
        accounts
    )

    # ── Sample Transactions ──
    base = datetime(2025, 6, 1, 9, 0, 0)
    txns = [
        (None, "CBACC0001", 50000.00, base),
        (None, "CBACC0002", 20000.00, base + timedelta(hours=1)),
        ("CBACC0001", "CBACC0002", 5000.00, base + timedelta(days=1)),
        ("CBACC0002", "CBACC0001", 2000.00, base + timedelta(days=3)),
        ("CBACC0001", "CBACC0002", 1500.00, base + timedelta(days=5)),
        ("CBACC0002", None, 5000.00, base + timedelta(days=7)),
    ]
    for t in txns:
        ts = t[3].isoformat(sep=" ", timespec="seconds")
        cur.execute(
            "INSERT OR IGNORE INTO Transactions (Sender_Account, Receiver_Account, Amount, Timestamp) VALUES (?,?,?,?)",
            (t[0], t[1], t[2], ts)
        )

    conn.commit()
    conn.close()
    print("\n✔  Demo data seeded successfully!\n")
    print("  alice@corebank.io  /  Password1  →  Account: CBACC0001")
    print("  bob@corebank.io    /  Password2  →  Account: CBACC0002\n")


if __name__ == "__main__":
    seed()
