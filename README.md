# Core-Bank — Terminal Banking System

A Python command-line application backed by SQLite, implementing a simple
banking system with account registration, login, deposits, withdrawals,
transfers, and mini statements.

---

## Files

| File            | Purpose                                      |
|-----------------|----------------------------------------------|
| `core_bank.py`  | Main application — run this                  |
| `seed_demo.py`  | Optional: loads two demo accounts            |
| `core_bank.db`  | SQLite database (auto-created on first run)  |

---

## Quick Start

```bash
# 1. Run the app (creates DB automatically)
python core_bank.py

# 2. (Optional) Load demo accounts first
python seed_demo.py
python core_bank.py
# Login: alice@corebank.io / Password1
# Login: bob@corebank.io   / Password2
```

No external packages required — only Python's standard library.

---

## Database Schema

```
Users
├── User_ID          INTEGER  PK AUTOINCREMENT
├── Name             TEXT     NOT NULL
├── Email            TEXT     NOT NULL UNIQUE
└── Hashed_Password  TEXT     NOT NULL

Accounts
├── Account_Number   TEXT     PK
├── User_ID          INTEGER  FK → Users(User_ID)
├── Account_Type     TEXT     CHECK IN ('Savings','Current')
└── Balance          REAL     DEFAULT 0  CHECK (Balance >= 0)

Transactions
├── Transaction_ID   INTEGER  PK AUTOINCREMENT
├── Sender_Account   TEXT     (NULL for cash deposits)
├── Receiver_Account TEXT     (NULL for cash withdrawals)
├── Amount           REAL     CHECK (Amount > 0)
└── Timestamp        TEXT
```

User personal data (name, email, password) is kept in its own table,
separate from financial data (account type, balance), and linked
through `User_ID`.

---

## Concepts Used

### Database Constraints
- `Balance >= 0` — enforced at the database level via `CHECK`.
- `Account_Type IN ('Savings','Current')` — enum-style validation.
- `Amount > 0` — ensures no zero-value transactions.
- `UNIQUE` on `Users.Email` — prevents duplicate accounts.
- `FOREIGN KEY` — links each account to its owning user.

### Basic Transaction Safety
Each write operation (deposit, withdraw, transfer) runs inside a
`try / except` block. If anything goes wrong partway through, the
change is rolled back with `conn.rollback()` so the database isn't
left in a half-updated state:

```python
try:
    conn.execute("UPDATE Accounts SET Balance = Balance - ? WHERE Account_Number = ?", ...)
    conn.execute("INSERT INTO Transactions (...) VALUES (...)", ...)
    conn.commit()
except Exception:
    conn.rollback()
```

For `transfer_funds()`, the sender is debited, the receiver is
credited, and one ledger entry is written before committing — so a
transfer either fully completes or is fully rolled back.

### Password Storage
Passwords are hashed with **SHA-256** before being stored — the plain
password is never saved to the database. `getpass` is used for
password input so the terminal doesn't echo characters while typing.

### Account Numbers
Each new account is assigned the next number in sequence
(`CBACC0001`, `CBACC0002`, ...) based on how many accounts already
exist.

---

## Feature Menu

```
[1]  View Balance       — SELECT with account lookup
[2]  Deposit            — UPDATE balance, INSERT transaction record
[3]  Withdraw           — Balance check, UPDATE, INSERT transaction record
[4]  Transfer Funds     — Debit + credit + ledger entry in one flow
[5]  Mini Statement     — Last 5 transactions, labelled DEBIT/CREDIT
[6]  Logout
```

---

## Security Notes

- Passwords are never stored in plain text — each is stored as a
  SHA-256 hash.
- `getpass` is used for password input — the terminal does not echo
  characters.

*Note: this hashing approach has no salt, so it's meant for
learning/demo purposes rather than production use.*

---

## Example Session

```
┌────────────────────────────────────────────────────────────┐
│              CORE-BANK  ▸  Welcome, Alice Sharma           │
└────────────────────────────────────────────────────────────┘

  Account : CBACC0001

  [1]  View Balance
  [2]  Deposit
  [3]  Withdraw
  [4]  Transfer Funds
  [5]  Mini Statement
  [6]  Logout

  Select option: 5

MINI STATEMENT  —  Last 5 Transactions
  Account No  : CBACC0001

  TXN ID   TYPE          AMOUNT  COUNTERPART        DATE/TIME
  ────────────────────────────────────────────────────────────────────
  6        DEBIT      -₹  1,500.00  CBACC0002          2025-06-06 09:00:00
  5        CREDIT     +₹  2,000.00  CBACC0002          2025-06-04 09:00:00
  4        DEBIT      -₹  5,000.00  CBACC0002          2025-06-02 09:00:00
  1        CREDIT     +₹ 50,000.00  BANK               2025-06-01 09:00:00
```
