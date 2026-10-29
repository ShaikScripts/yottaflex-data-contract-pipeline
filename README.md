# Data Contract Validator & Reliable Pipeline

A beginner-friendly Python project that checks customer and order data before saving it to a database. It demonstrates data validation, handling incorrect records, saving results, and testing a simple data pipeline.

## 1. What problem does it solve?

Imagine an online shop receives a CSV file containing thousands of orders. Some rows might have a negative price, an invalid order status, a customer ID that does not exist, or a broken date.

If the shop saves all those rows without checking them, its reports may be wrong. This project checks the data first:

- **Valid records** are saved to SQLite tables.
- **Invalid records** are saved in a `rejects` table along with a reason.

## 2. What are the main tools?

- **Python** runs the pipeline and checks each record.
- **CSV files** hold the input data in rows and columns.
- **SQLite** is a small database stored in a single `.db` file on your computer. It does not require a separate database server.
- **pytest** runs automatic checks to help confirm that the program behaves as expected.
- **VS Code SQLite extension** lets you view the database tables inside VS Code.

## 3. How the project works

customers.csv and orders.csv
            |
            v
 Check required column names
            |
            v
   Validate each data row
         /       \
        v         v
  Valid rows   Invalid rows
        |         |
        v         v
 SQLite tables  rejects table
         \       /
          v     v
    Summary in terminal

## 4. Project folder guide

- `src/pipeline.py` — main program: reads CSV files, validates rows, saves results, and prints a summary.
- `src/generate_data.py` — creates larger example CSV files for a scale demonstration.
- `data/input/` — small sample CSV files used by default.
- `data/generated/` — larger CSV files created when you run the generator.
- `data/output/` — SQLite `.db` files created by the pipeline.
- `tests/test_pipeline.py` — automatic tests for important behavior.
- `docs/data_dictionary.md` — explains the input columns.
- `requirements.txt` — lists the Python testing dependency.

## 5. Set up the project in VS Code (Windows)

Run the commands below in the terminal of VScode, from the project folder.

### Create and activate a virtual environment

```powershell
py -m venv .venv
```

Then activate it in the VS Code PowerShell terminal:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Install the required Python package

```powershell
python -m pip install -r requirements.txt
```

## Run the project

In the VS Code terminal, run:

```powershell
python -m src.pipeline
```
It shows how many rows were read, accepted, and rejected, plus where the database was saved.

The sample deliberately includes incorrect rows, so the final status may say `COMPLETED WITH REJECTS`. This means the pipeline completed and identified invalid records; it does not mean the program crashed.

### Install a SQLite extension

1. Install a SQLite extension.
2. After running the pipeline, open the Explorer panel and expand `data` → `output`.
3. Find the `.db` file printed in the terminal.
4. Use the extension's database/open command to open that file. 
5. Expand the database or its tables, then select a table to inspect its rows.

### What is stored in the database?

- `customers` — valid customer records.
- `orders` — accepted order records.
- `rejects` — invalid rows and the reasons they were rejected.
- `run_logs` — a summary of pipeline runs.

## 6. Run the automatic tests

```powershell
python -m pytest -q
```

The tests check examples of invalid data, missing required columns, and duplicate order handling. A successful run displays a summary such as `3 passed`. 

## 7. test with 1,00,000 orders

First generate the larger input files:

```powershell
python -m src.generate_data --orders 100000
```

Then process them into a separate database:

```powershell
python -m src.pipeline --customers data/generated/customers.csv --orders data/generated/orders.csv --db data/output/large_test.db
```

This creates files under `data/generated/` and a database at `data/output/large_test.db`.


