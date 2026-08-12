import { useState } from "react";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];
const key = (y, m, d) =>
  `${y}${String(m + 1).padStart(2, "0")}${String(d).padStart(2, "0")}`;

// 범위 선택 캘린더. 시작일(anchor)을 잡은 뒤 클릭은 항상 그 anchor 기준으로 종료일을
// 정한다. 예: 8/8~8/14 상태에서 8/10을 누르면 새로 시작하지 않고 8/8~8/10으로 조정된다.
// 시작일보다 앞 날짜를 누르면 그 날로 anchor를 다시 잡는다(완전 초기화는 '지우기').
// 두 클릭 사이에 달(‹ ›)을 넘겨도 선택이 유지되어 다음 달까지 걸친 범위를 고를 수 있다.
// 마우스를 올리면 예정 범위를 미리 보여준다. 지난 날짜/이미 오픈된 날짜는 선택 불가.
export default function Calendar({ startYmd, endYmd, onChange, openDates }) {
  const today = new Date();
  const todayKey = key(today.getFullYear(), today.getMonth(), today.getDate());

  const base =
    startYmd && startYmd.length === 8
      ? { y: +startYmd.slice(0, 4), m: +startYmd.slice(4, 6) - 1 }
      : { y: today.getFullYear(), m: today.getMonth() };
  const [view, setView] = useState(base);
  const [hover, setHover] = useState(null);

  const openSet = new Set(openDates || []);

  const firstWeekday = new Date(view.y, view.m, 1).getDay();
  const daysInMonth = new Date(view.y, view.m + 1, 0).getDate();
  const cells = [
    ...Array(firstWeekday).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  const move = (delta) =>
    setView((v) => {
      const m = v.m + delta;
      if (m < 0) return { y: v.y - 1, m: 11 };
      if (m > 11) return { y: v.y + 1, m: 0 };
      return { y: v.y, m };
    });

  const pick = (k) => {
    if (!startYmd || k < startYmd) {
      onChange(k, k); // 시작일 지정(또는 더 앞 날짜로 anchor 재설정)
    } else {
      onChange(startYmd, k); // anchor 기준 종료일 지정/조정
    }
    setHover(null);
  };

  // anchor(startYmd) 이후 hover 미리보기 범위 [start, hover]
  const previewing = startYmd && hover && hover >= startYmd && hover !== endYmd;

  return (
    <div className="cal">
      <div className="cal-hd">
        <button type="button" onClick={() => move(-1)} aria-label="이전 달">‹</button>
        <span>{view.y}년 {view.m + 1}월</span>
        <button type="button" onClick={() => move(1)} aria-label="다음 달">›</button>
      </div>

      <div className="cal-grid cal-wd">
        {WEEKDAYS.map((w, i) => (
          <span key={w} className={i === 0 ? "sun" : i === 6 ? "sat" : ""}>{w}</span>
        ))}
      </div>

      <div
        className="cal-grid cal-days"
        key={`${view.y}-${view.m}`}
        onMouseLeave={() => setHover(null)}
      >
        {cells.map((d, i) => {
          if (d === null) return <span key={`e${i}`} className="cal-cell empty" />;
          const k = key(view.y, view.m, d);
          const wd = i % 7;
          const isOpen = openSet.has(k);
          const disabled = k < todayKey || isOpen;
          const inRange = startYmd && endYmd && k >= startYmd && k <= endYmd;
          const inPreview = previewing && k >= startYmd && k <= hover;
          const isEnd = k === startYmd || k === endYmd || (previewing && k === hover);
          const cls = [
            "cal-cell",
            inRange || inPreview ? "range" : "",
            isEnd && (inRange || inPreview) ? "on" : "",
            k === todayKey ? "today" : "",
            isOpen ? "opened" : "",
            wd === 0 ? "sun" : wd === 6 ? "sat" : "",
          ].join(" ");
          return (
            <button
              key={k}
              type="button"
              className={cls}
              disabled={disabled}
              onClick={() => pick(k)}
              onMouseEnter={() => !disabled && setHover(k)}
            >
              {d}
              {isOpen && <i className="dot" />}
            </button>
          );
        })}
      </div>

      <p className="cal-legend">
        <i className="swatch open" /> 오픈 완료
      </p>
    </div>
  );
}
