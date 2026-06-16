import os
from mysql.connector.pooling import MySQLConnectionPool

WRITE_HOST = os.getenv("DB_WRITE_HOST") or os.getenv("DB_HOST", "localhost")
READ_HOST = os.getenv("DB_READ_HOST") or WRITE_HOST
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "hair_salon_db")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 5))

_WRITE_POOL = None
_READ_POOL = None


def _build_pool(host: str, pool_name: str) -> MySQLConnectionPool:
    return MySQLConnectionPool(
        pool_name=pool_name,
        pool_size=DB_POOL_SIZE,
        pool_reset_session=True,
        host=host,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
    )


def get_write_connection():
    global _WRITE_POOL
    if _WRITE_POOL is None:
        _WRITE_POOL = _build_pool(WRITE_HOST, "hair_salon_pool_write")
    return _WRITE_POOL.get_connection()


def get_read_connection():
    global _READ_POOL
    if _READ_POOL is None:
        _READ_POOL = _build_pool(READ_HOST, "hair_salon_pool_read")
    return _READ_POOL.get_connection()


if __name__ == "__main__":
    conn = get_read_connection()
    print("Połączenie z bazą działa!")
    conn.close()
