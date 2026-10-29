import argparse
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

REGIONS = ["north", "south", "east", "west", "central"]
STATUSES = ["pending", "paid", "shipped", "cancelled", "refunded"]


def main():
    parser = argparse.ArgumentParser(description="Create sample customer and order files.")
    parser.add_argument("--orders", type=int, default=100)
    parser.add_argument("--clean", action="store_true", help="Do not add deliberately bad rows")
    args = parser.parse_args()
    random.seed(42)
    out = Path("data/generated")
    out.mkdir(parents=True, exist_ok=True)
    customer_count = max(10, args.orders // 5)
    customers = [{"customer_id": f"C{i:06d}", "customer_name": f"Customer {i}",
                  "region": REGIONS[(i - 1) % len(REGIONS)]}
                 for i in range(1, customer_count + 1)]
    with (out / "customers.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["customer_id", "customer_name", "region"])
        writer.writeheader()
        writer.writerows(customers)

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    orders = []
    for i in range(1, args.orders + 1):
        order_time = base + timedelta(minutes=random.randint(0, 129600))
        update_time = order_time + timedelta(minutes=random.randint(0, 1000))
        orders.append({"order_id": f"O{i:08d}",
                       "customer_id": random.choice(customers)["customer_id"],
                       "order_timestamp": order_time.isoformat(timespec="seconds"),
                       "amount": f"{random.uniform(1, 5000):.2f}",
                       "status": random.choice(STATUSES),
                       "updated_at": update_time.isoformat(timespec="seconds")})
    if not args.clean and args.orders >= 5:
        orders[0]["amount"] = "-5.00"
        orders[1]["customer_id"] = "C999999"
        orders[2]["status"] = "flying"
        orders[3]["order_id"] = orders[2]["order_id"]
        orders[4]["amount"] = "not-a-number"
    with (out / "orders.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["order_id", "customer_id", "order_timestamp",
                                                   "amount", "status", "updated_at"])
        writer.writeheader()
        writer.writerows(orders)
    print("\nDATA FILES CREATED")
    print("_" * 38)
    print(f"Customers created : {len(customers)}")
    print(f"Orders created    : {len(orders)}")
    print(f"Invalid examples  : {'No' if args.clean else 'Yes, if at least 5 orders'}")
    print(f"Output folder     : {out}")
    print("_" * 38)


if __name__ == "__main__":
    main()
