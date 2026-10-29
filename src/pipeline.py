import argparse
import csv
import sqlite3
import time
from datetime import datetime
from pathlib import Path

# 1. Rules: these are the columns and values allowed.
CUSTOMER_COLUMNS = ["customer_id", "customer_name", "region"]
ORDER_COLUMNS = ["order_id", "customer_id", "order_timestamp", "amount", "status", "updated_at"]
ALLOWED_REGIONS = {"north", "south", "east", "west", "central"}
ALLOWED_STATUSES = {"pending", "paid", "shipped", "cancelled", "refunded"}


def read_csv(file_path):
    """Read a CSV file and return (column names, rows)."""
    with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames or [], list(reader)


def check_columns(expected, actual):
    """Return whether required columns exist, plus missing and extra columns."""
    missing = [name for name in expected if name not in actual]
    extra = [name for name in actual if name not in expected]
    return len(missing) == 0, missing, extra


def validate_customer(row):
    """Return a list of problems; an empty list means the customer is valid."""
    problems = []
    if not row.get("customer_id", "").strip():
        problems.append("customer_id is missing")
    if not row.get("customer_name", "").strip():
        problems.append("customer_name is missing")
    if row.get("region", "").strip().lower() not in ALLOWED_REGIONS:
        problems.append("region is not allowed")
    return problems


def validate_order(row, known_customer_ids):
    """Return a list of problems found in one order."""
    problems = []
    if not row.get("order_id", "").strip():
        problems.append("order_id is missing")
    if row.get("customer_id", "").strip() not in known_customer_ids:
        problems.append("customer_id does not exist")

    try:
        if float(row.get("amount", "")) < 0:
            problems.append("amount cannot be negative")
    except (ValueError, TypeError):
        problems.append("amount must be a number")

    if row.get("status", "").strip().lower() not in ALLOWED_STATUSES:
        problems.append("status is not allowed")

    try:
        order_time = datetime.fromisoformat(row["order_timestamp"].replace("Z", "+00:00"))
        update_time = datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
        if update_time < order_time:
            problems.append("updated_at cannot be before order_timestamp")
    except (ValueError, KeyError, TypeError):
        problems.append("timestamp is missing or invalid")
    return problems


def create_database(db):
    """Create the four small tables used by the project."""
    db.execute("""CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY, customer_name TEXT NOT NULL, region TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, order_timestamp TEXT NOT NULL,
        amount REAL NOT NULL CHECK(amount >= 0), status TEXT NOT NULL, updated_at TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS rejects (
        id INTEGER PRIMARY KEY AUTOINCREMENT, file_name TEXT NOT NULL,
        row_number INTEGER NOT NULL, record_id TEXT, reason TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS run_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT NOT NULL, status TEXT NOT NULL,
        customers_read INTEGER NOT NULL, orders_read INTEGER NOT NULL,
        accepted_orders INTEGER NOT NULL, rejected_rows INTEGER NOT NULL,
        duration_seconds REAL NOT NULL)""")
    db.commit()


def save_reject(db, file_name, row_number, record_id, problems):
    """Keep a rejected row's file, line number, ID, and reason."""
    db.execute(
        "INSERT INTO rejects(file_name, row_number, record_id, reason) VALUES (?, ?, ?, ?)",
        (file_name, row_number, record_id, "; ".join(problems)),
    )


