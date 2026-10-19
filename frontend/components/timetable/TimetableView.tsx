"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import SessionCard from "@/components/timetable/SessionCard";
import {
  DAY_SHORT,
  DAYS,
  GRID_END,
  GRID_START,
  hm,
  SLOT,
  SLOTS,
  courseAccentStyle,
  toMin,
  type PublicSession,
} from "@/lib/student";

export type TimetableViewProps = {
  sessions: PublicSession[];
  basePath: string;
  day: number;
  view: "day" | "week";
  today: number;
  nowMinutes: number;
  sourceFilename: string | null;
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
  today,
  nowMinutes,
  sourceFilename,
  renderActions,
  onMove,
  onSwap,
}: TimetableViewProps) {
  const week = view === "week";
  const byDay: Record<number, PublicSession[]> = { 1: [], 2: [], 3: [], 4: [], 5: [] };
  for (const s of sessions) {
    if (byDay[s.day_of_week]) byDay[s.day_of_week].push(s);
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <div className="inline-flex rounded-xl border border-border bg-card p-0.5 text-sm">
          <Tab href={link(basePath, `day=${day}`)} active={!week}>Day</Tab>
          <Tab href={link(basePath, `view=week`)} active={week}>Week</Tab>
        </div>
      </div>

      {week ? (
        <WeekView
          basePath={basePath}
          byDay={byDay}
          allSessions={sessions}
          today={today}
          nowMinutes={nowMinutes}
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
          today={today}
          nowMinutes={nowMinutes}
          isToday={day === today}
          sourceFilename={sourceFilename}
          renderActions={renderActions}
        />
      )}
    </div>
  );
}

function Tab({ href, active, children }: { href: string; active: boolean; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      prefetch={false}
      className={`rounded-lg px-4 py-1.5 font-medium transition ${
        active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"
      }`}
    >
      {children}
    </Link>
  );
}

