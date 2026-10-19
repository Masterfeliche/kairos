"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { MapPin, Search, User, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import SessionCard, { type SessionTone } from "@/components/timetable/SessionCard";
import { useCampusClock } from "@/components/timetable/useCampusClock";
import { DayStrip, ViewSwitch } from "@/components/timetable/DayNav";
import { fmtClock, fmtDuration, type CampusNow } from "@/lib/time";
import {
  DAY_SHORT,
  DAYS,
  GRID_START,
  hm,
  SLOT,
  SLOTS,
  courseAccentStyle,
  isCurrent,
  nowAndNext,
  sentence,
  toMin,
  type PublicSession,
} from "@/lib/student";

export type TimetableViewProps = {
  sessions: PublicSession[];
  basePath: string;
  day: number;
  view: "day" | "week";
  /** Campus clock at render time; the view keeps it ticking in the browser. */
  clock: CampusNow;
  sourceFilename: string | null;
  /** Shown under the "right now" card on the day view (e.g. venue heads-ups). */
  dayBanner?: React.ReactNode;
  renderActions?: (session: PublicSession) => React.ReactNode;
  /** Class reps can drag lessons on the week grid (drop empty = move, drop lesson = swap). */
  onMove?: (session: PublicSession, day: number, startMin: number) => void;
  onSwap?: (session: PublicSession, target: PublicSession) => void;
};

function link(basePath: string, params: string): string {
  return `${basePath}?${params}`;
}

