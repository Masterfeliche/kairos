// Campus clock. The timetable is in East Africa Time, so "now", "today" and the week's dates
// are always computed in Africa/Dar_es_Salaam — never in the server's (often UTC) zone or a
// visitor's device zone.

export const CAMPUS_TZ = "Africa/Dar_es_Salaam";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export type CampusNow = {
  /** ISO weekday: 1 = Monday … 7 = Sunday. */
  isoWeekday: number;
  /** Minutes since midnight, campus time. */
  minutes: number;
  /** Teaching day shown as "today": 1–5, or 0 at weekends. */
  today: number;
  /** Day-of-month labels ("15") for Mon–Fri of the current teaching week, index 1–5. */
  weekDates: string[];
  /** Long labels ("15 Oct") for Mon–Fri, index 1–5. */
  weekLabels: string[];
};

const PARTS = new Intl.DateTimeFormat("en-GB", {
  timeZone: CAMPUS_TZ,
  year: "numeric",
  month: "numeric",
  day: "numeric",
  hour: "numeric",
  minute: "numeric",
  hourCycle: "h23",
});

export function campusNow(at: Date = new Date()): CampusNow {
  const p: Record<string, number> = {};
  for (const part of PARTS.formatToParts(at)) {
    if (part.type !== "literal") p[part.type] = Number(part.value);
  }
  // A UTC date with the campus calendar fields lets us do plain date arithmetic.
  const day = new Date(Date.UTC(p.year, p.month - 1, p.day));
  const isoWeekday = day.getUTCDay() === 0 ? 7 : day.getUTCDay();
  const today = isoWeekday <= 5 ? isoWeekday : 0;

  // At weekends, show the coming week's dates.
  const monday = new Date(day);
  monday.setUTCDate(day.getUTCDate() - (isoWeekday - 1) + (isoWeekday > 5 ? 7 : 0));

  const weekDates = [""];
  const weekLabels = [""];
  for (let i = 0; i < 5; i++) {
    const d = new Date(monday);
    d.setUTCDate(monday.getUTCDate() + i);
    weekDates.push(String(d.getUTCDate()));
    weekLabels.push(`${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`);
  }

  return { isoWeekday, minutes: p.hour * 60 + p.minute, today, weekDates, weekLabels };
}

/** "1h 08m", "38 min". */
export function fmtDuration(mins: number): string {
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h}h ${String(m).padStart(2, "0")}m` : `${h}h`;
}

export function fmtClock(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/** "10:04" in campus time, from an ISO timestamp. */
export function campusClockOf(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", {
    timeZone: CAMPUS_TZ,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
}
