"""CgvClient 어댑터. (실제 Playwright 구현은 playwright_client.py)"""
from __future__ import annotations

from cgv_push.domain import Movie, Site


class FakeCgvClient:
    """인메모리 가짜 CGV — Poller/API 테스트용.

    open_dates: {(site_no, mov_no): set[YYYYMMDD]} 로 오픈 상태를 조작한다.
    fail_keys: 이 (site_no, mov_no) 조회는 예외를 던진다(견고성 테스트).
    """

    def __init__(
        self,
        sites: list[Site] | None = None,
        movies: dict[str, list[Movie]] | None = None,
        open_dates: dict[tuple[str, str], set[str]] | None = None,
    ) -> None:
        self._sites = sites or []
        self._movies = movies or {}
        self._open_dates = open_dates or {}
        self.fail_keys: set[tuple[str, str]] = set()

    def list_sites(self) -> list[Site]:
        return list(self._sites)

    def list_movies(self, site_no: str) -> list[Movie]:
        return list(self._movies.get(site_no, []))

    def list_open_dates(self, site_no: str, mov_no: str) -> set[str]:
        key = (site_no, mov_no)
        if key in self.fail_keys:
            raise RuntimeError(f"CGV 조회 실패(테스트): {key}")
        return set(self._open_dates.get(key, set()))

    # --- 테스트 편의 ---
    def set_open_dates(self, site_no: str, mov_no: str, dates: set[str]) -> None:
        self._open_dates[(site_no, mov_no)] = set(dates)
