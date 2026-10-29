# Data Dictionary 

## customers.csv
- `customer_id`: unique customer ID.
- `customer_name`: customer's name.
- `region`: must be north, south, east, west, or central.

## orders.csv
- `order_id`: unique order ID.
- `customer_id`: must match a known customer.
- `order_timestamp`: when the order was created.
- `amount`: order value; must be a number and cannot be negative.
- `status`: pending, paid, shipped, cancelled, or refunded.
- `updated_at`: when the order information was last updated.

## Database tables
- `customers`: accepted customer records.
- `orders`: latest accepted version of each order.
- `rejects`: bad rows and the reason they were rejected.
- `run_logs`: a short report for each run.
