import os
from contextlib import contextmanager
from datetime import date
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import pandas as pd
import psycopg


class DatabaseConnectionError(RuntimeError):
    """Raised when the app cannot connect to the configured database."""


def _resolve_dsn() -> str:
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        return dsn

    try:
        import streamlit as st

        secret_dsn = st.secrets.get("DATABASE_URL")
        if secret_dsn:
            return secret_dsn
    except Exception:
        pass

    return "postgresql://postgres:postgres@localhost:5432/attendance_tracker"


def _normalize_dsn(dsn: str) -> str:
    parsed = urlparse(dsn)
    if not parsed.hostname or parsed.hostname in {"localhost", "127.0.0.1"}:
        return dsn

    query = dict(parse_qsl(parsed.query))
    if "sslmode" in query:
        return dsn

    query["sslmode"] = "require"
    return urlunparse(parsed._replace(query=urlencode(query)))


@contextmanager
def get_conn():
    try:
        conn = psycopg.connect(_normalize_dsn(_resolve_dsn()), connect_timeout=10)
    except psycopg.OperationalError as exc:
        raise DatabaseConnectionError(
            "Unable to connect to PostgreSQL. Set DATABASE_URL (or Streamlit secret DATABASE_URL) "
            "to a reachable database, and include sslmode=require for hosted DB providers."
        ) from exc

    try:
        yield conn
    finally:
        conn.close()


def run_sql_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


def fetch_df(query: str, params: tuple | None = None) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql(query, conn, params=params)


def execute(query: str, params: tuple | None = None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
        conn.commit()


def log_audit(actor: str, action: str, entity_table: str, entity_id: str | None, before_data=None, after_data=None):
    execute(
        """
        INSERT INTO audit_log (actor, action, entity_table, entity_id, before_data, after_data)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (actor, action, entity_table, entity_id, before_data, after_data),
    )


def bulk_insert_df(df: pd.DataFrame, table: str):
    if df.empty:
        return
    cols = list(df.columns)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    with get_conn() as conn:
        with conn.cursor() as cur:
            for row in df.itertuples(index=False, name=None):
                cur.execute(sql, row)
        conn.commit()


def today_iso() -> str:
    return date.today().isoformat()
