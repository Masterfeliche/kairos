import { ArrowLeftRight, Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  DAY_SHORT,
  hm,
  LIVE_LABELS,
  sentence,
  type LiveStatus,
  type PublicSession,
} from "@/lib/student";

/** How a card should read at a glance on the viewed day. */
export type SessionTone = "default" | "past" | "live";

function originLabel(session: PublicSession): string {
  const dayChanged =
    session.original_day_of_week != null && session.original_day_of_week !== session.day_of_week;
  const prefix = dayChanged ? `${DAY_SHORT[session.original_day_of_week!]} ` : "";
  const venue =
    session.original_venue && session.original_venue !== session.venue
      ? `, ${session.original_venue}`
      : "";
  return `${prefix}${hm(session.original_start_time ?? session.start_time)}${venue}`;
}

function duration(start: string, end: string): string {
  const [sh, sm] = start.split(":").map(Number);
  const [eh, em] = end.split(":").map(Number);
  const mins = eh * 60 + em - (sh * 60 + sm);
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${h ? `${h}h` : ""}${m ? ` ${m}m` : ""}`.trim();
}

function lecturerLabel(lecturers: string[]): string | null {
  if (lecturers.length === 0) return null;
  return lecturers.length === 1 ? lecturers[0] : `${lecturers[0]} +${lecturers.length - 1}`;
}

export function LiveBadge({ status }: { status: LiveStatus }) {
  if (status === "scheduled") return null;
  if (status === "ended") {
    return (
      <span className="inline-flex shrink-0 items-center gap-1 text-xs font-semibold text-muted-foreground">
        <Check className="size-3.5" aria-hidden /> Ended
      </span>
    );
  }
  return (
    <span
      className={cn(
        "inline-flex h-[22px] shrink-0 items-center gap-1.5 rounded-full px-2 text-[11px] font-bold uppercase tracking-wide",
        status === "live"
          ? "bg-success text-success-foreground"
          : "bg-destructive/10 text-destructive",
      )}
    >
      {status === "live" && (
        <span className="size-1.5 animate-pulse rounded-full bg-current" aria-hidden />
      )}
      {LIVE_LABELS[status]}
    </span>
  );
}

export default function SessionCard({
  session,
  sourceFilename,
  tone = "default",
  showTime = true,
  actions,
}: {
  session: PublicSession;
  sourceFilename: string | null;
  tone?: SessionTone;
  /** The day timeline shows times in its own rail, so cards there omit them. */
  showTime?: boolean;
  actions?: React.ReactNode;
}) {
  const notHeld = session.live_status === "not_held";
  const lecturer = lecturerLabel(session.lecturers);

  return (
    <details
      className={cn(
        "group rounded-2xl border px-3.5 py-3 transition-colors",
        notHeld
          ? "border-dashed border-destructive/40 bg-card"
          : tone === "live"
            ? "border-[1.5px] border-success bg-card shadow-[0_2px_10px_color-mix(in_oklch,var(--success)_12%,transparent)]"
            : tone === "past"
              ? "border-border bg-muted/70"
              : "border-border bg-card",
      )}
    >
      <summary className="flex cursor-pointer list-none items-start gap-3 [&::-webkit-details-marker]:hidden">
        {showTime && (
          <span className="w-12 shrink-0 font-mono text-sm font-semibold tabular-nums text-foreground">
            {hm(session.start_time)}
            <span className="block text-xs font-medium text-muted-foreground">{hm(session.end_time)}</span>
          </span>
        )}
        <span className="min-w-0 flex-1">
          <span className="flex items-start justify-between gap-2">
            <span
              className={cn(
                "font-semibold leading-snug",
                notHeld && "line-through",
                notHeld || tone === "past" ? "text-muted-foreground" : "text-foreground",
              )}
            >
              {session.course_name}
            </span>
            <span className="flex shrink-0 items-center gap-1.5">
              <LiveBadge status={session.live_status} />
              <ChevronDown
                className="mt-0.5 size-4 text-muted-foreground transition-transform group-open:rotate-180"
                aria-hidden
              />
            </span>
          </span>
          <span className="mt-0.5 block text-[13px] text-muted-foreground">
            {[
              session.course_code && <span key="c" className="font-mono">{session.course_code}</span>,
              session.venue,
              lecturer,
            ]
              .filter(Boolean)
              .flatMap((part, i) => (i === 0 ? [part] : [" · ", part]))}
          </span>
          {(session.session_type || session.shared_with.length > 0) && (
            <span className="mt-2 flex flex-wrap gap-1.5">
              {session.session_type && <Chip>{sentence(session.session_type)}</Chip>}
              {session.shared_with.length > 0 && (
                <Chip>Shared with {session.shared_with.join(", ")}</Chip>
              )}
            </span>
          )}
          {session.rescheduled && (
            <span className="mt-2 flex items-center gap-1.5 text-xs font-semibold text-warning">
              <ArrowLeftRight className="size-3.5 shrink-0" aria-hidden />
              Moved by class rep · was {originLabel(session)}
            </span>
          )}
        </span>
      </summary>

      <dl className="mt-3 space-y-1 border-t border-border pt-3 text-sm">
        <Row label="Time">
          <span className="font-mono">{hm(session.start_time)}–{hm(session.end_time)}</span> (
          {duration(session.start_time, session.end_time)})
        </Row>
        {session.course_code && (
          <Row label="Code">
            <span className="font-mono">{session.course_code}</span>
          </Row>
        )}
        {session.department && <Row label="Department">{session.department}</Row>}
        <Row label="Lecturer">{session.lecturers.length ? session.lecturers.join(", ") : "Not provided"}</Row>
        <Row label="Venue">{session.venue || "Not provided"}</Row>
        <Row label="Status">{LIVE_LABELS[session.live_status]}</Row>
        {session.rescheduled && (
          <Row label="Change">
            {session.reschedule_reason || "Time/venue updated"}
            {session.original_venue && session.original_venue !== session.venue
              ? ` (was ${session.original_venue})`
              : ""}
          </Row>
        )}
        {session.shared_with.length > 0 && <Row label="Shared with">{session.shared_with.join(", ")}</Row>}
        <Row label="Source">
          From {sourceFilename ?? "source document"}, page {session.source_page}
        </Row>
      </dl>

      {actions && <div className="mt-3 border-t border-border pt-3">{actions}</div>}
    </details>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex h-[22px] items-center rounded-md bg-secondary px-2 text-xs font-medium text-secondary-foreground">
      {children}
    </span>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <dt className="w-24 shrink-0 text-muted-foreground">{label}</dt>
      <dd className="text-foreground">{children}</dd>
    </div>
  );
}
