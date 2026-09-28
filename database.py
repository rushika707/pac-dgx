import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "policy.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_id TEXT UNIQUE,
        policy_name TEXT,
        version TEXT,
        effective_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
""")


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policy_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER,
            rule_id TEXT,
            description TEXT,
            outcome TEXT,
            FOREIGN KEY (policy_id) REFERENCES policies(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER,
            total_records INTEGER,
            batch_size INTEGER,
            total_batches INTEGER,
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            FOREIGN KEY (policy_id) REFERENCES policies(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER,
            execution_id INTEGER,
            record_id TEXT,
            decision TEXT,
            reason TEXT,
            remediation TEXT,
            input_data TEXT,
            evaluated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (policy_id) REFERENCES policies(id),
            FOREIGN KEY (execution_id) REFERENCES executions(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS triggered_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id INTEGER,
            rule_id TEXT,
            FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
        )
    """)

    conn.commit()

    # Migration for an existing database
    columns = {
        row["name"]
        for row in cursor.execute(
            "PRAGMA table_info(evaluations)"
        ).fetchall()
    }

    if "execution_id" not in columns:
        cursor.execute(
            "ALTER TABLE evaluations ADD COLUMN execution_id INTEGER"
        )

    if "input_data" not in columns:
        cursor.execute(
            "ALTER TABLE evaluations ADD COLUMN input_data TEXT"
        )
        # Migration for execution range
    execution_columns = {
        row["name"]
        for row in cursor.execute(
            "PRAGMA table_info(executions)"
        ).fetchall()
    }

    if "start_record" not in execution_columns:
        cursor.execute(
            "ALTER TABLE executions ADD COLUMN start_record INTEGER"
        )

    if "end_record" not in execution_columns:
        cursor.execute(
            "ALTER TABLE executions ADD COLUMN end_record INTEGER"
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database ready: {DB_PATH}")