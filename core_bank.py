"""
Core-Bank: Terminal-Based Banking System
A simple Python CLI application with an SQLite backend.
Supports registration, login, deposit, withdrawal, transfer, and mini statements.
"""

import sqlite3
import hashlib
import getpass
import os
import sys
from datetime import datetime

# ─────────────────────────────────────────────
#  DATABASE SETUP
# ─────────────────────────────────────────────

DB_FILE = "core_bank.db"


def get_connection():
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def initialise_db():
    """Create the Users, Accounts, and Transactions tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    # ── Users ──────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            User_ID         INTEGER PRIMARY KEY AUTOINCREMENT,
            Name            TEXT    NOT NULL,
            Email           TEXT    NOT NULL UNIQUE,
            Hashed_Password TEXT    NOT NULL
        )
    """)

    # ── Accounts ───────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Accounts (
            Account_Number  TEXT    PRIMARY KEY,
            User_ID         INTEGER NOT NULL,
            Account_Type    TEXT    NOT NULL CHECK (Account_Type IN ('Savings','Current')),
            Balance         REAL    NOT NULL DEFAULT 0.00
                                    CHECK (Balance >= 0),
            FOREIGN KEY (User_ID) REFERENCES Users(User_ID)
        )
    """)

    # ── Transactions ───────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Transactions (
            Transaction_ID   INTEGER PRIMARY KEY AUTOINCREMENT,
            Sender_Account   TEXT,
            Receiver_Account TEXT,
            Amount           REAL    NOT NULL CHECK (Amount > 0),
            Timestamp        TEXT    NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  AUTHENTICATION HELPERS
# ─────────────────────────────────────────────

def hash_password(password):
    """Return a simple SHA-256 hash of the password."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, stored_hash):
    """Check a typed password against the stored hash."""
    return hash_password(password) == stored_hash


def generate_account_number(conn):
    """Generate the next account number in sequence, e.g. CBACC0001, CBACC0002 ..."""
    count = conn.execute("SELECT COUNT(*) AS total FROM Accounts").fetchone()["total"]
    next_number = count + 1
    return f"CBACC{next_number:04d}"


# ─────────────────────────────────────────────
#  USER & ACCOUNT MANAGEMENT
# ─────────────────────────────────────────────

def register_user():
    """Register a new user and open an account."""
    clear()
    banner("NEW USER REGISTRATION")

    name = input("  Full Name  : ").strip()
    email = input("  Email      : ").strip().lower()

    conn = get_connection()
    existing = conn.execute("SELECT User_ID FROM Users WHERE Email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        error("An account with this email already exists.")
        pause()
        return

    password = getpass.getpass("  Password   : ")
    confirm = getpass.getpass("  Confirm    : ")
    if password != confirm:
        conn.close()
        error("Passwords do not match.")
        pause()
        return

    acc_type = choose_account_type()
    opening = float(input("  Opening Deposit (₹): ") or "0")
    if opening < 0:
        conn.close()
        error("Opening deposit cannot be negative.")
        pause()
        return

    hashed = hash_password(password)
    acc_num = generate_account_number(conn)
    now = datetime.now().isoformat(sep=" ", timespec="seconds")

    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Users (Name, Email, Hashed_Password) VALUES (?,?,?)",
            (name, email, hashed)
        )
        user_id = cur.lastrowid
        cur.execute(
            "INSERT INTO Accounts (Account_Number, User_ID, Account_Type, Balance) VALUES (?,?,?,?)",
            (acc_num, user_id, acc_type, opening)
        )
        if opening > 0:
            cur.execute(
                "INSERT INTO Transactions (Sender_Account, Receiver_Account, Amount, Timestamp) VALUES (?,?,?,?)",
                (None, acc_num, opening, now)
            )
        conn.commit()
        success(f"Account created!  Account No: {acc_num}")
    except sqlite3.IntegrityError as e:
        conn.rollback()
        error(f"Registration failed: {e}")
    finally:
        conn.close()

    pause()


def login():
    """Authenticate user. Returns (user_id, name, account_number) or None."""
    clear()
    banner("USER LOGIN")

    email = input("  Email   : ").strip().lower()
    password = getpass.getpass("  Password: ")

    conn = get_connection()
    user = conn.execute(
        "SELECT User_ID, Name, Hashed_Password FROM Users WHERE Email = ?", (email,)
    ).fetchone()

    if not user or not verify_password(password, user["Hashed_Password"]):
        conn.close()
        error("Invalid email or password.")
        pause()
        return None

    account = conn.execute(
        "SELECT Account_Number FROM Accounts WHERE User_ID = ?", (user["User_ID"],)
    ).fetchone()
    conn.close()

    if not account:
        error("No account found for this user.")
        pause()
        return None

    success(f"Welcome back, {user['Name']}!")
    pause()
    return user["User_ID"], user["Name"], account["Account_Number"]


