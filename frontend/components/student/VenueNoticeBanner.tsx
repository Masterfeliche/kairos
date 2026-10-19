import { BellRing } from "lucide-react";
import { hm, type VenueNotice } from "@/lib/student";

/** Shows CR heads-ups for venues used on the viewed day so people can vacate in time. */
export default function VenueNoticeBanner({
  notices,
  venues,
}: {
  notices: VenueNotice[];
  venues: Set<string>;
}) {
  const relevant = notices
    .filter((n) => n.venue && venues.has(n.venue))
    .sort((a, b) => a.start_time.localeCompare(b.start_time));
  if (relevant.length === 0) return null;

  return (
    <aside
      aria-label="Venue heads-up"
      className="flex gap-2.5 rounded-2xl border border-warning/35 bg-warning/10 px-3.5 py-3 text-foreground"
    >
      <BellRing className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden />
      <ul className="space-y-2 text-[13px] leading-snug">
        {relevant.map((n) => (
          <li key={n.id}>
            <p className="font-semibold">
              {n.venue} is needed at <span className="font-mono">{hm(n.start_time)}</span>
              {n.end_time ? <span className="font-mono">–{hm(n.end_time)}</span> : null}
            </p>
            <p className="text-muted-foreground">
              {n.cohort_code ? `${n.cohort_code} has the room next` : "Someone has the room next"} — please
              leave on time{n.note ? ` · ${n.note}` : ""}.
            </p>
          </li>
        ))}
      </ul>
    </aside>
  );
}
