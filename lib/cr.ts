import type { VenueNotice } from "./student";

export type LiveStatus = "scheduled" | "live" | "ended" | "not_held";

export type CrCohort = { id: string; code: string; intake_year: number | null; section: string | null };

export type CrSession = {
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
  cohorts: string[];
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

export type CrMe = {
  id: string;
  email: string;
  role: "cr";
  display_name: string | null;
  cohorts: CrCohort[];
};

export type CrVersion = {
  id: string;
  label: string;
  status: string;
  is_preview: boolean;
  source_filename?: string | null;
  published_at?: string | null;
  updated_at?: string | null;
};

export type CrTimetable = {
  cohort: CrCohort;
  my_cohorts: CrCohort[];
  version: CrVersion;
  /** Monday of the teaching week these sessions describe (campus time). */
  week_start: string;
  sessions: CrSession[];
};

export type Institute = {
  version: CrVersion;
  sessions: CrSession[];
};

export type VenueAvail = { venue: string; name: string | null; free: boolean; notice?: VenueNotice | null };
export type Availability = { day: number; start: string; end: string; venues: VenueAvail[] };

import { api } from "./api";
export { api };
export type { VenueNotice } from "./student";
