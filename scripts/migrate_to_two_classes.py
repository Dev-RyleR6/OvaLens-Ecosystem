"""
Migration script to convert database schema and records to:
1. Strict 2-Class Model: FERTILE and INFERTILE (merging ABNORMAL into INFERTILE).
2. Single Candling Stage: DAY_10.
"""

import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import engine
from sqlalchemy import text


def run_migration():
    print("[*] Running migration to 2-class Day 10 model...")
    with engine.connect() as conn:
        r1 = conn.execute(text("UPDATE egg_scans SET final_class = 'INFERTILE' WHERE final_class = 'ABNORMAL'"))
        r2 = conn.execute(text("UPDATE candling_sessions SET infertile_count = infertile_count + abnormal_count, abnormal_count = 0"))
        r3 = conn.execute(text("UPDATE batches SET current_stage = 'DAY_10' WHERE current_stage IN ('DAY_18', 'DAY_25')"))
        conn.commit()
        print(f"[OK] Migrated {r1.rowcount} scans to INFERTILE.")
        print(f"[OK] Updated {r2.rowcount} session counts.")
        print(f"[OK] Updated {r3.rowcount} batches to DAY_10.")


if __name__ == "__main__":
    run_migration()
