"""
Loads orders.csv into a real SQLite database and executes every query in
sql_queries/*.sql against it, saving results as Markdown tables in
sql_queries/results/. This makes the SQL genuinely runnable and verifiable,
not just illustrative.

Run:
    python3 run_sql.py
"""
import csv
import glob
import os
import sqlite3

DB_PATH = "orders.db"
CSV_PATH = "orders.csv"
RESULTS_DIR = "sql_queries/results"


def load_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE orders (
            order_id INTEGER, order_date TEXT, year_month TEXT, customer_id INTEGER,
            is_new_customer INTEGER, months_since_acquisition INTEGER, sub_category TEXT,
            brand_tier TEXT, list_price INTEGER, discount_pct REAL, final_price INTEGER,
            units INTEGER, revenue INTEGER, marketing_channel TEXT, city_tier TEXT, returned INTEGER
        )
    """)
    with open(CSV_PATH) as f:
        reader = csv.DictReader(f)
        rows = [tuple(r.values()) for r in reader]
    cur.executemany(f"INSERT INTO orders VALUES ({','.join(['?'] * 16)})", rows)
    conn.execute("CREATE INDEX idx_ym ON orders(year_month)")
    conn.execute("CREATE INDEX idx_cust ON orders(customer_id)")
    conn.commit()
    return conn


def run_query_to_markdown(conn, sql_path):
    with open(sql_path) as f:
        sql = f.read()
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()

    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(lines), len(rows)


def main():
    conn = load_db()
    os.makedirs(RESULTS_DIR, exist_ok=True)
    for sql_path in sorted(glob.glob("sql_queries/*.sql")):
        name = os.path.splitext(os.path.basename(sql_path))[0]
        table_md, n_rows = run_query_to_markdown(conn, sql_path)
        out_path = os.path.join(RESULTS_DIR, f"{name}.md")
        # Cap huge outputs (e.g. cohort table) to first 60 rows in the saved preview.
        preview_lines = table_md.splitlines()
        if len(preview_lines) > 62:
            table_md = "\n".join(preview_lines[:62]) + f"\n\n_...truncated, {n_rows} total rows..._"
        with open(out_path, "w") as f:
            f.write(f"# Result: {name}\n\n{table_md}\n")
        print(f"{name}: {n_rows} rows -> {out_path}")
    conn.close()


if __name__ == "__main__":
    main()
