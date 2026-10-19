"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeftRight, ChevronRight, DoorOpen } from "lucide-react";
import SessionActions from "@/components/cr/SessionActions";
import { LiveBadge } from "@/components/timetable/SessionCard";
import { DayStrip, ViewSwitch } from "@/components/timetable/DayNav";
import { useCampusClock } from "@/components/timetable/useCampusClock";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { campusClockOf, fmtClock, fmtDuration, type CampusNow } from "@/lib/time";
import { DAY_SHORT, DAYS, hm, nowAndNext, toMin, type PublicSession } from "@/lib/student";
import type { VenueAvail } from "@/lib/cr";

/**
 * The class rep's day: the class on now and the next one get big one-tap controls; the
 * rest of the day is a compact list with a ⋯ menu each.
 */
export default function CrDayView({
  sessions,
  day,
  clock,
  banner,
  onChanged,
}: {
  sessions: PublicSession[];
  day: number;
  clock: CampusNow;
  banner?: React.ReactNode;
  onChanged: () => void;
}) {
  const now = useCampusClock(clock);
  const isToday = day === now.today;
  const daySessions = sessions
    .filter((s) => s.day_of_week === day)
    .sort((a, b) => a.start_time.localeCompare(b.start_time));
  const { current, next } = isToday ? nowAndNext(daySessions, now.minutes) : { current: undefined, next: undefined };
  const rest = daySessions.filter((s) => s !== current && s !== next);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold leading-tight tracking-tight text-foreground">
            {DAYS[day]}, {now.weekLabels[day]}
          </h1>
          <p className="text-sm text-muted-foreground">Changes you make show to the whole class instantly.</p>
        </div>
        <ViewSwitch basePath="/cr" day={day} week={false} />
      </div>

      <DayStrip basePath="/cr" day={day} now={now} />

      {current && (
        <ControlCard kind="current" session={current} minutes={now.minutes} siblings={sessions} onChanged={onChanged} />
      )}
      {next && (
        <ControlCard kind="next" session={next} minutes={now.minutes} siblings={sessions} onChanged={onChanged} />
      )}
      {isToday && !current && !next && daySessions.length > 0 && (
        <p className="rounded-2xl border border-border bg-card p-4 text-sm text-muted-foreground">
          No more classes today. You can still update earlier ones below.
        </p>
      )}

      {banner}

      {daySessions.length === 0 ? (
        <p className="rounded-2xl border border-border bg-card p-5 text-sm text-muted-foreground">
          No classes on {DAYS[day]}.
        </p>
      ) : (
        rest.length > 0 && (
          <section aria-labelledby="rest-heading" className="space-y-2">
            <h2 id="rest-heading" className="text-[13px] font-semibold uppercase tracking-wider text-muted-foreground">
              {isToday ? "Rest of today" : `${DAYS[day]}'s classes`}
            </h2>
            <ul className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
              {rest.map((s) => {
                const past = isToday && (s.live_status === "ended" || toMin(s.end_time) <= now.minutes);
                return (
                  <li key={s.id} className="flex min-h-15 items-center gap-3 py-2 pl-3.5 pr-1.5">
                    <span className={cn("w-11 shrink-0 font-mono text-[13px]", past ? "text-muted-foreground" : "text-foreground")}>
                      {hm(s.start_time)}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className={cn("block truncate text-sm font-medium", past || s.live_status === "not_held" ? "text-muted-foreground" : "text-foreground", s.live_status === "not_held" && "line-through")}>
                        {s.course_name}
                      </span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {s.venue || "Venue not provided"}
                        {s.rescheduled && " · moved"}
                      </span>
                    </span>
                    <LiveBadge status={s.live_status} />
                    <SessionActions session={s} siblings={sessions} onChanged={onChanged} layout="menu" />
                  </li>
                );
              })}
            </ul>
          </section>
        )
      )}

      {isToday && <FreeRoomsLink day={day} minutes={now.minutes} />}
    </div>
  );
}

