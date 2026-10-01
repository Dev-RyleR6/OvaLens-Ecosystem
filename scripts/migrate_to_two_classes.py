"""One-way PostgreSQL migration to the Day 10, two-class domain contract."""

import os
import sys

from sqlalchemy import inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import engine  # noqa: E402


def run_migration() -> None:
    if engine.dialect.name != "postgresql":
        raise RuntimeError("This migration targets the production PostgreSQL database only.")

    with engine.begin() as conn:
        session_columns = {column["name"] for column in inspect(conn).get_columns("candling_sessions")}

        conn.execute(text("UPDATE egg_scans SET final_class = 'INFERTILE' WHERE final_class::text = 'ABNORMAL'"))
        if "abnormal_count" in session_columns:
            conn.execute(text("""
                UPDATE candling_sessions
                SET infertile_count = infertile_count + abnormal_count,
                    abnormal_count = 0
            """))
        conn.execute(text("UPDATE candling_sessions SET stage = 'DAY_10' WHERE stage::text <> 'DAY_10'"))
        conn.execute(text("UPDATE batches SET current_stage = 'DAY_10' WHERE current_stage::text IN ('DAY_18', 'DAY_25')"))

        conn.execute(text("ALTER TABLE egg_scans ALTER COLUMN final_class TYPE VARCHAR(16) USING final_class::text"))
        conn.execute(text("DROP TYPE IF EXISTS fertilityclass"))
        conn.execute(text("CREATE TYPE fertilityclass AS ENUM ('FERTILE', 'INFERTILE')"))
        conn.execute(text("ALTER TABLE egg_scans ALTER COLUMN final_class TYPE fertilityclass USING final_class::fertilityclass"))

        conn.execute(text("ALTER TABLE candling_sessions ALTER COLUMN stage TYPE VARCHAR(16) USING stage::text"))
        conn.execute(text("DROP TYPE IF EXISTS candlingstage"))
        conn.execute(text("CREATE TYPE candlingstage AS ENUM ('DAY_10')"))
        conn.execute(text("ALTER TABLE candling_sessions ALTER COLUMN stage TYPE candlingstage USING stage::candlingstage"))

        conn.execute(text("ALTER TABLE batches ALTER COLUMN current_stage TYPE VARCHAR(16) USING current_stage::text"))
        conn.execute(text("DROP TYPE IF EXISTS batchstage"))
        conn.execute(text("CREATE TYPE batchstage AS ENUM ('SETTING', 'DAY_10', 'HATCHED', 'COMPLETED')"))
        conn.execute(text("ALTER TABLE batches ALTER COLUMN current_stage TYPE batchstage USING current_stage::batchstage"))

        if "abnormal_count" in session_columns:
            conn.execute(text("ALTER TABLE candling_sessions DROP COLUMN abnormal_count"))

    print("Migration complete: DAY_10 only; FERTILE/INFERTILE only.")


if __name__ == "__main__":
    run_migration()
