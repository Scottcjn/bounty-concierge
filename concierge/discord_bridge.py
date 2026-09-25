# SPDX-License-Identifier: MIT
"""Discord-to-chain wallet migration bridge.

Queries the Sophiacord Discord economy database (SQLite on NAS) via SSH,
and tracks migrations in a local database. Used by the ``concierge wallet
migrate`` CLI subcommand.
"""

import json
import os
import re
import sqlite3
import subprocess

from concierge import config

# Discord snowflakes are 17-20 digit integers. We refuse anything else
# before using the value in a SQL fragment -- this is a defence-in-depth
# guard that backs the parameterised queries introduced below.
_DISCORD_USER_ID_RE = re.compile(r"^\d{17,20}$")
_MIN_BALANCE_MAX = 1_000_000_000.0

# ---------------------------------------------------------------------------
# Local migration tracking
# ---------------------------------------------------------------------------

_TRACKING_DIR = os.path.join(os.path.expanduser("~"), ".concierge")
_TRACKING_DB = os.path.join(_TRACKING_DIR, "migrations.db")

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS migrations (
    id INTEGER PRIMARY KEY,
    discord_user_id TEXT NOT NULL,
    target_wallet TEXT NOT NULL,
    amount_rtc REAL NOT NULL,
    chain_tx_id TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(discord_user_id)
);
"""


def _init_tracking_db():
    """Ensure the local tracking database exists and has the schema."""
    os.makedirs(_TRACKING_DIR, exist_ok=True)
    con = sqlite3.connect(_TRACKING_DB)
    con.execute(_SCHEMA)
    con.commit()
    return con


def record_migration(discord_id, wallet, amount, chain_tx_id, status="completed"):
    """Record a completed migration in the local tracking DB."""
    con = _init_tracking_db()
    try:
        con.execute(
            "INSERT INTO migrations (discord_user_id, target_wallet, amount_rtc, "
            "chain_tx_id, status) VALUES (?, ?, ?, ?, ?)",
            (str(discord_id), wallet, amount, chain_tx_id, status),
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Already migrated
    finally:
        con.close()


def record_migration_force(discord_id, wallet, amount, chain_tx_id, status="completed"):
    """Record a migration, replacing any existing record for this user."""
    con = _init_tracking_db()
    try:
        con.execute(
            "INSERT OR REPLACE INTO migrations (discord_user_id, target_wallet, "
            "amount_rtc, chain_tx_id, status) VALUES (?, ?, ?, ?, ?)",
            (str(discord_id), wallet, amount, chain_tx_id, status),
        )
        con.commit()
        return True
    finally:
        con.close()


def get_migration_history():
    """Return all migration records, newest first."""
    con = _init_tracking_db()
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM migrations ORDER BY created_at DESC"
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def already_migrated(discord_id):
    """Check if a Discord user has already been migrated."""
    con = _init_tracking_db()
    row = con.execute(
        "SELECT id FROM migrations WHERE discord_user_id = ?",
        (str(discord_id),),
    ).fetchone()
    con.close()
    return row is not None


# ---------------------------------------------------------------------------
# SSH queries to NAS Discord economy database
# ---------------------------------------------------------------------------

def _ssh_cmd():
    """Build the base SSH command list for connecting to the NAS."""
    return [
        "sshpass", "-p", config.DISCORD_NAS_PASSWORD,
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        f"{config.DISCORD_NAS_USER}@{config.DISCORD_NAS_HOST}",
        "python3",
    ]


def _ssh_run_script(script, extra_stdin=""):
    """Run a Python script on the NAS via SSH stdin pipe.

    Piping via stdin avoids all shell quoting issues with parentheses,
    semicolons, and nested quotes that break when passed as -c args.
    The optional *extra_stdin* string is prepended before the script --
    it is the channel used to feed parameter values into the remote script
    without interpolating them into the SQL text on the client side.

    Returns:
        (stdout, stderr, returncode) tuple.
    """
    if not config.DISCORD_NAS_PASSWORD:
        return ("", "DISCORD_NAS_PASSWORD not set", 1)

    try:
        result = subprocess.run(
            _ssh_cmd(),
            input=(extra_stdin or "") + script,
            capture_output=True, text=True, timeout=30,
        )
        return (result.stdout.strip(), result.stderr.strip(), result.returncode)
    except subprocess.TimeoutExpired:
        return ("", "SSH timed out (30s)", 1)
    except FileNotFoundError:
        return ("", "sshpass not installed (apt install sshpass)", 1)


def _ssh_query(sql, params=()):
    """Run a parameterised SQL query on the NAS via SSH and return parsed JSON rows.

    *sql* must be a static query string with `?` placeholders. *params* is
    a tuple of values that are passed to the remote script via stdin as a
    single JSON line and bound with sqlite3 parameter substitution -- this
    closes the SQL injection that existed when caller-supplied values were
    interpolated into the SQL text with `%` formatting.
    """
    db_path = config.DISCORD_DB_PATH
    # NOTE: sql is a static literal from our own code; we wrap it in repr()
    # to make the f-string produce a safe Python literal regardless of any
    # inner quotes the SQL happens to contain.
    sql_repr = repr(sql)
    script = (
        "import json, sqlite3\n"
        "params = json.loads(__import__('sys').stdin.readline())\n"
        f"c = sqlite3.connect({db_path!r})\n"
        "c.row_factory = sqlite3.Row\n"
        f"rows = c.execute({sql_repr}, params).fetchall()\n"
        "print(json.dumps([dict(r) for r in rows]))\n"
        "c.close()\n"
    )
    param_payload = json.dumps(list(params)) + "\n"
    stdout, stderr, rc = _ssh_run_script(script, extra_stdin=param_payload)
    if rc != 0:
        return {"error": f"SSH query failed: {stderr}"}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"error": f"Failed to parse result: {stdout[:200]}"}


def get_discord_balance(user_id):
    """Get the Discord economy balance for a single user.

    Returns:
        Dict with user_id, balance, total_earned, total_spent,
        or an error dict.
    """
    if not _DISCORD_USER_ID_RE.match(str(user_id or "")):
        return {"error": f"Invalid Discord user id: {user_id!r}"}
    sql = (
        "SELECT user_id, balance, total_earned, total_spent "
        "FROM balances WHERE user_id = ?"
    )
    result = _ssh_query(sql, (str(user_id),))
    if isinstance(result, dict) and "error" in result:
        return result
    if not result:
        return {"error": f"Discord user {user_id} not found in economy DB"}
    return result[0]


def list_discord_holders(min_balance=0.1):
    """List all Discord economy holders with balance >= min_balance.

    Returns:
        List of dicts sorted by balance descending, or an error dict.
    """
    try:
        min_balance_f = float(min_balance)
    except (TypeError, ValueError):
        return {"error": f"Invalid min_balance: {min_balance!r}"}
    if min_balance_f < 0 or min_balance_f > _MIN_BALANCE_MAX:
        return {"error": f"min_balance out of range: {min_balance_f}"}
    sql = (
        "SELECT user_id, balance, total_earned, total_spent "
        "FROM balances WHERE balance >= ? "
        "ORDER BY balance DESC"
    )
    return _ssh_query(sql, (min_balance_f,))


def debit_discord_balance(user_id, amount):
    """Debit a user's Discord economy balance and record the transaction.

    Runs UPDATE + INSERT in the same script for atomicity. Both *user_id*
    and *amount* are validated client-side and bound via sqlite3 parameters
    on the remote side so the values never appear in the SQL text.

    Returns:
        True on success, error dict on failure.
    """
    if not _DISCORD_USER_ID_RE.match(str(user_id or "")):
        return {"error": f"Invalid Discord user id: {user_id!r}"}
    try:
        amount_f = float(amount)
    except (TypeError, ValueError):
        return {"error": f"Invalid amount: {amount!r}"}
    if amount_f <= 0 or amount_f > _MIN_BALANCE_MAX:
        return {"error": f"amount out of range: {amount_f}"}
    db_path = config.DISCORD_DB_PATH
    script = (
        "import json, sqlite3\n"
        "params = json.loads(__import__('sys').stdin.readline())\n"
        f"c = sqlite3.connect({db_path!r})\n"
        "c.execute(\n"
        "    'UPDATE balances SET balance = balance - ?,\n"
        "     total_spent = total_spent + ? WHERE user_id = ?',\n"
        "    (params[1], params[1], params[0]),\n"
        ")\n"
        "c.execute(\n"
        "    'INSERT INTO transactions\n"
        "     (from_user, to_user, amount, type, description)\n"
        "     VALUES (?, ?, ?, ?, ?)',\n"
        "    (params[0], 'CHAIN_MIGRATION', params[1],\n"
        "     'migration', 'Migrated to on-chain RTC wallet'),\n"
        ")\n"
        "c.commit()\n"
        "print('OK')\n"
        "c.close()\n"
    )
    payload = json.dumps([str(user_id), amount_f]) + "\n"
    stdout, stderr, rc = _ssh_run_script(script, extra_stdin=payload)
    if rc != 0:
        return {"error": f"Debit failed: {stderr}"}
    if "OK" in stdout:
        return True
    return {"error": f"Unexpected output: {stdout}"}
