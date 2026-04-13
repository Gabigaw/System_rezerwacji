from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta

from db import get_connection


SPECIALIZATIONS = [
    "męskie strzyżenie",
    "damskie strzyżenie",
    "koloryzacja",
    "modelowanie",
    "stylizacja",
]

SERVICES = [
    ("Strzyżenie męskie", "Klasyczne strzyżenie męskie", 30, 80.00),
    ("Strzyżenie damskie", "Strzyżenie damskie z modelowaniem", 45, 120.00),
    ("Koloryzacja", "Koloryzacja włosów", 90, 260.00),
    ("Modelowanie", "Układanie i modelowanie", 30, 70.00),
    ("Pielęgnacja", "Zabieg pielęgnacyjny", 60, 150.00),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed danych dla systemu rezerwacji salonów.")
    parser.add_argument("--start-date", default="2026-04-14", help="Data startowa w formacie YYYY-MM-DD.")
    parser.add_argument("--days", type=int, default=300, help="Liczba dni do wygenerowania.")
    parser.add_argument("--salons", type=int, default=100, help="Liczba salonów.")
    parser.add_argument("--hairdressers-per-salon", type=int, default=3, help="Liczba fryzjerów na salon.")
    parser.add_argument("--target-slots", type=int, default=100000, help="Docelowa liczba slotów.")
    parser.add_argument("--clients", type=int, default=1000, help="Liczba klientów testowych.")
    parser.add_argument("--batch-size", type=int, default=2000, help="Rozmiar paczki insertów.")
    return parser.parse_args()


def reset_tables(cursor) -> None:
    tables = [
        "queue_offer",
        "waiting_queue",
        "payment",
        "appointment",
        "time_slot",
        "hairdresser_service",
        "hairdresser",
        "client",
        "service",
        "salon",
    ]

    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in tables:
        cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


def chunked_insert(cursor, query: str, rows: list[tuple], batch_size: int) -> int:
    inserted = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        cursor.executemany(query, batch)
        inserted += len(batch)
    return inserted


def main() -> None:
    args = parse_args()
    start_date = date.fromisoformat(args.start_date)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        reset_tables(cursor)

        salon_rows = [
            (
                f"Salon {index:03d}",
                f"Ulica Testowa {index}, Warszawa",
                f"500{index:06d}"[:20],
                f"salon{index:03d}@example.com",
            )
            for index in range(1, args.salons + 1)
        ]
        cursor.executemany(
            """
            INSERT INTO salon (name, address, phone, email)
            VALUES (%s, %s, %s, %s)
            """,
            salon_rows,
        )

        service_rows = [
            (name, description, duration_minutes, base_price, True)
            for name, description, duration_minutes, base_price in SERVICES
        ]
        cursor.executemany(
            """
            INSERT INTO service (name, description, duration_minutes, base_price, is_active)
            VALUES (%s, %s, %s, %s, %s)
            """,
            service_rows,
        )

        salon_ids = list(range(1, args.salons + 1))
        hairdresser_map: dict[int, list[int]] = {salon_id: [] for salon_id in salon_ids}
        hairdresser_rows: list[tuple] = []
        for salon_id in salon_ids:
            for hairdresser_number in range(1, args.hairdressers_per_salon + 1):
                first_name = f"Imie{salon_id:03d}{hairdresser_number}"
                last_name = f"Nazwisko{salon_id:03d}{hairdresser_number}"
                specialization = SPECIALIZATIONS[(salon_id + hairdresser_number) % len(SPECIALIZATIONS)]
                hairdresser_rows.append(
                    (
                        salon_id,
                        first_name,
                        last_name,
                        f"600{salon_id:04d}{hairdresser_number}"[:20],
                        f"{first_name.lower()}.{last_name.lower()}@example.com",
                        specialization,
                        "active",
                    )
                )

        cursor.executemany(
            """
            INSERT INTO hairdresser (salon_id, first_name, last_name, phone, email, specialization, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            hairdresser_rows,
        )

        cursor.execute("SELECT hairdresser_id, salon_id FROM hairdresser ORDER BY hairdresser_id")
        for hairdresser_id, salon_id in cursor.fetchall():
            hairdresser_map[salon_id].append(hairdresser_id)

        cursor.execute("SELECT service_id FROM service ORDER BY service_id")
        service_ids = [row[0] for row in cursor.fetchall()]

        hairdresser_service_rows: list[tuple] = []
        for hairdresser_ids in hairdresser_map.values():
            for offset, hairdresser_id in enumerate(hairdresser_ids):
                start_index = offset % len(service_ids)
                selected_service_ids = [service_ids[(start_index + index) % len(service_ids)] for index in range(3)]
                for service_id in selected_service_ids:
                    hairdresser_service_rows.append((hairdresser_id, service_id, None))

        cursor.executemany(
            """
            INSERT INTO hairdresser_service (hairdresser_id, service_id, custom_price)
            VALUES (%s, %s, %s)
            """,
            hairdresser_service_rows,
        )

        client_rows = [
            (f"Klient{index:04d}", f"Testowy{index:04d}", f"700{index:06d}"[:20], f"client{index:04d}@example.com")
            for index in range(1, args.clients + 1)
        ]
        cursor.executemany(
            """
            INSERT INTO client (first_name, last_name, phone, email)
            VALUES (%s, %s, %s, %s)
            """,
            client_rows,
        )

        slots_per_hour = 4
        work_hours = 8
        slot_duration = timedelta(minutes=60 // slots_per_hour)
        slots_per_salon_day = slots_per_hour * work_hours
        active_salons_per_day = max(1, -(-args.target_slots // (args.days * slots_per_salon_day)))
        slot_rows: list[tuple] = []

        for day_index in range(args.days):
            current_day = start_date + timedelta(days=day_index)
            day_offset = (day_index * active_salons_per_day) % len(salon_ids)
            active_salons = [salon_ids[(day_offset + index) % len(salon_ids)] for index in range(active_salons_per_day)]

            for salon_id in active_salons:
                salon_hairdressers = hairdresser_map[salon_id]
                hairdresser_id = salon_hairdressers[day_index % len(salon_hairdressers)]
                start_dt = datetime.combine(current_day, time(9, 0))

                for slot_index in range(slots_per_salon_day):
                    slot_start = start_dt + slot_index * slot_duration
                    slot_end = slot_start + slot_duration
                    slot_rows.append((salon_id, hairdresser_id, slot_start, slot_end, "available"))
                    if len(slot_rows) >= args.target_slots:
                        break
                if len(slot_rows) >= args.target_slots:
                    break
            if len(slot_rows) >= args.target_slots:
                break

        chunked_insert(
            cursor,
            """
            INSERT INTO time_slot (salon_id, hairdresser_id, start_time, end_time, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            slot_rows,
            args.batch_size,
        )

        conn.commit()
        print(
            "Seed zakończony: "
            f"salony={len(salon_rows)}, fryzjerzy={len(hairdresser_rows)}, "
            f"uslugi={len(service_rows)}, klienci={len(client_rows)}, sloty={len(slot_rows)}"
        )

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()