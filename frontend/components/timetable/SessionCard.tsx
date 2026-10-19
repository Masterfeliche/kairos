import { Badge } from "@/components/ui/badge";
import {
  DAY_SHORT,
  hm,
  LIVE_LABELS,
  courseAccentStyle,
  type LiveStatus,
  type PublicSession,
} from "@/lib/student";

function originLabel(session: PublicSession): string {
  const dayChanged =
    session.original_day_of_week != null && session.original_day_of_week !== session.day_of_week;
  const prefix = dayChanged ? `${DAY_SHORT[session.original_day_of_week!]} ` : "";
  return `${prefix}${hm(session.original_start_time ?? session.start_time)}–${hm(
    session.original_end_time ?? session.end_time,
  )}`;
}

function duration(start: string, end: string): string {
  const [sh, sm] = start.split(":").map(Number);
  const [eh, em] = end.split(":").map(Number);
  const mins = eh * 60 + em - (sh * 60 + sm);
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${h ? `${h}h` : ""}${m ? ` ${m}m` : ""}`.trim();
}

const LIVE_CLASS: Record<LiveStatus, string> = {
  scheduled: "bg-muted text-muted-foreground",
  live: "bg-success text-success-foreground",
  ended: "bg-muted text-muted-foreground",
  not_held: "bg-destructive/15 text-destructive",
};

export function LiveBadge({ status }: { status: LiveStatus }) {
  if (status === "scheduled") return null;
  return (
    <Badge className={LIVE_CLASS[status]}>
      {status === "live" && (
        <span className="size-1.5 animate-pulse rounded-full bg-current" aria-hidden />
      )}
      {LIVE_LABELS[status]}
    </Badge>
  );
}

export default function SessionCard({
  session,
  sourceFilename,
  dim,
  actions,
}: {
  session: PublicSession;
  sourceFilename: string | null;
  dim?: boolean;
  actions?: React.ReactNode;
}) {
  const accent = courseAccentStyle(session.course_code);
  return (
    <details
      className={`card border-l-4 ${dim ? "bg-muted/40" : ""} ${
        session.live_status === "live" ? "ring-1 ring-success/50" : ""
      }`}
      style={accent}
    >
      <summary className="flex cursor-pointer list-none items-start gap-3">
        <span className="w-14 shrink-0 text-sm font-medium tabular-nums text-foreground sm:w-16">
          {hm(session.start_time)}
          <span className="block text-xs font-normal text-muted-foreground">{hm(session.end_time)}</span>
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-foreground">{session.course_name}</span>
            <LiveBadge status={session.live_status} />
          </span>
          <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
            {session.course_code && <span className="font-mono">{session.course_code}</span>}
            {session.venue && <span>· {session.venue}</span>}
            {session.session_type && <Badge variant="secondary">{session.session_type}</Badge>}
          </span>
          {session.rescheduled && (
            <span className="mt-1 block text-xs font-medium text-warning">
              Moved · was {originLabel(session)}
            </span>
          )}
        </span>
      </summary>

      <dl className="mt-3 space-y-1 border-t border-border pt-3 text-sm">
        <Row label="Time">
          {hm(session.start_time)}–{hm(session.end_time)} ({duration(session.start_time, session.end_time)})
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

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <dt className="w-24 shrink-0 text-muted-foreground">{label}</dt>
      <dd className="text-foreground">{children}</dd>
    </div>
  );
}
