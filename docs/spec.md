# Spec — CGV 예매 오픈 알리미 (v2)

> 이슈 트래커 미정(`docs/agents/issue-tracker.md`)이라 트래커 대신 이 파일에 발행한다. 트래커 확정 후 옮기고 `ready-for-agent` 라벨을 적용한다. 용어는 [CONTEXT.md](../CONTEXT.md), 설계는 [docs/design.md](./design.md), 결정은 [docs/adr/](./adr/)를 따른다.

## Problem Statement

CGV 특별관(IMAX·4DX·SCREENX 등)은 인기 상영일의 예매가 열리자마자 매진된다. 사용자는 원하는 극장·영화·상영일의 예매가 정확히 언제 열리는지 알 수 없어 수시로 CGV를 새로고침해야 한다. 게다가 CGV 리뉴얼로 기존 알리미(v1)가 쓰던 API가 폐기되어 더는 동작하지 않는다.

## Solution

사용자가 웹 페이지에서 **극장 + 영화 + 상영일**을 골라 구독을 등록하면, 서버가 CGV를 주기적으로 관찰하다가 그 조합의 예매가 오픈되는 순간 Slack으로 알림을 보낸다. 크롤링은 Cloudflare 뒤의 신규 CGV API를 Playwright로 호출해 이뤄진다.

## User Stories

1. 사용자로서, 특별관이 있는 극장 목록을 보고 싶다, 그래야 관심 극장을 고를 수 있다.
2. 사용자로서, 선택한 극장의 영화 목록을 보고 싶다, 그래야 볼 영화를 고를 수 있다.
3. 사용자로서, 원하는 상영일을 달력에서 고르고 싶다, 그래야 아직 열리지 않은 날짜의 오픈을 기다릴 수 있다.
4. 사용자로서, 극장·영화·상영일 조합으로 구독을 등록하고 싶다, 그래야 그 예매가 열릴 때 알림을 받는다.
5. 사용자로서, 내 Slack 채널의 webhook URL을 입력하고 싶다, 그래야 내가 지정한 채널로 알림이 온다.
6. 사용자로서, 등록한 구독 목록을 보고 싶다, 그래야 무엇을 기다리는지 확인한다.
7. 사용자로서, 구독을 삭제하고 싶다, 그래야 더는 필요 없는 알림을 끈다.
8. 사용자로서, 구독한 상영일의 예매가 오픈되면 Slack 메시지를 받고 싶다, 그래야 즉시 예매하러 간다.
9. 사용자로서, 같은 오픈에 대해 중복 알림을 받지 않고 싶다, 그래야 스팸이 되지 않는다.
10. 사용자로서, 알림 메시지에 극장·영화·상영일·(가능하면 예매 링크)이 담기길 원한다, 그래야 바로 행동한다.
11. 운영자로서, 크롤링이 CGV 오류/차단으로 실패해도 서비스가 죽지 않길 원한다, 그래야 알림이 계속 동작한다.
12. 운영자로서, 서버를 Docker로 상시 실행하고 싶다, 그래야 배포·운영이 단순하다.
13. 운영자로서, 폴링 주기를 설정으로 바꾸고 싶다, 그래야 부하와 반응성을 조절한다.

## Implementation Decisions

- **모듈**(= [docs/design.md](./design.md)): `CgvClient`(유일한 외부 seam, Playwright), `OpenDetector`(순수 함수), `SubscriptionStore`(SQLite), `Notifier`(Slack webhook), `Poller`(오케스트레이션), `Web API`(FastAPI), `React 웹`.
- **오픈 감지**: 상영일 집합의 스냅샷 비교. `current - previous`로 새로 등장한 상영일을 오픈으로 판정(순수 함수). 수량 증가가 아닌 '새 날짜 등장'이 기준.
- **CGV 접근**: 순수 HTTP는 Cloudflare 403 → Playwright Chromium 필수(ADR-0001). 렌더링 없이 `context.request.get()`으로 JSON API만 호출.
- **API 계약**(신규 CGV, 전부 `coCd=A420`):
  - 극장: `content/site/searchAllRegionAndSite`
  - 특별관 판별: `booking/searchSscnsSchdExistList?siteNo=` (해당 극장의 특별관 등급/상영일정 수)
  - 영화별 오픈 상영일: `booking/searchSiteScnscYmdListByMov?siteNo=&movNo=`
  - 영화 목록: `booking/searchAtktTopPostrList`
- **구독 스키마**: `id, site_no, site_nm, mov_no, mov_nm, special_auditorium, screening_date(YYYYMMDD), slack_webhook_url, notified_at?, created_at`.
- **중복 방지**: 알림 후 `notified_at` 기록, 이미 알린 구독은 재알림하지 않음.
- **주입**: `Poller`는 4개 의존성을 주입받는다(생성 X) → 가짜로 전 구간 테스트.
- **배포**: Chromium 포함 Docker 이미지, 상시 실행. 폴링 주기는 env(기본 5분).

## Testing Decisions

- **외부 행동만 테스트**한다(구현 세부 X). 관찰 지점은 인터페이스.
- `OpenDetector`: 순수 함수 → mock 없이 입출력 테스트(가장 촘촘히). 케이스: 새 날짜 등장, 변화 없음, 날짜 사라짐(오픈 아님), 최초 스냅샷.
- `Poller`: `FakeCgvClient` + `InMemorySubscriptionStore` + `RecordingNotifier` 주입 → 네트워크·Slack 없이 "오픈되면 정확히 한 번 알림" 검증. 중복 방지, 매칭 정확도(다른 극장·영화·날짜엔 알림 없음) 포함.
- `SubscriptionStore`: 인메모리 계약 테스트를 SQLite에도 동일 적용(계약 테스트).
- `Web API`: FastAPI TestClient로 라우팅·검증, `FakeCgvClient` 주입.
- `PlaywrightCgvClient`: 실제 네트워크 의존이라 단위테스트 대상 아님. 별도 수동/통합 스크립트로 스모크 확인.
- 프론트엔드: v1 범위에선 핵심 로직 위주, E2E는 후순위.

## Out of Scope

- 아직 CGV에 등록되지 않은 '상영예정' 영화의 사전 구독(영화 목록은 현재 CGV가 반환하는 범위). 후속 확장.
- 좌석 단위/특정 회차(시간) 알림 — 상영일 단위까지만.
- 사용자 인증·계정 시스템(구독은 webhook URL로 자기완결).
- 결제/자동 예매.
- 특별관 외 일반관.

## Further Notes

- v1(`v1/`)은 폐기된 구 API 기반이라 보존만 하고 참조하지 않는다.
- 신규 API 상세는 메모리 `cgv-new-api`에 기록됨.
- 열린 질문(설계 §열린 설계 질문): 상영예정 영화 선택, webhook 위치(구독별 vs 공용), 폴링 주기 최적화.
