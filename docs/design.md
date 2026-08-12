# 설계 — CGV 예매 오픈 알리미 (v2)

`codebase-design` 원칙(deep module, 작은 interface, 하나의 seam)으로 설계한다. 용어는 [CONTEXT.md](../CONTEXT.md)를 따른다.

## 전체 흐름

```
[React 웹]  --HTTP-->  [Web API]  ---->  [SubscriptionStore]  (구독 저장)
   구독 생성            (FastAPI)  ---->  [CgvClient]          (선택지 조회)

[Poller] (주기 루프)
   ├─ SubscriptionStore.list_active()      활성 구독 읽기
   ├─ CgvClient.list_open_dates(극장,영화)  현재 오픈된 상영일 조회
   ├─ OpenDetector.detect(이전, 현재)       새로 열린 상영일 판정 (순수 함수)
   └─ Notifier.notify(구독, 오픈)           Slack 알림 전송
```

## 모듈과 인터페이스

### 1. CgvClient — 유일한 외부 의존성 seam (ADR-0001)

CGV 신규 API를 Playwright로 호출하는 것을 전부 숨긴다. **이 프로젝트의 유일한 핵심 seam**: Poller와 Web API는 이 인터페이스만 알고, 테스트는 이 seam에서 가짜 CGV로 갈아끼운다.

Interface (호출자가 알아야 하는 전부):
- `list_sites() -> list[Site]` — 특별관을 보유한 극장만. (일반관 전용 극장은 제외.)
- `list_movies(site) -> list[Movie]` — 그 극장에서 선택 가능한 영화.
- `list_open_dates(site, movie) -> set[ScreeningDate]` — 그 극장·영화에 현재 예매 오픈된 상영일 집합.
- 제약: 호출은 비동기, 네트워크 실패 시 예외를 던진다(호출자가 재시도). coCd·엔드포인트·Cloudflare 우회는 인터페이스에 드러나지 않는다.

Implementation (deep): Playwright Chromium 수명주기, CF 우회, `coCd=A420`, 엔드포인트(`searchSscnsSchdExistList`/`searchSiteScnscYmdListByMov`/`searchAllRegionAndSite`/`searchAtktTopPostrList`), JSON 파싱·재시도.

Adapters (seam이 실재함 — 2개):
- `PlaywrightCgvClient` — 실제 (얕은 adapter, 깊은 구현)
- `FakeCgvClient` — 인메모리 (깊은 adapter, 얕은 구현). Poller·API 테스트용.

### 2. OpenDetector — 순수 도메인 로직 (seam 없음)

오픈 감지 규칙을 담은 **순수 함수**. I/O가 없어 mock 없이 직접 테스트한다. 시스템의 핵심 로직이자 가장 테스트하기 쉬운 지점.

Interface:
- `detect(previous: set[ScreeningDate], current: set[ScreeningDate]) -> set[ScreeningDate]`
- 규칙: `current - previous` (직전에 없던 상영일이 새로 등장 = 오픈). 수량 증가가 아니라 '새 날짜 등장'이 기준(CONTEXT: 오픈 감지).

### 3. SubscriptionStore — 저장 seam

Interface:
- `add(draft) -> Subscription`
- `list_active() -> list[Subscription]`
- `remove(id) -> None`
- `mark_notified(id) -> None` — 알림 후 재알림 방지
- `get_last_open_dates(site, movie) -> set[ScreeningDate]` / `save_open_dates(site, movie, dates)` — 스냅샷 보관

Adapters: `SqliteSubscriptionStore`(실제) + `InMemorySubscriptionStore`(테스트).

### 4. Notifier — Slack seam

Interface:
- `notify(subscription, opened: set[ScreeningDate]) -> None` — 부수효과: Slack Incoming Webhook POST.

Adapters: `SlackWebhookNotifier`(실제) + `RecordingNotifier`(테스트, 보낸 메시지 기록).

### 5. Poller — 오케스트레이션

의존성을 **주입받는다**(생성하지 않음): `Poller(cgv, store, detector, notifier)`. 주기 루프에서 활성 구독을 극장·영화로 묶어 CgvClient를 최소 호출하고, OpenDetector로 새 상영일을 판정해 해당 구독에 Notifier로 알린다. 가짜 4종을 주입하면 네트워크·Slack 없이 전 구간 테스트된다.

### 6. Web API (FastAPI) — 얇은 adapter

- `GET  /api/sites` → 특별관 보유 극장
- `GET  /api/sites/{siteNo}/movies` → 영화 목록
- `GET  /api/sites/{siteNo}/movies/{movNo}/open-dates` → 현재 오픈된 상영일 (참고용 표시)
- `POST /api/subscriptions` → 구독 생성 (극장+영화+상영일+Slack webhook URL)
- `GET  /api/subscriptions` / `DELETE /api/subscriptions/{id}`

CgvClient·SubscriptionStore 위의 얇은 변환층. 로직은 두지 않는다.

### 7. React 웹 — 설정 UI

극장 선택 → 영화 선택 → 상영일 선택 → Slack webhook URL 입력 → 구독 생성. 단순 폼.

## Seam 요약

- **주 seam = CgvClient** 하나. 전체 시스템이 이 지점에서 가짜 CGV로 테스트된다(to-spec: 이상적 seam 수 = 1).
- OpenDetector는 순수 → seam 불필요, 직접 테스트.
- SubscriptionStore·Notifier는 Poller 테스트를 위한 보조 seam.

## 데이터 모델

- **Subscription**: `id`, `site_no`, `site_nm`, `mov_no`, `mov_nm`, `special_auditorium`, `screening_date`(YYYYMMDD), `slack_webhook_url`, `notified_at`(nullable), `created_at`.
- **스냅샷**: `(site_no, mov_no) → set[screening_date]` 최근값.

## 열린 설계 질문 (구현 중 확정)

1. **아직 오픈되지 않은 상영일/영화 선택**: 알림의 목적은 '아직 안 열린' 상영을 기다리는 것이므로, 상영일은 오픈된 목록이 아니라 **달력에서 자유 선택**해야 한다. 영화는 CGV 영화 목록(현재 예매가능 + 가능하면 상영예정)에서 선택. 상영예정 영화 목록 엔드포인트는 구현 중 확인 필요.
2. **Slack webhook 위치**: 구독마다 사용자가 자신의 채널 webhook URL을 입력(멀티유저 웹폼 전제). 공용 단일 채널로 바꾸면 구독에서 필드 제거.
3. **폴링 주기**: 기본 5분(v1과 동일). 오픈 임박 시간대만 촘촘히 하는 최적화는 후순위.
