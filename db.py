from os import getenv
from mysql.connector.pooling import MySQLConnectionPool

POOL = MySQLConnectionPool(
    pool_name="hair_salon_pool",
    pool_size=int(getenv("DB_POOL_SIZE", "30")),
    pool_reset_session=True,
    host=getenv("DB_HOST", "localhost"),
    user=getenv("DB_USER", "root"),
    password=getenv("DB_PASSWORD", "root"),
    database=getenv("DB_NAME", "hair_salon_db"),
    charset="utf8mb4",
)

def get_connection():
    return POOL.get_connection()

if __name__ == "__main__":
    conn = get_connection()
    print("Połączenie z bazą działa!")
    conn.close()