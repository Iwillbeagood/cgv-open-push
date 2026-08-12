"""CgvClient 의 실제 어댑터 — Playwright(Chromium)로 신규 CGV API 호출 (ADR-0001).

스레드 안전성: Playwright sync 객체는 생성 스레드에 묶인다. FastAPI 스레드풀과
Poller 스레드가 공유해도 안전하도록, 전용 단일 워커 스레드가 브라우저를 소유하고
모든 호출을 그 스레드로 마샬링한다(ThreadPoolExecutor max_workers=1).
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from cgv_push.domain import Movie, Site

logger = logging.getLogger(__name__)

CO_CD = "A420"
BASE = "https://cgv.co.kr/api/v1"
BOOKING_URL = "https://cgv.co.kr/cnm/movieBook/cinema"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _poster_url(mov_no: str, i320_fnm: str | None) -> str | None:
    """CGV 포스터 CDN URL 조립. 예: 30001192 -> .../Poster/030001/30001192/30001192_320.jpg"""
    if not i320_fnm:
        return None
    try:
        group = f"{int(mov_no) // 1000:06d}"
    except ValueError:
        return None
    return f"https://cdn.cgv.co.kr/cgvpomsfilm/Movie/Thumbnail/Poster/{group}/{mov_no}/{i320_fnm}"


class PlaywrightCgvClient:
    def __init__(self, headless: bool = True) -> None:
        self._headless = headless
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cgv-pw")
        self._pw = None
        self._browser = None
        self._ctx = None
        self._executor.submit(self._start).result()

    # --- 워커 스레드에서만 실행되는 내부 메서드 ---
    def _start(self) -> None:
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self._headless)
        self._ctx = self._browser.new_context(user_agent=USER_AGENT, locale="ko-KR")
        # Cloudflare 통과를 위해 예매 페이지를 한 번 방문(쿠키/세션 확보).
        page = self._ctx.new_page()
        try:
            page.goto(BOOKING_URL, wait_until="domcontentloaded", timeout=45000)
        finally:
            page.close()

    def _get_data(self, path: str, **params: str) -> Any:
        query = "&".join([f"coCd={CO_CD}"] + [f"{k}={v}" for k, v in params.items()])
        url = f"{BASE}/{path}?{query}"
        resp = self._ctx.request.get(url, headers={"Referer": BOOKING_URL}, timeout=20000)
        body = json.loads(resp.text())
        # statusCode 는 보통 int 0 이지만, 문자열 "0" 로 올 수도 있어 방어적으로 허용.
        if body.get("statusCode") not in (0, "0", None):
            raise RuntimeError(f"CGV API 오류 {body.get('statusCode')}: {body.get('statusMessage')} ({url})")
        return body.get("data")

    def _list_sites(self) -> list[Site]:
        # 특별관 등급별 보유 극장(sscnsSiteList)을 뒤집어 극장 -> 특별관들로 집계하고,
        # searchAllRegionAndSite 로 각 극장의 지역(regnGrpCd)과 지역명을 붙인다.
        data = self._get_data("booking/searchSscnsSchdCntList") or []
        names: dict[str, str] = {}                     # site_no -> site_nm
        auditoriums: dict[str, list[str]] = {}         # site_no -> [특별관명...]
        for grade in data:
            grade_nm = grade.get("comCdvalNm")
            for site in grade.get("sscnsSiteList") or []:
                site_no, site_nm = site.get("siteNo"), site.get("siteNm")
                if not site_no or not site_nm:
                    continue
                names[site_no] = site_nm
                if grade_nm and grade_nm not in auditoriums.setdefault(site_no, []):
                    auditoriums[site_no].append(grade_nm)

        region_of, region_name = self._region_index()
        sites = [
            Site(
                site_no, site_nm, tuple(auditoriums.get(site_no, [])),
                region_code=region_of.get(site_no, ""),
                region_name=region_name.get(region_of.get(site_no, ""), "기타"),
            )
            for site_no, site_nm in names.items()
        ]
        return sorted(sites, key=lambda s: s.site_no)

    def _region_index(self) -> tuple[dict[str, str], dict[str, str]]:
        """searchAllRegionAndSite -> (site_no->지역코드, 지역코드->지역명)."""
        data = self._get_data("content/site/searchAllRegionAndSite") or {}
        region_name = {
            r["comCdval"]: r.get("comCdvalNm", "")
            for r in (data.get("regionInfo") or []) if r.get("comCdval")
        }
        region_of = {
            s["siteNo"]: s.get("regnGrpCd", "")
            for s in (data.get("siteInfo") or []) if s.get("siteNo")
        }
        return region_of, region_name

    def _list_movies(self, site_no: str) -> list[Movie]:
        # searchAtktTopPostrList 는 현재 예매 가능한 영화 목록(+포스터 파일명)을 반환한다.
        data = self._get_data("booking/searchAtktTopPostrList", movNm="", div="", attrCd="") or []
        movies: dict[str, Movie] = {}
        for m in data:
            mov_no = m.get("movNo") or m.get("movieNo") or m.get("movGrpCd") or m.get("movCd")
            mov_nm = m.get("movNm") or m.get("movieNm") or m.get("movNmKor")
            if mov_no and mov_nm and str(mov_no) not in movies:
                movies[str(mov_no)] = Movie(str(mov_no), mov_nm, _poster_url(str(mov_no), m.get("i320Fnm")))
        return list(movies.values())

    def _list_open_dates(self, site_no: str, mov_no: str) -> set[str]:
        data = self._get_data(
            "booking/searchSiteScnscYmdListByMov", siteNo=site_no, movNo=mov_no
        ) or []
        return {row["scnYmd"] for row in data if row.get("scnYmd")}

    def _stop(self) -> None:
        if self._ctx is not None:
            self._ctx.close()
        if self._browser is not None:
            self._browser.close()
        if self._pw is not None:
            self._pw.stop()

    # --- 공개 인터페이스(모든 스레드에서 호출 가능) ---
    def list_sites(self) -> list[Site]:
        return self._executor.submit(self._list_sites).result()

    def list_movies(self, site_no: str) -> list[Movie]:
        return self._executor.submit(self._list_movies, site_no).result()

    def list_open_dates(self, site_no: str, mov_no: str) -> set[str]:
        return self._executor.submit(self._list_open_dates, site_no, mov_no).result()

    def close(self) -> None:
        self._executor.submit(self._stop).result()
        self._executor.shutdown(wait=True)