function DayView({
  basePath, day, sessions, today, nowMinutes, isToday, sourceFilename, renderActions,
}: {
  basePath: string; day: number; sessions: PublicSession[]; today: number;
  nowMinutes: number; isToday: boolean; sourceFilename: string | null;
  renderActions?: (s: PublicSession) => React.ReactNode;
}) {
  const prev = day > 1 ? day - 1 : 5;
  const next = day < 5 ? day + 1 : 1;
  const dateLabel = dateFor(day);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Button asChild variant="outline" size="icon" aria-label="Previous day">
          <Link prefetch={false} href={link(basePath, `day=${prev}`)}>◀</Link>
        </Button>
        <div className="text-center">
          <p className="font-semibold text-foreground">{DAYS[day]}</p>
          {dateLabel && <p className="text-xs text-muted-foreground">{dateLabel}</p>}
        </div>
        <Button asChild variant="outline" size="icon" aria-label="Next day">
          <Link prefetch={false} href={link(basePath, `day=${next}`)}>▶</Link>
        </Button>
      </div>

      <div className="-mx-4 flex gap-1 overflow-x-auto px-4 pb-1">
        {[1, 2, 3, 4, 5].map((d) => (
          <Link key={d} prefetch={false} href={link(basePath, `day=${d}`)}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm transition ${
              d === day ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/70"
            }`}>
            {DAY_SHORT[d]}{d === today ? " •" : ""}
          </Link>
        ))}
      </div>

      {sessions.length === 0 ? (
        <div className="card space-y-2 text-sm text-muted-foreground">
          <p>No classes on {DAYS[day]}.</p>
          <Link prefetch={false} className="text-primary hover:underline" href={link(basePath, "view=week")}>
            See the whole week
          </Link>
        </div>
      ) : (
        <Agenda sessions={sessions} sourceFilename={sourceFilename}
          nowMinutes={isToday ? nowMinutes : null} renderActions={renderActions} />
      )}
    </div>
  );
}

function Agenda({
  sessions, sourceFilename, nowMinutes, renderActions,
}: {
  sessions: PublicSession[]; sourceFilename: string | null; nowMinutes: number | null;
  renderActions?: (s: PublicSession) => React.ReactNode;
}) {
  const items: React.ReactNode[] = [];
  let prevEnd: string | null = null;

  for (const s of sessions) {
    if (prevEnd && s.start_time > prevEnd) {
      items.push(
        <div key={`gap-${s.id}`} className="flex items-center gap-2 py-0.5 text-xs text-muted-foreground">
          <span className="h-px flex-1 bg-border" />
          Free {hm(prevEnd)}–{hm(s.start_time)}
          <span className="h-px flex-1 bg-border" />
        </div>,
      );
    }
    const past = nowMinutes !== null && !s.rescheduled && toMin(s.end_time) <= nowMinutes;
    items.push(
      <SessionCard
        key={s.id}
        session={s}
        sourceFilename={sourceFilename}
        dim={past}
        actions={renderActions?.(s)}
      />,
    );
    prevEnd = s.end_time;
  }

  return <div className="space-y-2.5">{items}</div>;
}

function WeekView({
  basePath, byDay, allSessions, today, nowMinutes, sourceFilename, renderActions, onMove, onSwap,
}: {
  basePath: string; byDay: Record<number, PublicSession[]>; allSessions: PublicSession[];
  today: number; nowMinutes: number; sourceFilename: string | null;
  renderActions?: (s: PublicSession) => React.ReactNode;
  onMove?: (s: PublicSession, day: number, startMin: number) => void;
  onSwap?: (s: PublicSession, target: PublicSession) => void;
}) {
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
          <details key={d} className="card" open={d === today}>
            <summary className="cursor-pointer list-none font-semibold text-foreground">
              {DAYS[d]}
              <span className="ml-2 text-xs text-muted-foreground">{byDay[d].length} classes</span>
            </summary>
            <div className="mt-3 space-y-2.5">
              {byDay[d].length === 0
                ? <p className="text-sm text-muted-foreground">No classes.</p>
                : byDay[d].map((s) => (
                    <SessionCard key={s.id} session={s} sourceFilename={sourceFilename}
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
        <div
          className="grid items-end gap-x-1"
          style={{ gridTemplateColumns: "3.25rem repeat(5, minmax(0, 1fr))" }}
        >
          <div />
          {[1, 2, 3, 4, 5].map((d) => (
            <div key={d}
              className={`flex items-center justify-center gap-1 rounded-t-lg border-b-2 pb-1 text-sm font-semibold ${
                d === today ? "border-primary text-primary" : "border-border text-foreground"
              }`}>
              {DAY_SHORT[d]}
              {d === today && <span className="text-[10px] text-muted-foreground">today</span>}
            </div>
          ))}
        </div>

        <div
          className="relative grid gap-x-1"
          style={{
            gridTemplateColumns: "3.25rem repeat(5, minmax(0, 1fr))",
            gridTemplateRows: `repeat(${SLOTS}, 1.75rem)`,
          }}
        >
          {Array.from({ length: SLOTS / 2 + 1 }, (_, i) => i * 2).map((slot) => (
            <div key={`t-${slot}`}
              className="col-start-1 pr-2 text-right text-[10px] leading-none text-muted-foreground"
              style={{ gridRow: `${slot + 1} / span 1`, alignSelf: "start", transform: "translateY(-0.35rem)" }}>
              {slot === SLOTS ? "" : fmtTime(GRID_START + slot * SLOT)}
            </div>
          ))}

          {[1, 2, 3, 4, 5].map((d) => (
            <div key={`col-${d}`} data-daycol={d}
              className={`border-l border-border/60 transition-colors ${dragged ? "bg-primary/5" : ""}`}
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
            const slot = (nowMinutes - GRID_START) / SLOT;
            if (slot < 0 || slot > SLOTS) return null;
            return (
              <div
                className="pointer-events-none z-20 h-0.5 bg-destructive"
                style={{ gridColumn: today + 1, gridRow: `${Math.floor(slot) + 1} / span 1`, alignSelf: "start" }}
              />
            );
          })()}
        </div>
      </div>
    </>
  );
}

function GridSession({
  session, day, basePath, dragEnabled, dragging, dropTarget,
  onDragStart, onDragEnd, onDragOver, onDrop,
}: {
  session: PublicSession; day: number; basePath: string; dragEnabled: boolean;
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
  const stateBg = notHeld
    ? "bg-destructive/10"
    : live
      ? "bg-success/10"
      : session.rescheduled
        ? "bg-warning/10"
        : "";

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
      className={`m-0.5 z-10 flex flex-col overflow-hidden rounded-lg border border-border border-l-4 p-1.5 text-left text-xs shadow-sm transition hover:shadow-md ${stateBg} ${
        dragEnabled ? "cursor-grab active:cursor-grabbing" : ""
      } ${dragging ? "opacity-40" : ""} ${dropTarget ? "ring-2 ring-primary ring-offset-1 ring-offset-background" : ""}`}
      style={{
        gridColumn: day + 1,
        gridRow: `${start + 1} / span ${rowSpan}`,
        borderLeftColor: accent.borderLeftColor,
        background: stateBg ? undefined : accent.background,
      }}
    >
      <span className="flex items-center gap-1 font-medium tabular-nums text-foreground">
        {hm(session.start_time)}
        {live && <span className="size-1.5 animate-pulse rounded-full bg-success" aria-hidden />}
      </span>
      <span className="line-clamp-2 font-semibold text-foreground">{session.course_name}</span>
      {rowSpan >= 2 && (
        <span className="mt-auto truncate text-[10px] text-muted-foreground">
          {session.venue || session.course_code || ""}
        </span>
      )}
      {session.rescheduled && rowSpan >= 2 && (
        <span className="text-[10px] font-medium text-warning">
          was{" "}
          {session.original_day_of_week != null && session.original_day_of_week !== session.day_of_week
            ? `${DAY_SHORT[session.original_day_of_week]} `
            : ""}
          {hm(session.original_start_time ?? session.start_time)}
        </span>
      )}
    </Link>
  );
}

function fmtTime(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function dateFor(weekday: number): string | null {
  const now = new Date();
  const current = now.getDay();
  if (current === 0 || current === 6) return null;
  const delta = weekday - current;
  const d = new Date(now);
  d.setDate(now.getDate() + delta);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
}
