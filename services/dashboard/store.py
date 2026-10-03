"""SQLite persistence for assessment runs.

WHY THIS EXISTS
---------------
Streamlit re-executes its whole script on every interaction, so anything held
in Python variables disappears as soon as the analyst clicks something. Without
storage the dashboard could only ever show the single most recent run, which is
not enough to demonstrate a Sprint 1 assessment.

WHY SQLITE
----------
The project plan names "SQLite initially; PostgreSQL optional" as the results
database. SQLite needs no extra container, no credentials and no network
service, so it adds nothing to the attack surface of the lab. The file lives on
a Docker volume so results survive `docker compose down`.

WHY THE RAW RESPONSE IS STORED
------------------------------
The project requires findings to be explainable and reproducible. Storing only
the verdict would make a finding an assertion. Storing the agent's full run
trace alongside it means any PASS / WARNING / FAIL can be re-derived from the
evidence later, including after the verdict logic changes in Sprint 2.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time

DB_PATH = os.environ.get("RESULTS_DB", "/evidence/results.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at       REAL    NOT NULL,
    scan_id           TEXT    NOT NULL,
    test_id           TEXT    NOT NULL,
    user              TEXT,
    role              TEXT,          -- role claimed by the request
    effective_role    TEXT,          -- role resolved from the identity table
    message           TEXT,
    result            TEXT    NOT NULL,
    expected_decision TEXT,
    observed_decision TEXT,
    policy_id         TEXT,
    resource          TEXT,
    tool              TEXT,
    stop_reason       TEXT,
    canaries          TEXT,          -- JSON array
    notes             TEXT,          -- JSON array
    agent_message     TEXT,
    raw_response      TEXT           -- JSON: the full AgentResponse trace
);

CREATE INDEX IF NOT EXISTS idx_findings_scan ON findings(scan_id);
"""


# Every column `record()` writes. Used to detect a pre-existing `findings`
# table that does not match this schema.
EXPECTED_COLUMNS = {
    "recorded_at", "scan_id", "test_id", "user", "role", "effective_role",
    "message", "result", "expected_decision", "observed_decision", "policy_id",
    "resource", "tool", "stop_reason", "canaries", "notes", "agent_message",
    "raw_response",
}

# Set by connect() when it finds and sets aside an incompatible table, so the
# dashboard can tell the analyst their history was archived rather than leaving
# them to wonder where it went. A module global rather than a changed return
# type, so existing callers and tests are unaffected.
LAST_SCHEMA_NOTE: str | None = None


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the findings table, setting aside an incompatible existing one.

    WHY THIS IS NEEDED
    ------------------
    `CREATE TABLE IF NOT EXISTS` does exactly what it says: if a table of that
    name already exists it is left alone, whatever columns it has. SQLite has
    no automatic migration. So a results.db left behind by a different version
    of this project -- or by a different project that happened to use the same
    Docker volume name -- produces a table that every INSERT then fails
    against, with the unhelpful message:

        sqlite3.OperationalError: table findings has no column named recorded_at

    That is not hypothetical: an earlier AgentSentry lab prototype used both
    the same Compose project name and the same volume name, so its database
    was still mounted into this service and caused exactly that error.

    The incompatible table is renamed rather than dropped. Deleting somebody's
    recorded assessment history to fix a startup problem is the wrong trade,
    and the archived table can still be read with any SQLite browser.
    """
    global LAST_SCHEMA_NOTE
    LAST_SCHEMA_NOTE = None

    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='findings'"
    ).fetchone()

    if exists:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(findings)")}
        missing = EXPECTED_COLUMNS - columns
        if missing:
            archived = "findings_incompatible_" + time.strftime("%Y%m%d_%H%M%S")
            conn.execute(f"ALTER TABLE findings RENAME TO {archived}")
            conn.commit()
            LAST_SCHEMA_NOTE = (
                f"An existing `findings` table did not match this schema "
                f"(missing: {', '.join(sorted(missing))}). It has been renamed "
                f"to `{archived}` and a new table created. No rows were deleted."
            )

    conn.executescript(SCHEMA)
    conn.commit()


def connect() -> sqlite3.Connection:
    """Open the results database, creating the file and schema if needed."""
    directory = os.path.dirname(DB_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def record(conn: sqlite3.Connection, finding) -> int:
    """Persist one finding. Returns its row id."""
    cur = conn.execute(
        """INSERT INTO findings (
               recorded_at, scan_id, test_id, user, role, effective_role, message, result,
               expected_decision, observed_decision, policy_id, resource, tool,
               stop_reason, canaries, notes, agent_message, raw_response)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            time.time(), finding.scan_id, finding.test_id, finding.user,
            finding.role, finding.effective_role, finding.message, finding.result,
            finding.expected_decision, finding.observed_decision,
            finding.policy_id, finding.resource, finding.tool,
            finding.stop_reason,
            json.dumps(finding.canaries), json.dumps(finding.notes),
            finding.agent_message, json.dumps(finding.raw_response, default=str),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def recent(conn: sqlite3.Connection, limit: int = 200) -> list[dict]:
    """Most recent findings first."""
    rows = conn.execute(
        "SELECT * FROM findings ORDER BY recorded_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def counts(conn: sqlite3.Connection) -> dict:
    """PASS / WARNING / FAIL totals for the summary tiles."""
    out = {"PASS": 0, "WARNING": 0, "FAIL": 0}
    for row in conn.execute("SELECT result, COUNT(*) c FROM findings GROUP BY result"):
        out[row["result"]] = row["c"]
    return out


def clear(conn: sqlite3.Connection) -> None:
    """Wipe recorded findings. Used between demo runs."""
    conn.execute("DELETE FROM findings")
    conn.commit()
