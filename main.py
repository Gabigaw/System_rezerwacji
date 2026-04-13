from contextlib import contextmanager
from datetime import date, datetime, time, timedelta

import mysql.connector
from fastapi import FastAPI, HTTPException, Query, status

from db import get_connection
from models import BookSlotRequest

app = FastAPI()

ALLOWED_SLOT_STATUSES = {"available", "booked", "cancelled", "blocked"}


@contextmanager
def connection_cursor(dictionary: bool = False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()


@app.get("/")
def root():
    return {"message": "API działa"}

@app.get("/salons")
def get_salons():
    with connection_cursor(dictionary=True) as (_, cursor):
        cursor.execute("SELECT * FROM salon ORDER BY salon_id")
        return cursor.fetchall()


def _normalize_day_range(date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
    start_datetime = datetime.combine(date_from, time.min) if date_from else None
    end_datetime = datetime.combine(date_to + timedelta(days=1), time.min) if date_to else None
    return start_datetime, end_datetime


def _build_slot_filters(
    date_from: date | None,
    date_to: date | None,
    salon_id: int | None,
    hairdresser_id: int | None,
    slot_status: str | None,
) -> tuple[str, list[object]]:
    where_clauses = ["1 = 1"]
    parameters: list[object] = []

    start_datetime, end_datetime = _normalize_day_range(date_from, date_to)
    if start_datetime is not None:
        where_clauses.append("ts.start_time >= %s")
        parameters.append(start_datetime)
    if end_datetime is not None:
        where_clauses.append("ts.start_time < %s")
        parameters.append(end_datetime)
    if salon_id is not None:
        where_clauses.append("ts.salon_id = %s")
        parameters.append(salon_id)
    if hairdresser_id is not None:
        where_clauses.append("ts.hairdresser_id = %s")
        parameters.append(hairdresser_id)
    if slot_status is not None:
        if slot_status not in ALLOWED_SLOT_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nieprawidłowy status slotu.")
        where_clauses.append("ts.status = %s")
        parameters.append(slot_status)

    return " AND ".join(where_clauses), parameters


@app.get("/slots")
def get_slots(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    salon_id: int | None = Query(default=None, gt=0),
    hairdresser_id: int | None = Query(default=None, gt=0),
    slot_status: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_from nie może być późniejszy niż date_to.")

    where_clause, parameters = _build_slot_filters(date_from, date_to, salon_id, hairdresser_id, slot_status)
    offset = (page - 1) * limit

    count_query = f"""
        SELECT COUNT(*) AS total
        FROM time_slot ts
        WHERE {where_clause}
    """

    data_query = f"""
        SELECT
            ts.slot_id,
            ts.salon_id,
            salon.name AS salon_name,
            ts.hairdresser_id,
            CONCAT(hairdresser.first_name, ' ', hairdresser.last_name) AS hairdresser_name,
            ts.start_time,
            ts.end_time,
            ts.status,
            ts.created_at
        FROM time_slot ts
        INNER JOIN salon ON salon.salon_id = ts.salon_id
        INNER JOIN hairdresser ON hairdresser.hairdresser_id = ts.hairdresser_id
        WHERE {where_clause}
        ORDER BY ts.start_time, ts.slot_id
        LIMIT %s OFFSET %s
    """

    with connection_cursor(dictionary=True) as (_, cursor):
        cursor.execute(count_query, parameters)
        total = cursor.fetchone()["total"]

        cursor.execute(data_query, parameters + [limit, offset])
        slots = cursor.fetchall()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "slots": slots,
    }


@app.post("/slots/book", status_code=status.HTTP_201_CREATED)
def book_slot(payload: BookSlotRequest):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        cursor.execute(
            """
            SELECT client_id
            FROM client
            WHERE client_id = %s
            """,
            (payload.client_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nie znaleziono klienta.")

        cursor.execute(
            """
            SELECT service_id
            FROM service
            WHERE service_id = %s AND is_active = TRUE
            """,
            (payload.service_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nie znaleziono aktywnej usługi.")

        cursor.execute(
            """
            SELECT
                ts.slot_id,
                ts.status,
                ts.hairdresser_id,
                CASE WHEN hs.service_id IS NULL THEN 0 ELSE 1 END AS service_supported
            FROM time_slot ts
            LEFT JOIN hairdresser_service hs
                ON hs.hairdresser_id = ts.hairdresser_id
               AND hs.service_id = %s
            WHERE ts.slot_id = %s
            FOR UPDATE
            """,
            (payload.service_id, payload.slot_id),
        )
        slot_row = cursor.fetchone()
        if slot_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nie znaleziono slotu.")

        if slot_row["service_supported"] == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wybrana usługa nie jest obsługiwana przez przypisanego fryzjera.",
            )

        if slot_row["status"] != "available":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot jest już zajęty.")

        cursor.execute(
            """
            INSERT INTO appointment (slot_id, client_id, service_id, status, notes)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (payload.slot_id, payload.client_id, payload.service_id, "pending", payload.notes),
        )
        appointment_id = cursor.lastrowid

        cursor.execute(
            """
            UPDATE time_slot
            SET status = 'booked'
            WHERE slot_id = %s
            """,
            (payload.slot_id,),
        )

        conn.commit()

        cursor.execute(
            """
            SELECT appointment_id, slot_id, client_id, service_id, status, booking_time
            FROM appointment
            WHERE appointment_id = %s
            """,
            (appointment_id,),
        )
        return cursor.fetchone()

    except HTTPException:
        conn.rollback()
        raise
    except mysql.connector.Error as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd bazy danych podczas rezerwacji: {exc.msg}",
        ) from exc
    finally:
        cursor.close()
        conn.close()
