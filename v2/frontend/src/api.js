// 백엔드 API 래퍼.
async function json(res) {
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.status === 204 ? null : res.json();
}

export const api = {
  listSites: () => fetch("/api/sites").then(json),
  listRegions: () => fetch("/api/regions").then(json),
  listMovies: (siteNo) => fetch(`/api/sites/${siteNo}/movies`).then(json),
  listOpenDates: (siteNo, movNo) =>
    fetch(`/api/sites/${siteNo}/movies/${movNo}/open-dates`).then(json),
  listSubscriptions: () => fetch("/api/subscriptions").then(json),
  createSubscription: (body) =>
    fetch("/api/subscriptions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(json),
  completeSubscription: (id) =>
    fetch(`/api/subscriptions/${id}/complete`, { method: "POST" }).then(json),
  deleteSubscription: (id) =>
    fetch(`/api/subscriptions/${id}`, { method: "DELETE" }).then(json),
};

// "2026-08-15" -> "20260815"
export const toYmd = (isoDate) => isoDate.replaceAll("-", "");
// "20260815" -> "2026-08-15"
export const fromYmd = (ymd) =>
  `${ymd.slice(0, 4)}-${ymd.slice(4, 6)}-${ymd.slice(6, 8)}`;

// movNo 로 CGV 포스터 URL 조립 (백엔드와 동일 규칙). 구독 목록 썸네일용.
export const posterUrlOf = (movNo) => {
  const n = Number(movNo);
  if (!n) return null;
  const group = String(Math.floor(n / 1000)).padStart(6, "0");
  return `https://cdn.cgv.co.kr/cgvpomsfilm/Movie/Thumbnail/Poster/${group}/${movNo}/${movNo}_320.jpg`;
};