export default function TimetableView({
  sessions,
  basePath,
  day,
  view,
  clock,
  sourceFilename,
  dayBanner,
  renderActions,
  onMove,
  onSwap,
}: TimetableViewProps) {
  const now = useCampusClock(clock);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  const filteredSessions = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return sessions;
    return sessions.filter((s) =>
      [s.course_name, s.course_code, s.venue, s.department, s.lecturers.join(" ")]
        .some((field) => (field || "").toLowerCase().includes(q)),
    );
  }, [sessions, searchQuery]);

  const week = view === "week";
  const byDay: Record<number, PublicSession[]> = { 1: [], 2: [], 3: [], 4: [], 5: [] };
  for (const s of filteredSessions) {
    if (byDay[s.day_of_week]) byDay[s.day_of_week].push(s);
  }
  for (const d of [1, 2, 3, 4, 5]) byDay[d].sort((a, b) => a.start_time.localeCompare(b.start_time));

  const dayCount = byDay[day].length;

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          {week ? (
            <>
              <h2 className="text-2xl font-bold tracking-tight text-foreground">This week</h2>
              <p className="text-sm text-muted-foreground">
                {now.weekLabels[1]} – {now.weekLabels[5]}
              </p>
            </>
          ) : (
            <>
              <h2 className="text-[1.625rem] font-bold leading-tight tracking-tight text-foreground">
                {DAYS[day]}
              </h2>
              <p className="text-sm text-muted-foreground">
                {now.weekLabels[day]} · {dayCount} {dayCount === 1 ? "class" : "classes"}
              </p>
            </>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={() => setSearchOpen((o) => !o)}
            aria-expanded={searchOpen}
            aria-controls="tt-search"
            aria-label="Search this timetable"
            className="flex size-11 items-center justify-center rounded-xl text-muted-foreground transition hover:bg-muted hover:text-foreground sm:hidden"
          >
            <Search className="size-5" aria-hidden />
          </button>
          <ViewSwitch basePath={basePath} day={day} week={week} />
        </div>
      </div>

      <div id="tt-search" className={cn("relative max-w-md", searchOpen || searchQuery ? "block" : "hidden sm:block")}>
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input
          type="search"
          placeholder="Filter by course, code, lecturer, room"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="h-11 rounded-xl bg-card pl-9 pr-9 text-sm"
          aria-label="Filter timetable sessions"
        />
        {searchQuery && (
          <button
            type="button"
            onClick={() => setSearchQuery("")}
            className="absolute right-1 top-1/2 flex size-9 -translate-y-1/2 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground"
            aria-label="Clear search"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      {searchQuery.trim() && (
        <p className="px-1 text-xs text-muted-foreground" aria-live="polite">
          Showing <strong className="text-foreground">{filteredSessions.length}</strong> of{" "}
          {sessions.length} sessions matching &quot;{searchQuery}&quot;
        </p>
      )}

      {filteredSessions.length === 0 && searchQuery.trim() ? (
        <div className="rounded-2xl border border-dashed border-border bg-card/40 p-8 text-center">
          <Search className="mx-auto mb-2 size-7 text-muted-foreground/60" aria-hidden="true" />
          <p className="font-semibold text-foreground">No matching classes found</p>
          <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
            Try a course code, room or lecturer name.
          </p>
          <Button variant="outline" size="sm" className="mt-4" onClick={() => setSearchQuery("")}>
            Clear search
          </Button>
        </div>
      ) : week ? (
        <WeekView
          basePath={basePath}
          byDay={byDay}
          allSessions={filteredSessions}
          now={now}
          sourceFilename={sourceFilename}
          renderActions={renderActions}
          onMove={onMove}
          onSwap={onSwap}
        />
      ) : (
        <DayView
          basePath={basePath}
          day={day}
          sessions={byDay[day]}
          now={now}
          sourceFilename={sourceFilename}
          dayBanner={dayBanner}
          renderActions={renderActions}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ Day view */

function toneFor(s: PublicSession, minutes: number | null): SessionTone {
  if (minutes === null) return s.live_status === "live" ? "live" : "default";
  if (isCurrent(s, minutes)) return "live";
  if (s.live_status === "ended" || toMin(s.end_time) <= minutes) return "past";
  return "default";
}

function DayView({
  basePath, day, sessions, now, sourceFilename, dayBanner, renderActions,
}: {
  basePath: string; day: number; sessions: PublicSession[]; now: CampusNow;
  sourceFilename: string | null; dayBanner?: React.ReactNode;
  renderActions?: (s: PublicSession) => React.ReactNode;
}) {
  const isToday = day === now.today;

  return (
    <div className="space-y-4">
      <DayStrip basePath={basePath} day={day} now={now} />

      {isToday && sessions.length > 0 && <NowCard sessions={sessions} minutes={now.minutes} />}
      {dayBanner}

      {sessions.length === 0 ? (
        <div className="space-y-2 rounded-2xl border border-border bg-card p-5 text-sm text-muted-foreground">
          <p>No classes on {DAYS[day]}.</p>
          <Link prefetch={false} className="font-medium text-primary hover:underline" href={link(basePath, "view=week")}>
            See the whole week
          </Link>
        </div>
      ) : (
        <Timeline
          sessions={sessions}
          sourceFilename={sourceFilename}
          minutes={isToday ? now.minutes : null}
          renderActions={renderActions}
        />
      )}

      <p className="text-xs text-muted-foreground">Times are East Africa Time (EAT).</p>
    </div>
  );
}

/** "What's on now, and what's next" — the question students open the app to answer. */
function NowCard({ sessions, minutes }: { sessions: PublicSession[]; minutes: number }) {
  const { current, next } = nowAndNext(sessions, minutes);

  if (!current && !next) {
    return (
      <section aria-label="Right now" className="rounded-2xl bg-spotlight p-4 text-spotlight-foreground">
        <p className="font-semibold">No more classes today</p>
        <p className="text-sm text-spotlight-muted">Check tomorrow in the day strip above.</p>
      </section>
    );
  }

  return (
    <section aria-label="Right now" className="rounded-[1.125rem] bg-spotlight p-4 text-spotlight-foreground">
      {current ? (
        <CurrentBlock session={current} minutes={minutes} />
      ) : (
        next && <UpNextBlock session={next} minutes={minutes} />
      )}

      {current && next && (
        <div className="mt-4 flex items-center gap-3 border-t border-spotlight-accent pt-3.5">
          <span className="text-[11px] font-bold tracking-wider text-sidebar-primary">NEXT</span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">{next.course_name}</p>
            <p className="truncate text-xs text-spotlight-muted">
              <span className="font-mono">{hm(next.start_time)}</span>
              {next.venue ? ` · ${next.venue}` : ""}
              {next.rescheduled ? " · moved" : ""}
            </p>
          </div>
          <span className="shrink-0 font-mono text-[13px] font-semibold">
            in {fmtDuration(toMin(next.start_time) - minutes)}
          </span>
        </div>
      )}
    </section>
  );
}

function CurrentBlock({ session, minutes }: { session: PublicSession; minutes: number }) {
  const start = toMin(session.start_time);
  const end = toMin(session.end_time);
  const pct = Math.min(100, Math.max(0, ((minutes - start) / (end - start)) * 100));
  const left = end - minutes;
  const live = session.live_status === "live";

  return (
    <>
      <div className="flex items-center justify-between gap-2">
        <span
          className={cn(
            "inline-flex h-[26px] items-center gap-1.5 rounded-full px-2.5 text-xs font-bold tracking-wide",
            live ? "bg-[#1f6f43] text-white" : "bg-spotlight-accent text-spotlight-foreground",
          )}
        >
          <span className={cn("size-[7px] rounded-full", live ? "animate-pulse bg-[#86efac]" : "bg-sidebar-primary")} />
          {live ? "LIVE NOW" : "IN PROGRESS"}
        </span>
        {left > 0 && <span className="font-mono text-[13px] text-spotlight-muted">ends in {fmtDuration(left)}</span>}
      </div>
      <SessionHeadline session={session} />
      <div className="mt-3.5 flex items-center gap-2.5">
        <span className="font-mono text-xs text-spotlight-muted">{hm(session.start_time)}</span>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-spotlight-accent" role="presentation">
          <div className="h-full rounded-full bg-sidebar-primary" style={{ width: `${pct}%` }} />
        </div>
        <span className="font-mono text-xs text-spotlight-muted">{hm(session.end_time)}</span>
      </div>
    </>
  );
}

function UpNextBlock({ session, minutes }: { session: PublicSession; minutes: number }) {
  return (
    <>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-bold tracking-wider text-sidebar-primary">UP NEXT</span>
        <span className="font-mono text-[13px] text-spotlight-muted">
          {hm(session.start_time)} · in {fmtDuration(toMin(session.start_time) - minutes)}
        </span>
      </div>
      <SessionHeadline session={session} />
    </>
  );
}

function SessionHeadline({ session }: { session: PublicSession }) {
  const lecturer = session.lecturers[0];
  return (
    <>
      <h3 className="mt-3 text-xl font-semibold leading-snug">{session.course_name}</h3>
      {(session.course_code || session.session_type) && (
        <p className="font-mono text-[13px] text-spotlight-muted">
          {[session.course_code, session.session_type && sentence(session.session_type)].filter(Boolean).join(" · ")}
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-sm text-spotlight-foreground/90">
        <span className="inline-flex items-center gap-1.5">
          <MapPin className="size-4" aria-hidden />
          {session.venue || "Venue not provided"}
        </span>
        {lecturer && (
          <span className="inline-flex items-center gap-1.5">
            <User className="size-4" aria-hidden />
            {lecturer}
          </span>
        )}
      </div>
    </>
  );
}

/** Chronological rail: times, state dots, free gaps and a "now" marker. */
function Timeline({
  sessions, sourceFilename, minutes, renderActions,
}: {
  sessions: PublicSession[]; sourceFilename: string | null; minutes: number | null;
  renderActions?: (s: PublicSession) => React.ReactNode;
}) {
  const rows: React.ReactNode[] = [];
  let prevEnd: string | null = null;
  let nowPlaced = minutes === null;

  const nowRow = (key: string) => (
    <li key={key} aria-label={`Current time ${fmtClock(minutes!)}`} className="grid grid-cols-[3rem_1.125rem_minmax(0,1fr)] items-center gap-x-2 pb-2">
      <span className="font-mono text-xs font-semibold text-primary">{fmtClock(minutes!)}</span>
      <span className="size-2.5 justify-self-center rounded-full bg-primary" />
      <span className="h-0.5 rounded-full bg-primary" />
    </li>
  );

  sessions.forEach((s, i) => {
    if (!nowPlaced && toMin(s.start_time) > minutes!) {
      rows.push(nowRow("now"));
      nowPlaced = true;
    }
    if (prevEnd && s.start_time > prevEnd) {
      const gap = toMin(s.start_time) - toMin(prevEnd);
      rows.push(
        <li key={`gap-${s.id}`} className="grid grid-cols-[3rem_1.125rem_minmax(0,1fr)] gap-x-2">
          <span />
          <span className="justify-self-center border-l-2 border-dashed border-input" />
          <p className="mb-2.5 px-0.5 py-1.5 text-[13px] text-muted-foreground">
            Free · <span className="font-mono">{hm(prevEnd)}–{hm(s.start_time)}</span> · {fmtDuration(gap)}
          </p>
        </li>,
      );
    }

    const tone = toneFor(s, minutes);
    const notHeld = s.live_status === "not_held";
    const last = i === sessions.length - 1;
    rows.push(
      <li key={s.id} className="grid grid-cols-[3rem_1.125rem_minmax(0,1fr)] gap-x-2">
        <div
          className={cn(
            "pt-3 font-mono text-[13px] leading-tight tabular-nums",
            tone === "live" ? "font-semibold text-foreground" : "text-muted-foreground",
            notHeld && "line-through",
          )}
        >
          {hm(s.start_time)}
          <span className="block text-xs font-medium text-muted-foreground">{hm(s.end_time)}</span>
        </div>
        <div className="flex flex-col items-center">
          <RailDot session={s} tone={tone} />
          {!last && <span className="w-0.5 flex-1 bg-input" />}
        </div>
        <div className="min-w-0 pb-2.5">
          <SessionCard
            session={s}
            sourceFilename={sourceFilename}
            tone={tone}
            showTime={false}
            actions={renderActions?.(s)}
          />
        </div>
      </li>,
    );
    prevEnd = prevEnd && prevEnd > s.end_time ? prevEnd : s.end_time;
  });

  if (!nowPlaced) rows.push(nowRow("now-end"));

  return <ol className="flex flex-col">{rows}</ol>;
}

function RailDot({ session, tone }: { session: PublicSession; tone: SessionTone }) {
  if (session.live_status === "not_held") {
    return <span className="mt-[15px] size-3 rounded-[3px] bg-destructive" aria-hidden />;
  }
  if (tone === "live") {
    return <span className="mt-[13px] size-4 rounded-full bg-success ring-4 ring-success/20" aria-hidden />;
  }
  if (tone === "past") {
    return <span className="mt-[15px] size-3 rounded-full bg-muted-foreground/40" aria-hidden />;
  }
  if (session.rescheduled) {
    return <span className="mt-[15px] size-3 rounded-full border-2 border-warning bg-card" aria-hidden />;
  }
  return <span className="mt-[15px] size-3 rounded-full border-2 border-primary bg-card" aria-hidden />;
}

/* ----------------------------------------------------------------- Week view */

function WeekView({
  basePath, byDay, allSessions, now, sourceFilename, renderActions, onMove, onSwap,
}: {
  basePath: string; byDay: Record<number, PublicSession[]>; allSessions: PublicSession[];
  now: CampusNow; sourceFilename: string | null;
  renderActions?: (s: PublicSession) => React.ReactNode;
  onMove?: (s: PublicSession, day: number, startMin: number) => void;
  onSwap?: (s: PublicSession, target: PublicSession) => void;
}) {
  const today = now.today;
  const dragEnabled = Boolean(onMove && onSwap);
  const [dragId, setDragId] = useState<string | null>(null);
  const [hover, setHover] = useState<{ day: number; slot: number } | null>(null);
  const [overId, setOverId] = useState<string | null>(null);
  // `dragstart` may fire before React commits `dragId`, so mirror it in a ref that the
  // dragover/drop handlers can read synchronously.
  const dragIdRef = useRef<string | null>(null);
  const dragged = dragId ? allSessions.find((s) => s.id === dragId) ?? null : null;

  function draggedSession(): PublicSession | null {
    const id = dragIdRef.current;
    return id ? allSessions.find((s) => s.id === id) ?? null : null;
  }

  function reset() {
    dragIdRef.current = null;
    setDragId(null);
    setHover(null);
    setOverId(null);
  }

  function slotFromY(clientY: number, el: HTMLElement): number {
    const rect = el.getBoundingClientRect();
    const rowH = rect.height / SLOTS;
    return Math.max(0, Math.min(SLOTS - 1, Math.floor((clientY - rect.top) / rowH)));
  }

  function onColDragOver(e: React.DragEvent<HTMLDivElement>, d: number) {
    if (!dragEnabled || !draggedSession()) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setOverId(null);
    setHover({ day: d, slot: slotFromY(e.clientY, e.currentTarget) });
  }

  function onColDrop(e: React.DragEvent<HTMLDivElement>, d: number) {
    const src = draggedSession();
    if (!dragEnabled || !src) return;
    e.preventDefault();
    const startMin = GRID_START + slotFromY(e.clientY, e.currentTarget) * SLOT;
    reset();
    onMove!(src, d, startMin);
  }

  return (
    <>
      {/* Mobile: collapsible agenda per day */}
      <div className="space-y-2 md:hidden">
        {[1, 2, 3, 4, 5].map((d) => (
          <details key={d} className="group rounded-2xl border border-border bg-card p-4" open={d === today}>
            <summary className="flex min-h-6 cursor-pointer list-none items-center justify-between font-semibold text-foreground [&::-webkit-details-marker]:hidden">
              <span>
                {DAYS[d]} <span className="font-normal text-muted-foreground">· {now.weekLabels[d]}</span>
                {d === today && <span className="ml-2 text-xs font-semibold text-primary">Today</span>}
              </span>
              <span className="text-xs font-normal text-muted-foreground">{byDay[d].length} classes</span>
            </summary>
            <div className="mt-3 space-y-2.5">
              {byDay[d].length === 0
                ? <p className="text-sm text-muted-foreground">No classes.</p>
                : byDay[d].map((s) => (
                    <SessionCard key={s.id} session={s} sourceFilename={sourceFilename}
                      tone={d === today ? toneFor(s, now.minutes) : "default"}
                      actions={renderActions?.(s)} />
                  ))}
            </div>
          </details>
        ))}
      </div>

      {/* Desktop: aligned time grid */}
      <div className="hidden md:block">
        {dragEnabled && (
          <p className="mb-2 text-xs text-muted-foreground">
            {dragged
              ? "Drop on a free slot to move, or on another class to swap."
              : "Drag a class to another time — drop on a free slot to move, or on another class to swap."}
          </p>
        )}
        <div className="rounded-2xl border border-border bg-card pb-3 pr-3">
          <div
            className="grid border-b border-border"
            style={{ gridTemplateColumns: "3.5rem repeat(5, minmax(0, 1fr))" }}
          >
            <div />
            {[1, 2, 3, 4, 5].map((d) => (
              <div key={d}
                className={cn(
                  "py-2.5 text-center",
                  d === today && "rounded-t-xl bg-primary/8",
                )}>
                <div className={cn("text-xs font-medium", d === today ? "font-bold text-primary" : "text-muted-foreground")}>
                  {DAY_SHORT[d]}{d === today ? " · Today" : ""}
                </div>
                <div className={cn("font-mono text-[17px] font-semibold", d === today ? "text-primary" : "text-foreground")}>
                  {now.weekDates[d]}
                </div>
              </div>
            ))}
          </div>

          <div
            className="relative grid"
            style={{
              gridTemplateColumns: "3.5rem repeat(5, minmax(0, 1fr))",
              gridTemplateRows: `repeat(${SLOTS}, 1.75rem)`,
            }}
          >
            {Array.from({ length: SLOTS / 2 + 1 }, (_, i) => i * 2).map((slot) => (
              <div key={`t-${slot}`}
                className="col-start-1 pr-2.5 text-right font-mono text-[11px] leading-none text-muted-foreground"
                style={{ gridRow: `${slot + 1} / span 1`, alignSelf: "start", transform: "translateY(-0.35rem)" }}>
                {slot === SLOTS || slot === 0 ? "" : fmtClock(GRID_START + slot * SLOT)}
              </div>
            ))}

            {[1, 2, 3, 4, 5].map((d) => (
              <div key={`col-${d}`} data-daycol={d}
                className={cn(
                  "border-l border-border/60 transition-colors",
                  d === today && "bg-primary/[0.04]",
                  dragged && "bg-primary/5",
                )}
                style={{ gridColumn: d + 1, gridRow: `1 / span ${SLOTS}` }}
                onDragOver={(e) => onColDragOver(e, d)}
                onDragLeave={() => setHover((h) => (h?.day === d ? null : h))}
                onDrop={(e) => onColDrop(e, d)}
              />
            ))}

            {hover && (
              <div
                className="pointer-events-none z-0 rounded-lg bg-primary/20 ring-1 ring-inset ring-primary/50"
                style={{ gridColumn: hover.day + 1, gridRow: `${hover.slot + 1} / span 1`,
                         margin: "0 0.125rem" }}
                aria-hidden
              />
            )}

            {[1, 2, 3, 4, 5].flatMap((d) =>
              byDay[d].map((s) => (
                <GridSession
                  key={s.id}
                  session={s}
                  day={d}
                  basePath={basePath}
                  past={d === today && toneFor(s, now.minutes) === "past"}
                  dragEnabled={dragEnabled}
                  dragging={dragId === s.id}
                  dropTarget={overId === s.id}
                  onDragStart={() => {
                    dragIdRef.current = s.id;
                    setDragId(s.id);
                  }}
                  onDragEnd={reset}
                  onDragOver={(e) => {
                    const src = draggedSession();
                    if (!dragEnabled || !src || src.id === s.id) return;
                    e.preventDefault();
                    e.stopPropagation();
                    e.dataTransfer.dropEffect = "move";
                    setHover(null);
                    setOverId(s.id);
                  }}
                  onDrop={(e) => {
                    const src = draggedSession();
                    if (!dragEnabled || !src || src.id === s.id) return;
                    e.preventDefault();
                    e.stopPropagation();
                    reset();
                    onSwap!(src, s);
                  }}
                />
              )),
            )}

            {(() => {
              const slot = (now.minutes - GRID_START) / SLOT;
              if (!today || slot < 0 || slot > SLOTS) return null;
              return (
                <div
                  className="pointer-events-none relative z-20 h-0.5 bg-primary"
                  style={{
                    gridColumn: today + 1,
                    gridRow: `${Math.floor(slot) + 1} / span 1`,
                    alignSelf: "start",
                    marginTop: `${(slot % 1) * 1.75}rem`,
                  }}
                >
                  <span className="absolute -left-1 -top-1 size-2.5 rounded-full bg-primary" />
                </div>
              );
            })()}
          </div>
        </div>
      </div>
    </>
  );
}

function GridSession({
  session, day, basePath, past, dragEnabled, dragging, dropTarget,
  onDragStart, onDragEnd, onDragOver, onDrop,
}: {
  session: PublicSession; day: number; basePath: string; past: boolean; dragEnabled: boolean;
  dragging: boolean; dropTarget: boolean;
  onDragStart: () => void; onDragEnd: () => void;
  onDragOver: (e: React.DragEvent<HTMLAnchorElement>) => void;
  onDrop: (e: React.DragEvent<HTMLAnchorElement>) => void;
}) {
  const start = Math.max(0, Math.floor((toMin(session.start_time) - GRID_START) / SLOT));
  const end = Math.min(SLOTS, Math.ceil((toMin(session.end_time) - GRID_START) / SLOT));
  const rowSpan = Math.max(1, end - start);
  const live = session.live_status === "live";
  const notHeld = session.live_status === "not_held";
  const accent = courseAccentStyle(session.course_code);

  return (
    <Link
      prefetch={false}
      href={link(basePath, `day=${day}`)}
      draggable={dragEnabled}
      onDragStart={(e) => {
        if (!dragEnabled) return;
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", session.id);
        onDragStart();
      }}
      onDragEnd={onDragEnd}
      onDragOver={onDragOver}
      onDrop={onDrop}
      title={`${session.course_name}\n${hm(session.start_time)}–${hm(session.end_time)}${
        session.venue ? ` · ${session.venue}` : ""
      }`}
      className={cn(
        "z-10 m-0.5 flex flex-col gap-0.5 overflow-hidden rounded-lg px-2 py-1.5 text-left text-xs leading-tight transition hover:shadow-md",
        notHeld
          ? "border border-dashed border-destructive/40 bg-muted"
          : live
            ? "border-2 border-success"
            : session.rescheduled
              ? "border-[1.5px] border-dashed border-warning"
              : "border border-transparent",
        past && "opacity-55",
        dragEnabled && "cursor-grab active:cursor-grabbing",
        dragging && "opacity-40",
        dropTarget && "ring-2 ring-primary ring-offset-1 ring-offset-background",
      )}
      style={{
        gridColumn: day + 1,
        gridRow: `${start + 1} / span ${rowSpan}`,
        background: notHeld ? undefined : accent.background,
      }}
    >
      {live && (
        <span className="self-start rounded bg-success px-1.5 text-[10px] font-bold tracking-wide text-success-foreground">
          LIVE
        </span>
      )}
      <span className={cn("line-clamp-2 font-semibold text-foreground", notHeld && "text-muted-foreground line-through")}>
        {session.course_name}
      </span>
      {rowSpan >= 2 && (
        <span className="truncate font-mono text-[11px] text-muted-foreground">
          {hm(session.start_time)}{session.venue ? ` · ${session.venue}` : ""}
        </span>
      )}
      {notHeld && <span className="text-[10px] font-bold text-destructive">NOT HELD</span>}
      {session.rescheduled && !notHeld && rowSpan >= 2 && (
        <span className="text-[10px] font-semibold text-warning">
          Moved · was{" "}
          {session.original_day_of_week != null && session.original_day_of_week !== session.day_of_week
            ? `${DAY_SHORT[session.original_day_of_week]} `
            : ""}
          {hm(session.original_start_time ?? session.start_time)}
        </span>
      )}
    </Link>
  );
}
