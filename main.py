from fastapi import FastAPI
from db import get_connection

app = FastAPI()

@app.get("/")
def root():
    return {"message": "API działa"}

@app.get("/salons")
def get_salons():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM salon")
    salons = cursor.fetchall()

    cursor.close()
    conn.close()
    return salons

@app.post("/slots/test")
def add_test_slot():
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO time_slot (salon_id, hairdresser_id, start_time, end_time, status)
    VALUES (%s, %s, %s, %s, %s)
    """
    values = (1, 1, "2026-03-26 12:00:00", "2026-03-26 13:00:00", "available")

    cursor.execute(query, values)
    conn.commit()

    new_id = cursor.lastrowid

    cursor.close()
    conn.close()

    return {"message": "Dodano slot", "slot_id": new_id}