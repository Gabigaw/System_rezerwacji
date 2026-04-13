from mysql.connector.pooling import MySQLConnectionPool

POOL = MySQLConnectionPool(
    pool_name="hair_salon_pool",
    pool_size=5,
    pool_reset_session=True,
    host="localhost",
    user="root",
    password="root",
    database="hair_salon_db",
    charset="utf8mb4",
)

def get_connection():
    return POOL.get_connection()

if __name__ == "__main__":
    conn = get_connection()
    print("Połączenie z bazą działa!")
    conn.close()