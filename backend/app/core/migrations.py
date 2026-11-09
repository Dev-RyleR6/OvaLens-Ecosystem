"""
Automatic lightweight schema migrations for PostgreSQL.
Ensures that schema evolutions (new enum values, new columns, indexes)
are applied safely on startup without requiring destructive database resets.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def run_migrations(engine: Engine) -> None:
    """Run idempotent schema updates on startup."""
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("ALTER TABLE candling_sessions ADD COLUMN IF NOT EXISTS operator_id UUID REFERENCES users(user_id) ON DELETE SET NULL;"))
        # 1. Update routingaction enum to include MANUAL_REVIEW if not present
        try:
            conn.execute(text("ALTER TYPE routingaction ADD VALUE IF NOT EXISTS 'MANUAL_REVIEW';"))
        except Exception:
            pass

        # 2. Add manual_review_count to candling_sessions
        conn.execute(text(
            "ALTER TABLE candling_sessions ADD COLUMN IF NOT EXISTS manual_review_count INTEGER DEFAULT 0 NOT NULL;"
        ))

        # 3. Add override and physical tracking columns to egg_scans
        conn.execute(text(
            "ALTER TABLE egg_scans ADD COLUMN IF NOT EXISTS is_overridden BOOLEAN DEFAULT FALSE NOT NULL;"
        ))
        conn.execute(text(
            "ALTER TABLE egg_scans ADD COLUMN IF NOT EXISTS override_reason TEXT;"
        ))
        conn.execute(text(
            "ALTER TABLE egg_scans ADD COLUMN IF NOT EXISTS overridden_at TIMESTAMP WITH TIME ZONE;"
        ))
        conn.execute(text(
            "ALTER TABLE egg_scans ADD COLUMN IF NOT EXISTS cradle_index INTEGER;"
        ))
        conn.execute(text(
            "ALTER TABLE egg_scans ADD COLUMN IF NOT EXISTS aspect_ratio NUMERIC(4, 2);"
        ))
        conn.execute(text(
            "ALTER TABLE egg_scans ADD COLUMN IF NOT EXISTS vascular_index NUMERIC(5, 3);"
        ))

        # 4. Add edge_url and telemetry columns to devices
        conn.execute(text(
            "ALTER TABLE devices ADD COLUMN IF NOT EXISTS edge_url VARCHAR(255);"
        ))
        conn.execute(text(
            "ALTER TABLE devices ADD COLUMN IF NOT EXISTS telemetry JSON;"
        ))

        # 5. Indexes for fast query filtering
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_scans_routing_action ON egg_scans(routing_action);"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_scans_is_overridden ON egg_scans(is_overridden);"
        ))
