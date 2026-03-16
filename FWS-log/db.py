import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "fws_logs"),
        user=os.getenv("POSTGRES_USER", "fws"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def insert_log(level: str, module: str, event: str, message: str,
               vm_name: str, server_ip: str):
    sql = """
        INSERT INTO logs (level, module, event, message, vm_name, server_ip)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (level, module, event, message, vm_name, server_ip))


def fetch_logs(level: str = None, event: str = None,
               vm_name: str = None, limit: int = 100) -> list:
    conditions = []
    params = []

    if level:
        conditions.append("level = %s")
        params.append(level)
    if event:
        conditions.append("event = %s")
        params.append(event)
    if vm_name:
        conditions.append("vm_name = %s")
        params.append(vm_name)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM logs {where} ORDER BY timestamp DESC LIMIT %s"
    params.append(limit)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
