# CGV 예매 오픈 알리미

특별관(IMAX·4DX·SCREENX 등) 상영의 **예매가 열리는 순간을 감지**해 Slack으로 알려주는 서비스.
원하는 극장·영화·상영일을 구독해두면, 백엔드가 주기적으로 CGV를 확인하다가 예매가 오픈되면 알림을 보낸다.

> 리뉴얼된 CGV는 Cloudflare 뒤의 신규 API를 쓴다. 순수 HTTP로는 403이 떠서 **Playwright(Chromium)** 로 JSON API를 호출해 크롤링한다. → [ADR-0001](docs/adr/0001-playwright-for-cloudflare-bypass.md)

## 동작 방식

1. 사용자가 웹 UI에서 **극장 + 영화 + 상영일**과 **Slack Webhook URL**로 구독을 등록한다.
   - 등록 즉시 Slack으로 "구독이 시작되었어요" 안내가 간다.
2. 백엔드 폴러가 주기적으로(기본 5분) 각 구독의 (극장, 영화)에 대해 CGV의 오픈된 상영일을 조회한다.
3. 구독한 상영일이 오픈 집합에 나타나면(그리고 아직 안 알렸으면) **Slack으로 예매 오픈 알림**을 보낸다.

## 구조

```
.
├── v2/                       # 현재 버전 (신규 CGV API 대응)
│   ├── backend/              # Python (FastAPI + Playwright)
│   │   └── src/cgv_push/
│   │       ├── domain.py           # 도메인 타입 (Site, Movie, Subscription)
│   │       ├── detector.py         # 오픈 감지 순수 로직
│   │       ├── ports.py            # seam 인터페이스 (Protocol)
│   │       ├── playwright_client.py  # CgvClient 실제 어댑터 (Cloudflare 우회)
│   │       ├── sqlite_store.py     # SubscriptionStore 실제 어댑터
│   │       ├── slack_notifier.py   # Notifier 실제 어댑터 (Slack Webhook)
│   │       ├── poller.py           # 오케스트레이션
│   │       ├── runner.py           # 폴링 백그라운드 루프
│   │       ├── api.py              # FastAPI (얇은 변환층)
│   │       └── main.py             # 조립 루트
│   ├── frontend/             # React (Vite) 설정 UI
│   ├── Dockerfile            # 멀티스테이지 (프론트 빌드 → Playwright 백엔드)
│   ├── docker-compose.yml
│   └── DEPLOY.md             # 배포 가이드 (Oracle Cloud 무료 VM)
├── docs/                     # 설계·스펙·ADR
└── CONTEXT.md                # 도메인 용어(ubiquitous language)
```

설계는 헥사고날(포트/어댑터) 구조다. 순수 로직(`detector`)과 외부 의존성(`playwright_client`, `sqlite_store`, `slack_notifier`)을 `ports.py`의 seam으로 분리해, 테스트에서는 Fake 어댑터를 주입한다.

## 개발

```bash
# 백엔드
cd v2/backend
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=src ./.venv/bin/python -m pytest          # 테스트
PYTHONPATH=src ./.venv/bin/python -m cgv_push.main    # 서버 (localhost:8000)

# 프론트엔드
cd v2/frontend
npm install
npm run dev        # localhost:5173, /api 는 :8000 으로 프록시
```

## 배포 (Docker)

```bash
cd v2
docker compose up -d --build
# http://localhost:8000  (빌드된 프론트 + API, 폴러 상시 구동)
```

Oracle Cloud 무료 VM에 상시 배포하는 방법은 [v2/DEPLOY.md](v2/DEPLOY.md) 참고.

### 환경변수 / 빌드 인자

| 이름 | 위치 | 설명 |
|------|------|------|
| `CGV_POLL_INTERVAL` | 런타임 | 폴링 주기(초, 기본 300) |
| `CGV_DB_PATH` | 런타임 | SQLite 경로 |
| `CGV_HEADLESS` | 런타임 | Chromium 헤드리스 여부 |
| `CGV_STATIC_DIR` | 런타임 | 빌드된 프론트 정적 파일 경로 |
| `VITE_DEFAULT_WEBHOOK` | 빌드 | (선택) 웹훅 입력칸 기본값. 빌드 시에만 주입되며 저장소엔 남지 않는다 |

## 알려진 한계

- 영화 목록은 CGV가 반환하는 '예매 가능' 범위(극장별 필터 아님).
- 상영일 단위까지 감지(특정 회차/좌석 아님).
- Slack Webhook은 구독마다 사용자가 입력한다.

## 라이선스

개인 프로젝트. 별도 명시 없으면 참고용.
