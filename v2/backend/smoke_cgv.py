"""실제 CGV에 대한 PlaywrightCgvClient 스모크 (수동 실행). 유닛테스트 아님."""
import sys

sys.path.insert(0, "src")
from cgv_push.playwright_client import PlaywrightCgvClient  # noqa: E402

c = PlaywrightCgvClient(headless=True)
try:
    sites = c.list_sites()
    print(f"[list_sites] 특별관 보유 극장 {len(sites)}개")
    for s in sites[:8]:
        print(f"   {s.site_no} {s.site_nm} :: {s.special_auditoriums}")

    yongsan = next((s for s in sites if s.site_no == "0013"), sites[0])
    print(f"\n[대상] {yongsan.site_no} {yongsan.site_nm}")

    movies = c.list_movies(yongsan.site_no)
    print(f"[list_movies] {len(movies)}편")
    for m in movies[:6]:
        print(f"   movNo={m.mov_no}  {m.mov_nm}")

    if movies:
        dates = c.list_open_dates(yongsan.site_no, movies[0].mov_no)
        print(f"\n[list_open_dates] {yongsan.site_nm} × {movies[0].mov_nm}: {len(dates)}일")
        print("   ", sorted(dates)[:12])
finally:
    c.close()
    print("\n[closed]")