function ControlCard({
  kind, session, minutes, siblings, onChanged,
}: {
  kind: "current" | "next";
  session: PublicSession;
  minutes: number;
  siblings: PublicSession[];
  onChanged: () => void;
}) {
  const live = session.live_status === "live";
  const lecturer = session.lecturers[0];
  const movedFrom =
    session.rescheduled &&
    `moved from ${
      session.original_day_of_week && session.original_day_of_week !== session.day_of_week
        ? `${DAY_SHORT[session.original_day_of_week]} `
        : ""
    }${hm(session.original_start_time ?? session.start_time)}`;

  return (
    <section
      aria-label={kind === "current" ? "Class on now" : "Next class"}
      className={cn(
        "rounded-[1.125rem] bg-card p-4",
        live ? "border-[1.5px] border-success" : "border border-border",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        {kind === "current" ? (
          live ? (
            <span className="inline-flex h-6 items-center gap-1.5 rounded-full bg-success px-2.5 text-[11px] font-bold tracking-wide text-success-foreground">
              <span className="size-1.5 animate-pulse rounded-full bg-current" aria-hidden />
              LIVE{session.live_started_at ? ` · since ${campusClockOf(session.live_started_at)}` : ""}
            </span>
          ) : (
            <span className="inline-flex h-6 items-center rounded-full bg-warning/15 px-2.5 text-[11px] font-bold tracking-wide text-warning">
              NOT STARTED YET
            </span>
          )
        ) : (
          <span className="text-xs font-bold tracking-wider text-muted-foreground">
            UP NEXT · in {fmtDuration(toMin(session.start_time) - minutes)}
          </span>
        )}
        <span className="shrink-0 font-mono text-[13px] text-muted-foreground">
          {hm(session.start_time)}–{hm(session.end_time)}
        </span>
      </div>
      <h2 className="mt-2.5 text-lg font-semibold leading-snug text-foreground">{session.course_name}</h2>
      <p className="text-[13px] text-muted-foreground">
        {[session.venue || "Venue not provided", lecturer].filter(Boolean).join(" · ")}
        {movedFrom && (
          <span className="font-semibold text-warning">
            {" · "}
            <ArrowLeftRight className="inline size-3.5 align-[-2px]" aria-hidden /> {movedFrom}
          </span>
        )}
      </p>
      <div className="mt-3.5">
        <SessionActions session={session} siblings={siblings} onChanged={onChanged} layout="buttons" />
      </div>
    </section>
  );
}

/** Shortcut to the room finder, previewing venues free for the next hour. */
function FreeRoomsLink({ day, minutes }: { day: number; minutes: number }) {
  const [free, setFree] = useState<string[] | null>(null);
  // Re-query every 15 minutes rather than on every clock tick.
  const bucket = Math.floor(minutes / 15) * 15;

  useEffect(() => {
    if (bucket < 6 * 60 || bucket + 60 > 22 * 60) {
      setFree(null);
      return;
    }
    let alive = true;
    const start = fmtClock(bucket);
    const end = fmtClock(bucket + 60);
    api<{ venues: VenueAvail[] }>(`/api/v1/cr/availability?day=${day}&start=${start}&end=${end}`)
      .then((r) => alive && setFree(r.venues.filter((v) => v.free).map((v) => v.venue)))
      .catch(() => alive && setFree(null));
    return () => {
      alive = false;
    };
  }, [day, bucket]);

  const preview =
    free && free.length > 0
      ? `Free now: ${free.slice(0, 3).join(", ")}${free.length > 3 ? ` +${free.length - 3} more` : ""}`
      : free
        ? "No rooms free for the next hour"
        : "See which venues are open";

  return (
    <Link
      href="/cr/institute"
      className="flex items-center gap-3 rounded-2xl border border-primary/25 bg-primary/8 p-3.5 transition hover:bg-primary/12"
    >
      <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
        <DoorOpen className="size-5" aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[15px] font-semibold text-foreground">Find a free room</span>
        <span className="block truncate text-[13px] text-muted-foreground">{preview}</span>
      </span>
      <ChevronRight className="size-5 shrink-0 text-primary" aria-hidden />
    </Link>
  );
}