# ─────────────────────────────────────────────
#  BANKING OPERATIONS
# ─────────────────────────────────────────────

def view_balance(acc_num):
    clear()
    banner("ACCOUNT BALANCE")
    conn = get_connection()
    row = conn.execute(
        "SELECT Account_Number, Account_Type, Balance FROM Accounts WHERE Account_Number = ?",
        (acc_num,)
    ).fetchone()
    conn.close()

    if row:
        print(f"\n  Account No  : {row['Account_Number']}")
        print(f"  Type        : {row['Account_Type']}")
        print(f"  Balance     : ₹ {row['Balance']:,.2f}")
    else:
        error("Account not found.")
    pause()


def deposit(acc_num):
    clear()
    banner("DEPOSIT FUNDS")
    print(f"  Account No  : {acc_num}\n")

    try:
        amount = float(input("  Amount (₹) : "))
    except ValueError:
        error("Invalid amount.")
        pause()
        return

    if amount <= 0:
        error("Deposit amount must be positive.")
        pause()
        return

    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE Accounts SET Balance = Balance + ? WHERE Account_Number = ?",
            (amount, acc_num)
        )
        conn.execute(
            "INSERT INTO Transactions (Sender_Account, Receiver_Account, Amount, Timestamp) VALUES (?,?,?,?)",
            (None, acc_num, amount, now)
        )
        conn.commit()
        success(f"₹ {amount:,.2f} deposited successfully.")
    except Exception as e:
        conn.rollback()
        error(f"Deposit failed: {e}")
    finally:
        conn.close()
    pause()


def withdraw(acc_num):
    clear()
    banner("WITHDRAW FUNDS")
    print(f"  Account No  : {acc_num}\n")

    try:
        amount = float(input("  Amount (₹) : "))
    except ValueError:
        error("Invalid amount.")
        pause()
        return

    if amount <= 0:
        error("Withdrawal amount must be positive.")
        pause()
        return

    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT Balance FROM Accounts WHERE Account_Number = ?", (acc_num,)
        ).fetchone()

        if not row or row["Balance"] < amount:
            error("Insufficient balance.")
            conn.close()
            pause()
            return

        conn.execute(
            "UPDATE Accounts SET Balance = Balance - ? WHERE Account_Number = ?",
            (amount, acc_num)
        )
        conn.execute(
            "INSERT INTO Transactions (Sender_Account, Receiver_Account, Amount, Timestamp) VALUES (?,?,?,?)",
            (acc_num, None, amount, now)
        )
        conn.commit()
        success(f"₹ {amount:,.2f} withdrawn successfully.")
    except sqlite3.IntegrityError:
        conn.rollback()
        error("Transaction violates balance constraint (balance cannot go below ₹0).")
    except Exception as e:
        conn.rollback()
        error(f"Withdrawal failed: {e}")
    finally:
        conn.close()
    pause()


def transfer_funds(sender_acc):
    """Transfer money from the logged-in account to another account."""
    clear()
    banner("TRANSFER FUNDS")
    print(f"  From Account: {sender_acc}\n")

    receiver_acc = input("  To Account No : ").strip().upper()
    if receiver_acc == sender_acc:
        error("Cannot transfer to your own account.")
        pause()
        return

    try:
        amount = float(input("  Amount (₹)    : "))
    except ValueError:
        error("Invalid amount.")
        pause()
        return

    if amount <= 0:
        error("Transfer amount must be positive.")
        pause()
        return

    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    conn = get_connection()
    try:
        # Verify receiver exists
        recv = conn.execute(
            "SELECT Account_Number FROM Accounts WHERE Account_Number = ?", (receiver_acc,)
        ).fetchone()
        if not recv:
            error(f"Receiver account '{receiver_acc}' not found.")
            conn.close()
            pause()
            return

        # Verify sender balance
        sender = conn.execute(
            "SELECT Balance FROM Accounts WHERE Account_Number = ?", (sender_acc,)
        ).fetchone()
        if not sender or sender["Balance"] < amount:
            error("Insufficient balance for transfer.")
            conn.close()
            pause()
            return

        # Debit sender, credit receiver, log the transaction
        conn.execute(
            "UPDATE Accounts SET Balance = Balance - ? WHERE Account_Number = ?",
            (amount, sender_acc)
        )
        conn.execute(
            "UPDATE Accounts SET Balance = Balance + ? WHERE Account_Number = ?",
            (amount, receiver_acc)
        )
        conn.execute(
            "INSERT INTO Transactions (Sender_Account, Receiver_Account, Amount, Timestamp) VALUES (?,?,?,?)",
            (sender_acc, receiver_acc, amount, now)
        )
        conn.commit()
        success(f"₹ {amount:,.2f} transferred to {receiver_acc}.")
    except sqlite3.IntegrityError:
        conn.rollback()
        error("Transfer violates a database constraint. Rolled back.")
    except Exception as e:
        conn.rollback()
        error(f"Transfer failed and was rolled back: {e}")
    finally:
        conn.close()
    pause()


