import csv
import sqlite3
from src.pipeline import run_pipeline


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_bad_order_is_rejected_and_good_order_saved(tmp_path):
    customers = tmp_path / "customers.csv"
    orders = tmp_path / "orders.csv"
    database = tmp_path / "test.db"
    write_csv(customers, ["customer_id", "customer_name", "region"], [
        {"customer_id": "C1", "customer_name": "Asha", "region": "south"}])
    columns = ["order_id", "customer_id", "order_timestamp", "amount", "status", "updated_at"]
    write_csv(orders, columns, [
        {"order_id": "O1", "customer_id": "C1", "order_timestamp": "2026-01-01T10:00:00+00:00",
         "amount": "10", "status": "paid", "updated_at": "2026-01-01T10:05:00+00:00"},
        {"order_id": "O2", "customer_id": "C1", "order_timestamp": "2026-01-01T10:00:00+00:00",
         "amount": "-1", "status": "paid", "updated_at": "2026-01-01T10:05:00+00:00"}])
    result = run_pipeline(customers, orders, database)
    assert result["status"] == "COMPLETED WITH REJECTS"
    assert result["accepted_orders"] == 1
    assert result["rejected_rows"] == 1
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM rejects").fetchone()[0] == 1


def test_missing_required_column_stops_pipeline(tmp_path):
    customers = tmp_path / "customers.csv"
    orders = tmp_path / "orders.csv"
    write_csv(customers, ["customer_id", "customer_name"], [])
    write_csv(orders, ["order_id", "customer_id", "amount"], [])
    result = run_pipeline(customers, orders, tmp_path / "test.db")
    assert result["status"] == "schema_error"


def test_running_same_file_twice_does_not_duplicate_order(tmp_path):
    customers = tmp_path / "customers.csv"
    orders = tmp_path / "orders.csv"
    database = tmp_path / "test.db"
    write_csv(customers, ["customer_id", "customer_name", "region"], [
        {"customer_id": "C1", "customer_name": "Asha", "region": "south"}])
    write_csv(orders, ["order_id", "customer_id", "order_timestamp", "amount", "status", "updated_at"], [
        {"order_id": "O1", "customer_id": "C1", "order_timestamp": "2026-01-01T10:00:00+00:00",
         "amount": "10", "status": "paid", "updated_at": "2026-01-01T10:05:00+00:00"}])
    run_pipeline(customers, orders, database)
    run_pipeline(customers, orders, database)
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1
