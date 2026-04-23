
import json
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

DB_NAME = os.getenv("DB_NAME", "kppas")
DB_USER = os.getenv("DB_USER", "kppas_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "kppas_pass")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

TABLE_NAME = "health_covid_data"

# Load data from JSON file
def load_data(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def create_table(conn):
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id SERIAL PRIMARY KEY,
                date DATE,
                county TEXT,
                indicator TEXT,
                value TEXT,
                source TEXT
            );
        """)
        conn.commit()

def insert_data(conn, records):
    with conn.cursor() as cur:
        for rec in records:
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (date, county, indicator, value, source)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                rec.get("date"),
                rec.get("county"),
                rec.get("indicator"),
                rec.get("value"),
                rec.get("source")
            ))
        conn.commit()

def main():
    data = load_data("health_data_prototype.json")
    print(f"Loaded {len(data)} records from JSON.")
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    create_table(conn)
    insert_data(conn, data)
    print(f"Inserted {len(data)} records into table '{TABLE_NAME}'.")
    conn.close()

if __name__ == "__main__":
    main()
