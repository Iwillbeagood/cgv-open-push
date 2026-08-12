# CGV API 호출에 순수 HTTP 대신 Playwright(headless Chromium)를 사용한다

신규 CGV API(`cgv.co.kr/api/v1/...`)는 Cloudflare 봇 차단 뒤에 있어 `requests`/`curl` 등 순수 HTTP 클라이언트는 HTTP 403으로 막힌다(2026-08 검증). Playwright의 실제 Chromium 네트워크 스택으로 호출하면 쿠키 없이도 200으로 통과한다. 따라서 크롤링은 상시 headless Chromium 1개를 띄우고 `context.request.get()`으로 JSON API만 호출한다(페이지 렌더링·클릭 불필요).

## Considered Options

- **순수 `requests`/`httpx`** — 가장 가볍지만 Cloudflare에 403. TLS 지문·JS 챌린지를 우회할 수 없어 탈락.
- **`curl_cffi` 등 TLS 임퍼소네이션 라이브러리** — 브라우저 없이 통과 가능성이 있으나 Cloudflare 정책 변경에 취약하고 검증되지 않음. 향후 경량화가 필요하면 재검토 대상.
- **Playwright(채택)** — 무겁지만(Chromium ~100MB+, 메모리) 가장 확실하게 통과. 렌더링 없이 request 클라이언트만 쓰면 비용이 낮다.

## Consequences

- Docker 이미지에 Chromium 의존성이 포함되어 이미지가 커지고 메모리 사용이 늘어난다.
- 크롤러는 브라우저 컨텍스트 수명주기(기동/재기동)를 관리해야 한다.
- 순수 HTTP가 아니므로 CGV API 호출은 반드시 이 seam(브라우저 컨텍스트)을 거친다 — 이 지점이 전체 시스템의 외부 의존성 seam이 된다.
