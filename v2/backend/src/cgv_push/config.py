"""환경변수 기반 설정."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    db_path: str
    poll_interval_seconds: int
    headless: bool
    static_dir: str | None  # 빌드된 React 정적 파일 경로(없으면 API만)

    @staticmethod
    def from_env() -> "Config":
        return Config(
            db_path=os.environ.get("CGV_DB_PATH", "cgv_push.db"),
            poll_interval_seconds=int(os.environ.get("CGV_POLL_INTERVAL", "300")),
            headless=os.environ.get("CGV_HEADLESS", "1") != "0",
            static_dir=os.environ.get("CGV_STATIC_DIR") or None,
        )
