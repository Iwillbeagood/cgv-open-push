import { useEffect, useState } from "react";
import { api, fromYmd, posterUrlOf } from "./api.js";
import Calendar from "./Calendar.jsx";

export default function App() {
  const [regions, setRegions] = useState([]);
  const [regionCode, setRegionCode] = useState("");
  const [siteNo, setSiteNo] = useState("");
  const [movies, setMovies] = useState([]);
  const [movNo, setMovNo] = useState("");
  const [openDates, setOpenDates] = useState(null);
  const [startYmd, setStartYmd] = useState("");
  const [endYmd, setEndYmd] = useState("");
  // 웹훅은 소스에 두지 않고 브라우저(localStorage)에 기억시킨다.
  // 저장된 값이 없으면 빌드 시 주입된 기본 웹훅(VITE_DEFAULT_WEBHOOK)을 사용한다.
  const [webhook, setWebhook] = useState(
    () => localStorage.getItem("cgv_webhook") || import.meta.env.VITE_DEFAULT_WEBHOOK || ""
  );
  const [subs, setSubs] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [moviesState, setMoviesState] = useState("idle"); // idle | loading | error
  const [slowLoad, setSlowLoad] = useState(false);

  useEffect(() => {
    api
      .listRegions()
      .then((rs) => {
        setRegions(rs);
        if (rs[0]) setRegionCode(rs[0].code);
      })
      .catch(() => setError("극장 목록을 불러오지 못했습니다."));
    refreshSubs();
  }, []);

  const refreshSubs = () => api.listSubscriptions().then(setSubs).catch(() => {});

  // 입력한 웹훅을 브라우저에 기억
  useEffect(() => {
    if (webhook) localStorage.setItem("cgv_webhook", webhook);
  }, [webhook]);

  const region = regions.find((r) => r.code === regionCode);
  const sites = region ? region.sites : [];
  const site = sites.find((s) => s.siteNo === siteNo);

  // 영화 목록 로드(재시도 가능). CGV 크롤링이라 느릴 수 있어 로딩/오류 상태를 구분한다.
  const loadMovies = () => {
    if (!siteNo) return;
    setMovies([]);
    setMovNo("");
    setError("");
    setMoviesState("loading");
    setSlowLoad(false);
    const slowTimer = setTimeout(() => setSlowLoad(true), 8000);
    api
      .listMovies(siteNo)
      .then((ms) => {
        setMovies(ms);
        setMoviesState("idle");
      })
      .catch(() => setMoviesState("error"))
      .finally(() => clearTimeout(slowTimer));
  };

  useEffect(() => {
    setOpenDates(null);
    setStartYmd("");
    setEndYmd("");
    if (!siteNo) {
      setMovies([]);
      setMovNo("");
      setMoviesState("idle");
      return;
    }
    loadMovies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteNo]);

  useEffect(() => {
    setOpenDates(null);
    setStartYmd("");
    setEndYmd("");
    if (!siteNo || !movNo) return;
    api.listOpenDates(siteNo, movNo).then(setOpenDates).catch(() => {});
  }, [siteNo, movNo]);

  const movie = movies.find((m) => m.movNo === movNo);
  const isRange = startYmd && endYmd && startYmd !== endYmd;

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!site || !movie) {
      setError("극장과 영화를 먼저 선택해주세요.");
      return;
    }
    if (!startYmd) {
      setError("상영일을 선택해주세요.");
      return;
    }
    if (!webhook) {
      setError("Slack Webhook URL을 입력해주세요.");
      return;
    }
    setBusy(true);
    try {
      await api.createSubscription({
        siteNo: site.siteNo,
        siteNm: site.siteNm,
        movNo: movie.movNo,
        movNm: movie.movNm,
        startDate: startYmd,
        endDate: endYmd || startYmd,
        slackWebhookUrl: webhook,
        specialAuditorium: null,
      });
      setStartYmd("");
      setEndYmd("");
      await refreshSubs();
    } catch {
      setError("이미 예매가 열려 있거나 등록에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  };

  const complete = async (id) => {
    await api.completeSubscription(id);
    refreshSubs();
  };

  const rangeLabel = (s) =>
    s.startDate === s.endDate ? fromYmd(s.startDate) : `${fromYmd(s.startDate)} ~ ${fromYmd(s.endDate)}`;

  return (
    <div className="page">
      <header className="hd">
        <div className="brand">
          <span className="mark">CGV</span>
          <span>예매 오픈 알리미</span>
        </div>
        <p className="tagline">특별관 상영, 예매가 열리는 순간 Slack으로 알려드려요.</p>
      </header>

      <div className="workspace">
        {/* ── 극장 ── */}
        <section className="panel col-theaters">
          <div className="ph"><h3>극장</h3></div>
          <div className="regions">
            {regions.map((r) => (
              <button
                type="button"
                key={r.code}
                className={"chip" + (r.code === regionCode ? " on" : "")}
                onClick={() => { setRegionCode(r.code); setSiteNo(""); }}
              >
                {r.name}<em>{r.sites.length}</em>
              </button>
            ))}
          </div>
          <div className="body sites">
            {sites.map((s) => (
              <button
                type="button"
                key={s.siteNo}
                className={"site" + (s.siteNo === siteNo ? " on" : "")}
                onClick={() => setSiteNo(s.siteNo)}
              >
                <strong>{s.siteNm}</strong>
                <span className="auds">{s.specialAuditoriums.join(" · ")}</span>
              </button>
            ))}
          </div>
        </section>

        {/* ── 영화 포스터 ── */}
        <section className="panel col-movies">
          <div className="ph">
            <h3>영화{site && <small> · {site.siteNm}</small>}</h3>
          </div>
          <div className="body">
            {!siteNo && <p className="empty-hint">← 왼쪽에서 극장을 먼저 선택하세요.</p>}
            {siteNo && moviesState === "loading" && (
              <MovieLoading slow={slowLoad} onRetry={loadMovies} />
            )}
            {siteNo && moviesState === "error" && <MovieError onRetry={loadMovies} />}
            {siteNo && moviesState === "idle" && movies.length === 0 && (
              <p className="empty-hint">지금 예매 가능한 영화가 없어요.</p>
            )}
            {siteNo && moviesState === "idle" && movies.length > 0 && (
              <div className="movies">
                {movies.map((m) => (
                  <button
                    type="button"
                    key={m.movNo}
                    className={"movie" + (m.movNo === movNo ? " on" : "")}
                    onClick={() => setMovNo(m.movNo)}
                    title={m.movNm}
                  >
                    <div className="poster">
                      {m.posterUrl ? (
                        <img src={m.posterUrl} alt={m.movNm} loading="lazy" />
                      ) : (
                        <div className="noposter">{m.movNm.slice(0, 6)}</div>
                      )}
                    </div>
                    <span className="mtitle">{m.movNm}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* ── 알림 설정 / 내 구독 (분리된 두 패널) ── */}
        <div className="col-side">
        <section className="panel side-alarm">
          <div className="ph"><h3>알림 설정</h3></div>
          <div className="body">
            {!movNo && <p className="empty-hint">영화를 선택하면 상영일과 알림을 설정할 수 있어요.</p>}
            {movNo && (
              <form onSubmit={submit} className="infoform">
                <div className="pick">
                  {movie?.posterUrl && <img src={movie.posterUrl} alt="" />}
                  <div>
                    <strong>{movie?.movNm}</strong>
                    <span>{site?.siteNm}</span>
                  </div>
                </div>

                <div className="fieldlabel">
                  상영일 <small>{isRange ? "기간 선택됨" : startYmd ? "하루 선택됨" : "날짜를 선택하세요"}</small>
                </div>
                <Calendar
                  startYmd={startYmd}
                  endYmd={endYmd}
                  openDates={openDates}
                  onChange={(s, e) => { setStartYmd(s); setEndYmd(e); }}
                />

                <label>
                  Slack Webhook URL
                  <input
                    type="url"
                    placeholder="https://hooks.slack.com/services/..."
                    value={webhook}
                    onChange={(e) => setWebhook(e.target.value)}
                  />
                </label>
                {error && <p className="hint err">{error}</p>}
                <button className="submit" type="submit" disabled={busy}>
                  {busy ? "등록 중…" : "알림 구독하기"}
                </button>
              </form>
            )}
          </div>
        </section>

        <section className="panel side-subs">
          <div className="ph"><h3>내 구독 <span className="count">{subs.length}</span></h3></div>
          <div className="body">
            <ul className="subs">
              {subs.map((s) => (
                <li key={s.id} className={"scard" + (s.completedAt ? " done" : "")}>
                  <div className="s-poster">
                    <img
                      src={posterUrlOf(s.movNo)}
                      alt=""
                      loading="lazy"
                      onError={(e) => { e.currentTarget.style.visibility = "hidden"; }}
                    />
                  </div>
                  <div className="s-info">
                    <strong className="s-title">{s.movNm}</strong>
                    <span className="s-site">{s.siteNm}</span>
                    <span className="s-period">{rangeLabel(s)}</span>
                  </div>
                  {s.completedAt ? (
                    <span className="s-badge">종료됨</span>
                  ) : (
                    <button type="button" className="done-btn" onClick={() => complete(s.id)}>
                      구독종료
                    </button>
                  )}
                </li>
              ))}
              {subs.length === 0 && <li className="empty">아직 구독이 없어요.</li>}
            </ul>
          </div>
        </section>
        </div>
      </div>
    </div>
  );
}

// 영화 로딩: 스켈레톤 포스터 + 스피너, 오래 걸리면 재시도 안내.
function MovieLoading({ slow, onRetry }) {
  return (
    <div className="movie-loading">
      <div className="movies skeleton" aria-hidden="true">
        {Array.from({ length: 8 }).map((_, i) => (
          <div className="movie" key={i}>
            <div className="poster sk" />
            <span className="sk-line" />
          </div>
        ))}
      </div>
      <div className="load-note">
        <span className="spinner" />
        <span>{slow ? "예매 정보를 가져오는 중이에요…" : "영화 목록을 불러오는 중…"}</span>
      </div>
      {slow && (
        <div className="load-slow">
          <p>CGV에서 실시간으로 가져오느라 평소보다 오래 걸리고 있어요.</p>
          <button type="button" className="retry" onClick={onRetry}>다시 시도</button>
        </div>
      )}
    </div>
  );
}

// 영화 로딩 실패: 사유 안내 + 다시 불러오기.
function MovieError({ onRetry }) {
  return (
    <div className="load-error">
      <div className="load-error-face">😵‍💫</div>
      <strong>영화 목록을 불러오지 못했어요</strong>
      <p>네트워크가 불안정하거나 CGV 응답이 지연됐을 수 있어요.</p>
      <button type="button" className="retry" onClick={onRetry}>다시 불러오기</button>
    </div>
  );
}
