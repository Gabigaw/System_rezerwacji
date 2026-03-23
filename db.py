import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="miejsce na hasło",
        database="hair_salon_db"
    )

if __name__ == "__main__":
    conn = get_connection()
    print("Połączenie z bazą działa!")
    conn.close()