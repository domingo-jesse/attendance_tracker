import os
from contextlib import contextmanager
from datetime import date

import pandas as pd
import psycopg


DB_DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/attendance_tracker")


@contextmanager
def get_conn():
    conn = psycopg.connect(DB_DSN)
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
