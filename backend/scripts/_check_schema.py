import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
)
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
tables = [row[0] for row in cur.fetchall()]
print("Tables in DB:", tables)

for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM \"{t}\";")
    print(f"  {t}: {cur.fetchone()[0]} rows")

cur.close()
conn.close()
