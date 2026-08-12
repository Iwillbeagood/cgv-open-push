"""SubscriptionStore 의 SQLite 어댑터 — 서버 상시 실행용 영속 저장소."""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone

from cgv_push.domain import Subscription, SubscriptionDraft

_COLUMNS = (
    "id, site_no, site_nm, mov_no, mov_nm, start_date, end_date, "
    "slack_webhook_url, special_auditorium, alerted_dates, completed_at, created_at"
)


def _split(csv: str | None) -> frozenset[str]:
    return frozenset(d for d in (csv or "").split(",") if d)


def _row_to_subscription(row: sqlite3.Row) -> Subscription:
    return Subscription(
        id=str(row["id"]),
        site_no=row["site_no"],
        site_nm=row["site_nm"],
        mov_no=row["mov_no"],
        mov_nm=row["mov_nm"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        slack_webhook_url=row["slack_webhook_url"],
        special_auditorium=row["special_auditorium"],
        alerted_dates=_split(row["alerted_dates"]),
        completed_at=row["completed_at"],
        created_at=row["created_at"],
    )


class SqliteSubscriptionStore:
    def __init__(self, path: str) -> None:
        # 폴러 스레드와 FastAPI 스레드풀이 커넥션을 공유하므로 락으로 직렬화한다.
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_no TEXT NOT NULL,
                site_nm TEXT NOT NULL,
                mov_no TEXT NOT NULL,
                mov_nm TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                slack_webhook_url TEXT NOT NULL,
                special_auditorium TEXT,
                alerted_dates TEXT NOT NULL DEFAULT '',
                completed_at TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def add(self, draft: SubscriptionDraft) -> Subscription:
        created_at = datetime.now(timezone.utc).isoformat()
        alerted = ",".join(sorted(draft.alerted_dates))
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO subscriptions
                    (site_no, site_nm, mov_no, mov_nm, start_date, end_date,
                     slack_webhook_url, special_auditorium, alerted_dates, completed_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (draft.site_no, draft.site_nm, draft.mov_no, draft.mov_nm,
                 draft.start_date, draft.end_date, draft.slack_webhook_url,
                 draft.special_auditorium, alerted, created_at),
            )
            self._conn.commit()
            return self._get(str(cur.lastrowid))

    def _get(self, subscription_id: str) -> Subscription:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM subscriptions WHERE id = ?", (subscription_id,)
        ).fetchone()
        return _row_to_subscription(row)

    def list_all(self) -> list[Subscription]:
        with self._lock:
            rows = self._conn.execute(
                f"SELECT {_COLUMNS} FROM subscriptions ORDER BY id"
            ).fetchall()
        return [_row_to_subscription(r) for r in rows]

    def list_active(self) -> list[Subscription]:
        with self._lock:
            rows = self._conn.execute(
                f"SELECT {_COLUMNS} FROM subscriptions WHERE completed_at IS NULL ORDER BY id"
            ).fetchall()
        return [_row_to_subscription(r) for r in rows]

    def remove(self, subscription_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
            self._conn.commit()

    def record_alerted(self, subscription_id: str, dates: set[str]) -> None:
        with self._lock:
            row = self._conn.execute(
                "SELECT alerted_dates FROM subscriptions WHERE id = ?", (subscription_id,)
            ).fetchone()
            if row is None:
                return
            merged = _split(row["alerted_dates"]) | frozenset(dates)
            self._conn.execute(
                "UPDATE subscriptions SET alerted_dates = ? WHERE id = ?",
                (",".join(sorted(merged)), subscription_id),
            )
            self._conn.commit()

    def complete(self, subscription_id: str, when: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE subscriptions SET completed_at = ? WHERE id = ?",
                (when, subscription_id),
            )
            self._conn.commit()
