import sys
import os
import psycopg2

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.core.config import settings

print(f"Testing database connection to: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME} (User: {settings.DB_USER})")

try:
    conn = psycopg2.connect(settings.database_url)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    db_version = cur.fetchone()
    print("✅ Connected successfully to PostgreSQL!")
    print(f"PostgreSQL Version: {db_version[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("Please verify PostgreSQL is running and check backend/.env credentials.")