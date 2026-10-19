export type PublicVersion = {
  id: string;
  period_id: string;
  label: string;
  status: string;
  is_active: boolean;
  is_preview: boolean;
  published_at: string | null;
  updated_at: string | null;
  source_filename: string | null;
};

export type LiveStatus = "scheduled" | "live" | "ended" | "not_held";

export type PublicSession = {
  id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  course_code: string | null;
  course_name: string;
  department: string | null;
  lecturers: string[];
  venue: string | null;
  session_type: string | null;
  shared_with: string[];
  source_page: number;
  live_status: LiveStatus;
  live_started_at: string | null;
  live_ended_at: string | null;
  rescheduled: boolean;
  reschedule_reason: string | null;
  rescheduled_at: string | null;
  original_day_of_week: number | null;
  original_start_time: string | null;
  original_end_time: string | null;
  original_venue: string | null;
};

export type TimetableResponse = {
  cohort: { id: string; code: string; intake_year: number | null; section: string | null };
  version: PublicVersion;
  sessions: PublicSession[];
};

export type VenueNotice = {
  id: string;
  venue: string;
  cohort_code: string | null;
  day_of_week: number;
  start_time: string;
  end_time: string | null;
  note: string | null;
  created_at: string | null;
};

export type Programme = {
  id: string;
  name: string;
  code: string;
  level: "beng" | "diploma" | "btech" | "masters";
  department: string | null;
  cohorts: { id: string; code: string; intake_year: number | null; section: string | null }[];
};

export const DAYS = ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
export const DAY_SHORT = ["", "Mon", "Tue", "Wed", "Thu", "Fri"];

export const LEVEL_LABELS: Record<string, string> = {
  beng: "BEng — Bachelor of Engineering",
  diploma: "Diploma",
  btech: "BTech",
  masters: "Masters",
};

export const LEVEL_ORDER = ["beng", "diploma", "btech", "masters"];

export function hm(t: string): string {
  return t.slice(0, 5);
}

export function todayWeekday(): number {
  const d = new Date().getDay();
  return d >= 1 && d <= 5 ? d : 1;
}

export const LIVE_LABELS: Record<LiveStatus, string> = {
  scheduled: "Scheduled",
  live: "Live now",
  ended: "Ended",
  not_held: "Not held",
};

export function toMin(t: string): number {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

// Grid geometry shared by the week view (start 07:00, 30-minute slots).
export const GRID_START = 7 * 60;
export const GRID_END = 21 * 60;
export const SLOT = 30;
export const SLOTS = (GRID_END - GRID_START) / SLOT;

// A small curated palette so each course gets a stable, pleasant accent hue.
const ACCENTS = [265, 210, 155, 25, 330, 190, 285, 45];

export function courseHue(seed: string | null | undefined): number {
  const s = (seed || "?").toUpperCase();
  let n = 0;
  for (let i = 0; i < s.length; i++) n = (n * 33 + s.charCodeAt(i)) % 100000;
  return ACCENTS[n % ACCENTS.length];
}

export function courseAccentStyle(seed: string | null | undefined): React.CSSProperties {
  const hue = courseHue(seed);
  const base = `hsl(${hue} 70% 55%)`;
  return {
    borderLeftColor: base,
    background: `hsl(${hue} 70% 55% / 0.10)`,
  };
}


