# CGV 예매 오픈 알리미 v2

특별관 상영의 예매가 열리는 순간을 감지해 Slack으로 알림을 보낸다. 리뉴얼된 CGV(Cloudflare 뒤)의 신규 API를 **Playwright**로 크롤링한다.

## 구조

```
v2/
├── backend/                # Python (FastAPI + Playwright)
│   └── src/cgv_push/
│       ├── domain.py          # 도메인 타입 (Site, Movie, Subscription)
│       ├── detector.py        # 오픈 감지 순수 로직 (is_due)
│       ├── ports.py           # seam 인터페이스 (Protocol)
│       ├── playwright_client.py  # CgvClient 실제 어댑터 (CF 우회)
│       ├── cgv_client.py      # FakeCgvClient (테스트)
│       ├── sqlite_store.py    # SubscriptionStore 실제 어댑터
│       ├── store.py           # InMemorySubscriptionStore (테스트)
│       ├── slack_notifier.py  # Notifier 실제 어댑터 (Slack Webhook)
│       ├── notifier.py        # RecordingNotifier (테스트)
│       ├── poller.py          # 오케스트레이션
│       ├── runner.py          # 폴링 백그라운드 루프
│       ├── api.py             # FastAPI (얇은 변환층)
│       ├── config.py          # 환경변수 설정
│       └── main.py            # 조립 루트
├── frontend/               # React (Vite) 설정 UI
├── Dockerfile              # 멀티스테이지 (프론트 빌드 → Playwright 백엔드)
└── docker-compose.yml
```

설계·결정은 [../docs/design.md](../docs/design.md), [../docs/spec.md](../docs/spec.md), [../docs/adr/](../docs/adr/), 용어는 [../CONTEXT.md](../CONTEXT.md) 참고.

## 동작 방식

1. 사용자가 웹에서 **극장 + 영화 + 상영일**과 Slack Webhook URL로 구독을 등록한다.
2. 백엔드가 주기적으로(기본 5분) 각 구독의 (극장, 영화)에 대해 CGV의 오픈된 상영일을 조회한다.
3. 구독한 상영일이 오픈 집합에 나타나면(그리고 아직 안 알렸으면) Slack으로 알림을 보낸다.

크롤링은 순수 HTTP로는 Cloudflare 403이라 Playwright(Chromium)로 JSON API를 호출한다 → [ADR-0001](../docs/adr/0001-playwright-for-cloudflare-bypass.md).

## 개발

```bash
# 백엔드 (레포 루트의 .venv 사용)
cd v2/backend
PYTHONPATH=src ../../.venv/bin/python -m pytest         # 테스트
PYTHONPATH=src ../../.venv/bin/python smoke_cgv.py       # 실제 CGV 스모크(수동)
PYTHONPATH=src ../../.venv/bin/python -m cgv_push.main   # 서버 (localhost:8000)

# 프론트엔드
cd v2/frontend
npm install
npm run dev        # localhost:5173, /api 는 :8000 으로 프록시
```

## 배포 (Docker)

```bash
cd v2
docker compose up --build
# http://localhost:8000  (빌드된 프론트 + API, 폴러 상시 구동)
```

환경변수: `CGV_POLL_INTERVAL`(초, 기본 300), `CGV_DB_PATH`, `CGV_HEADLESS`, `CGV_STATIC_DIR`.

## 알려진 한계

- 영화 목록은 현재 CGV가 반환하는 '예매 가능' 범위(극장별 필터 아님). 상영예정 영화 사전 구독은 후속 과제.
- 상영일 단위까지 감지(특정 회차/좌석 아님).
- Slack Webhook은 구독마다 사용자가 입력(공용 채널 방식으로 바꾸려면 구독 스키마에서 필드 제거).
