import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
    <Alert className="border-warning bg-warning/10 text-foreground">
      <AlertTitle>Venue heads-up</AlertTitle>
      <AlertDescription>
        <ul className="list-disc space-y-0.5 pl-4">
          {relevant.map((n) => (
            <li key={n.id}>
              <span className="font-medium">{n.venue}</span> is needed
              {n.cohort_code ? ` by ${n.cohort_code}` : ""} from {hm(n.start_time)}
              {n.end_time ? `–${hm(n.end_time)}` : ""} — please vacate in time
              {n.note ? ` · ${n.note}` : ""}.
            </li>
          ))}
        </ul>
      </AlertDescription>
    </Alert>
  );
}
