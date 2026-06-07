from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Order:
    id: int
    customer_chat_id: int
    customer_user_id: int | None
    customer_username: str | None
    name: str
    phone: str
    screenshot_file_id: str
    status: str
    rejection_reason: str | None
    created_at: str
    updated_at: str


class OrderStore:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_chat_id INTEGER NOT NULL,
                    customer_user_id INTEGER,
                    customer_username TEXT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    screenshot_file_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    rejection_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create_order(
        self,
        *,
        customer_chat_id: int,
        customer_user_id: int | None,
        customer_username: str | None,
        name: str,
        phone: str,
        screenshot_file_id: str,
    ) -> Order:
        now = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO orders (
                    customer_chat_id,
                    customer_user_id,
                    customer_username,
                    name,
                    phone,
                    screenshot_file_id,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    customer_chat_id,
                    customer_user_id,
                    customer_username,
                    name,
                    phone,
                    screenshot_file_id,
                    now,
                    now,
                ),
            )
            order_id = int(cursor.lastrowid)
        return self.get_order(order_id)

    def get_order(self, order_id: int) -> Order:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            raise KeyError(f"Order not found: {order_id}")
        return _row_to_order(row)

    def set_status(self, order_id: int, status: str, rejection_reason: str | None = None) -> Order:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE orders
                SET status = ?, rejection_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, rejection_reason, _now(), order_id),
            )
        return self.get_order(order_id)

    def list_pending(self, limit: int = 20) -> list[Order]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM orders
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_to_order(row) for row in rows]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _row_to_order(row: sqlite3.Row) -> Order:
    return Order(
        id=row["id"],
        customer_chat_id=row["customer_chat_id"],
        customer_user_id=row["customer_user_id"],
        customer_username=row["customer_username"],
        name=row["name"],
        phone=row["phone"],
        screenshot_file_id=row["screenshot_file_id"],
        status=row["status"],
        rejection_reason=row["rejection_reason"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
