# Context

CGV 예매 오픈 알리미. CGV의 예매 정보를 주기적으로 관찰하여, 사용자가 지정한 상영의 예매가 새로 열리는 순간을 감지해 알림을 보낸다. 이 파일은 이 프로젝트의 유비쿼터스 언어(용어집)이며 구현 세부는 담지 않는다.

## Language

### 예매 대상

**극장 (Site)**:
CGV의 물리적 상영 지점. CGV가 부여한 사이트번호(siteNo)로 식별한다.
_Avoid_: 지점, 영화관, theater, cinema, branch

**특별관 (Special Auditorium)**:
IMAX·4DX·SCREENX·DOLBY ATMOS·ULTRA 4DX 등 프리미엄 상영 등급. 이 서비스가 다루는 관심 대상이며, 일반관은 대상이 아니다.
_Avoid_: 상영관, 관, 스크린, format, screen, auditorium(단독)

**영화 (Movie)**:
한 극장의 특별관에서 상영되는 작품. CGV가 부여한 영화번호(movNo)로 식별한다.
_Avoid_: 작품, 콘텐츠, title, film

**상영일 (Screening Date)**:
특정 극장에서 상영일정이 존재하는 하나의 날짜(YYYYMMDD).
_Avoid_: 날짜, 일자, day, playdate

**상영일정 (Schedule)**:
한 극장이 특정 특별관/영화/상영일에 대해 예매 가능하게 열어둔 회차의 집합.
_Avoid_: 스케줄, 타임테이블, 편성, showtime(단건), timetable

### 오픈 감지

**오픈 (Open)**:
어떤 상영일정이 예매 가능한 상태로 새로 공개되는 사건. 이 서비스가 사용자에게 알리려는 바로 그 순간.
_Avoid_: 오픈런, 발매, 티켓팅, release, launch

**스냅샷 (Snapshot)**:
한 시점에 극장에서 관찰한 상영일(및 특별관별 상영일정 수)의 집합. 오픈 감지는 두 스냅샷의 비교로 이루어진다.
_Avoid_: 캡처, 상태, capture, state

**오픈 감지 (Open Detection)**:
직전 스냅샷 대비 새 상영일이 나타난 것을 오픈으로 간주해 판정하는 것. (수량 증가가 아니라 '새로 등장'이 기준.)
_Avoid_: 변동 감지, 폴링, diff, change detection

### 알림

**구독 (Subscription)**:
사용자가 등록한 하나의 알림 조건. 극장 + 영화 + 상영일의 조합이며, 그 조합의 예매가 오픈되면 알림을 받는다.
_Avoid_: 알림설정, 구독설정, watch, alert rule

**알림 (Alert)**:
구독의 대상이 오픈되었을 때 Slack으로 전송되는 메시지.
_Avoid_: 푸시, 노티, 통지, push, notification