def run_pipeline(customers_file, orders_file, database_file):
    """Runs the full process and prints an easy-to-read report."""
    start_clock = time.perf_counter()
    started_at = datetime.now().isoformat(timespec="seconds")
    customers_file, orders_file, database_file = map(Path, (customers_file, orders_file, database_file))
    database_file.parent.mkdir(parents=True, exist_ok=True)

    customer_columns, customers = read_csv(customers_file)
    order_columns, orders = read_csv(orders_file)
    customers_ok, missing_customers, extra_customers = check_columns(CUSTOMER_COLUMNS, customer_columns)
    orders_ok, missing_orders, extra_orders = check_columns(ORDER_COLUMNS, order_columns)

    print("\n" + "=" * 54)
    print("       DATA CONTRACT VALIDATOR - RUN REPORT")
    print("=" * 54)
    print(f"Customer file : {customers_file}")
    print(f"Order file    : {orders_file}")
    print("_" * 54)
    for label, okay, missing, extra in [
        ("Customers", customers_ok, missing_customers, extra_customers),
        ("Orders", orders_ok, missing_orders, extra_orders),
    ]:
        print(f"{label} columns : {'OK' if okay else 'FAILED'}")
        if missing:
            print(f"  Missing       : {', '.join(missing)}")
        if extra:
            print(f"  Extra         : {', '.join(extra)} (allowed)")

    if not customers_ok or not orders_ok:
        print("_" * 54)
        print("FINAL STATUS : STOPPED - REQUIRED COLUMN MISSING")
        print("Fix the column headings and run again.")
        print("=" * 54 + "\n")
        return {"status": "schema_error", "accepted_orders": 0, "rejected_rows": 0}

    rejected = accepted_customers = accepted_orders = 0
    seen_customers, seen_orders = set(), set()

    with sqlite3.connect(database_file) as db:
        db.execute("PRAGMA foreign_keys = ON")
        create_database(db)

        # Save valid customers first. Orders refer to these customer IDs.
        for line, row in enumerate(customers, start=2):
            key = row.get("customer_id", "").strip()
            problems = validate_customer(row)
            if key in seen_customers:
                problems.append("duplicate customer_id in this file")
            seen_customers.add(key)
            if problems:
                save_reject(db, customers_file.name, line, key, problems)
                rejected += 1
                continue
            db.execute("""INSERT INTO customers VALUES (?, ?, ?)
                ON CONFLICT(customer_id) DO UPDATE SET
                customer_name=excluded.customer_name, region=excluded.region""",
                (key, row["customer_name"].strip(), row["region"].strip().lower()))
            accepted_customers += 1

        known_customers = {r[0] for r in db.execute("SELECT customer_id FROM customers")}

        # Check orders, save valid rows, and record invalid rows separately.
        for line, row in enumerate(orders, start=2):
            key = row.get("order_id", "").strip()
            problems = validate_order(row, known_customers)
            if key in seen_orders:
                problems.append("duplicate order_id in this file")
            seen_orders.add(key)
            if problems:
                save_reject(db, orders_file.name, line, key, problems)
                rejected += 1
                continue

            order_time = datetime.fromisoformat(row["order_timestamp"].replace("Z", "+00:00")).isoformat(timespec="seconds")
            update_time = datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")).isoformat(timespec="seconds")
            amount = round(float(row["amount"]), 2)
            old = db.execute("SELECT updated_at FROM orders WHERE order_id = ?", (key,)).fetchone()
            if old and old[0] > update_time:
                continue  # Ignore an older version of an order.
            db.execute("""INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                customer_id=excluded.customer_id, order_timestamp=excluded.order_timestamp,
                amount=excluded.amount, status=excluded.status, updated_at=excluded.updated_at
                WHERE excluded.updated_at >= orders.updated_at""",
                (key, row["customer_id"].strip(), order_time, amount,
                 row["status"].strip().lower(), update_time))
            accepted_orders += 1

        db.commit()
        duration = time.perf_counter() - start_clock
        status = "COMPLETED" if rejected == 0 else "COMPLETED WITH REJECTS"
        db.execute("""INSERT INTO run_logs
            (started_at, status, customers_read, orders_read, accepted_orders, rejected_rows, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (started_at, status, len(customers), len(orders), accepted_orders, rejected, round(duration, 3)))
        db.commit()
        customer_total = db.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        order_total = db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        reject_total = db.execute("SELECT COUNT(*) FROM rejects").fetchone()[0]

    print("_" * 54)
    print("PROCESSING SUMMARY")
    print("_" * 54)
    print(f"Customer rows read      : {len(customers)}")
    print(f"Customer rows accepted  : {accepted_customers}")
    print(f"Order rows read         : {len(orders)}")
    print(f"Orders accepted/updated : {accepted_orders}")
    print(f"Rows rejected           : {rejected}")
    print(f"Customers now in DB     : {customer_total}")
    print(f"Orders now in DB        : {order_total}")
    print(f"Rejects saved in DB     : {reject_total}")
    print(f"Time taken              : {duration:.3f} seconds")
    print(f"Database location       : {database_file}")
    print("_" * 54)
    print(f"FINAL STATUS            : {status}")
    print("=" * 54 + "\n")
    return {"status": status, "accepted_orders": accepted_orders, "rejected_rows": rejected,
            "duration_seconds": round(duration, 3)}


def main():
    parser = argparse.ArgumentParser(description="Check customer and order CSV files.")
    parser.add_argument("--customers", default="data/input/customers.csv")
    parser.add_argument("--orders", default="data/input/orders.csv")
    parser.add_argument("--db", default="data/output/pipeline.db")
    args = parser.parse_args()
    run_pipeline(args.customers, args.orders, args.db)


if __name__ == "__main__":
    main()
