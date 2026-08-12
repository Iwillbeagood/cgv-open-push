# CGV 예매 오픈 알리미

CGV 예매 정보를 주기적으로 크롤링해, 특정 상영(특별관·영화·날짜)의 예매가 열리면 알림을 보내는 서비스.

- 구 버전(`v1/`)은 CGV 리뉴얼 이전의 내부 API(`ticket.cgv.co.kr`)를 `requests` + `diff_match_patch`로 폴링해 Discord로 알림. 리뉴얼로 해당 엔드포인트가 폐기되어 **더 이상 동작하지 않음**.
- 신규 버전은 Cloudflare 뒤의 새 CGV API(`cgv.co.kr/api/v1/...`)를 **Playwright(Chromium)**로 호출해 크롤링하고, **Slack**으로 알림 예정. 설정 UI는 React 웹 페이지.

## Agent skills

### Issue tracker

**미정 (추후 결정).** 정해지면 `docs/agents/issue-tracker.md`를 채우거나 `/setup-matt-pocock-skills` 재실행. 자세한 후보는 `docs/agents/issue-tracker.md`.

### Triage labels

캐노니컬 기본 라벨 5종을 그대로 사용(`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

단일 컨텍스트(single-context) — 루트 `CONTEXT.md` + `docs/adr/`. See `docs/agents/domain.md`.