def mini_statement(acc_num):
    """Show the last 5 transactions for this account."""
    clear()
    banner("MINI STATEMENT  —  Last 5 Transactions")
    print(f"  Account No  : {acc_num}\n")

    conn = get_connection()
    rows = conn.execute("""
        SELECT Transaction_ID, Sender_Account, Receiver_Account, Amount, Timestamp
        FROM Transactions
        WHERE Sender_Account = ? OR Receiver_Account = ?
        ORDER BY Transaction_ID DESC
        LIMIT 5
    """, (acc_num, acc_num)).fetchall()
    conn.close()

    if not rows:
        print("  No transactions found.")
    else:
        print(f"  {'TXN ID':<8} {'TYPE':<8} {'AMOUNT':>12}  {'COUNTERPART':<18} {'DATE/TIME'}")
        print("  " + "─" * 68)
        for r in rows:
            # Work out whether this was money going out (DEBIT) or coming in (CREDIT)
            if r["Sender_Account"] == acc_num:
                direction = "DEBIT"
                counterpart = r["Receiver_Account"] or "BANK"
                sign = "-"
            else:
                direction = "CREDIT"
                counterpart = r["Sender_Account"] or "BANK"
                sign = "+"

            print(
                f"  {r['Transaction_ID']:<8} {direction:<8} "
                f"{sign}₹{r['Amount']:>10,.2f}  {counterpart:<18} {r['Timestamp']}"
            )

    pause()


# ─────────────────────────────────────────────
#  TERMINAL UI HELPERS
# ─────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def banner(title):
    width = 60
    print("┌" + "─" * width + "┐")
    print("│" + f"  CORE-BANK  ▸  {title}".center(width) + "│")
    print("└" + "─" * width + "┘")
    print()


def success(msg):
    print(f"\n  ✔  {msg}")


def error(msg):
    print(f"\n  ✘  ERROR: {msg}")


def pause():
    input("\n  Press ENTER to continue...")


def choose_account_type():
    print("\n  Account Type:")
    print("    [1] Savings")
    print("    [2] Current")
    choice = input("  Select (1/2): ").strip()
    return "Current" if choice == "2" else "Savings"


# ─────────────────────────────────────────────
#  MAIN MENU (authenticated)
# ─────────────────────────────────────────────

def banking_menu(user_id, name, acc_num):
    while True:
        clear()
        banner(f"Welcome, {name}")
        print(f"  Account : {acc_num}\n")
        print("  [1]  View Balance")
        print("  [2]  Deposit")
        print("  [3]  Withdraw")
        print("  [4]  Transfer Funds")
        print("  [5]  Mini Statement")
        print("  [6]  Logout")
        print()

        choice = input("  Select option: ").strip()

        if choice == "1":
            view_balance(acc_num)
        elif choice == "2":
            deposit(acc_num)
        elif choice == "3":
            withdraw(acc_num)
        elif choice == "4":
            transfer_funds(acc_num)
        elif choice == "5":
            mini_statement(acc_num)
        elif choice == "6":
            clear()
            print("\n  Goodbye! Have a great day.\n")
            break
        else:
            error("Invalid option. Please choose 1–6.")
            pause()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    initialise_db()

    while True:
        clear()
        print("""
  ╔══════════════════════════════════════════════════╗
  ║                                                  ║
  ║          C O R E - B A N K   v1.0               ║
  ║       Secure Terminal Banking System             ║
  ║                                                  ║
  ╚══════════════════════════════════════════════════╝

    [1]  Login
    [2]  Register New Account
    [3]  Exit
        """)

        choice = input("  Select option: ").strip()

        if choice == "1":
            session = login()
            if session:
                banking_menu(*session)

        elif choice == "2":
            register_user()

        elif choice == "3":
            clear()
            print("\n  Thank you for using Core-Bank. Goodbye!\n")
            sys.exit(0)

        else:
            error("Invalid option.")
            pause()


if __name__ == "__main__":
    main()
