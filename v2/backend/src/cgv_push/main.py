"""조립 루트(composition root) — 실제 어댑터를 배선하고 API + 폴러를 구동한다."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi.staticfiles import StaticFiles

from cgv_push.api import create_app
from cgv_push.config import Config
from cgv_push.playwright_client import PlaywrightCgvClient
from cgv_push.poller import Poller
from cgv_push.runner import PollerLoop
from cgv_push.slack_notifier import SlackWebhookNotifier
from cgv_push.sqlite_store import SqliteSubscriptionStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def build_app(config: Config | None = None):
    config = config or Config.from_env()
    cgv = PlaywrightCgvClient(headless=config.headless)
    store = SqliteSubscriptionStore(config.db_path)
    notifier = SlackWebhookNotifier()
    poller = Poller(
        cgv=cgv, store=store, notifier=notifier,
        clock=lambda: datetime.now(timezone.utc).isoformat(),
    )
    loop = PollerLoop(poller, interval_seconds=config.poll_interval_seconds)

    @asynccontextmanager
    async def lifespan(app):
        logger.info("폴러 시작 (주기 %ss)", config.poll_interval_seconds)
        loop.start()
        try:
            yield
        finally:
            logger.info("종료: 폴러/브라우저 정리")
            loop.stop()
            cgv.close()

    app = create_app(cgv=cgv, store=store, notifier=notifier)
    app.router.lifespan_context = lifespan

    if config.static_dir:
        # 빌드된 React 정적 파일 서빙 (SPA fallback 포함)
        app.mount("/", StaticFiles(directory=config.static_dir, html=True), name="static")

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(build_app(), host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
