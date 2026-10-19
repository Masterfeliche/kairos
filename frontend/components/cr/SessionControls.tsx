"use client";

import { useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import { LiveBadge } from "@/components/timetable/SessionCard";
import VenueNoticeDialog from "@/components/cr/VenueNoticeDialog";
import MoveSwapDialog from "@/components/cr/MoveSwapDialog";
import type { LiveStatus, PublicSession } from "@/lib/student";

const STATUS_OPTIONS: { value: LiveStatus; label: string }[] = [
  { value: "live", label: "Start / mark live" },
  { value: "ended", label: "End class" },
  { value: "not_held", label: "Not held" },
  { value: "scheduled", label: "Reset to scheduled" },
];

/** The extra controls the CR gets on top of the normal student timetable. */
export default function SessionControls({
  session,
  siblings = [],
  onChanged,
}: {
  session: PublicSession;
  siblings?: PublicSession[];
  onChanged: () => void;
}) {
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function setLive(st: LiveStatus) {
    setSaving(true);
    setErr(null);
    try {
      await api(`/api/v1/cr/sessions/${session.id}/live`, {
        method: "POST",
        body: JSON.stringify({ status: st }),
      });
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">Class rep:</span>
        <LiveBadge status={session.live_status} />
        <Select value="action" onValueChange={(v) => v !== "action" && setLive(v as LiveStatus)}>
          <SelectTrigger className="h-8 w-[150px]" disabled={saving}>
            <SelectValue placeholder="Mark live" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <MoveSwapDialog session={session} siblings={siblings} onDone={onChanged} />
        <VenueNoticeDialog
          defaultVenue={session.venue ?? ""}
          defaultDay={session.day_of_week}
          defaultStart={session.start_time}
          defaultEnd={session.end_time}
          triggerLabel="Venue soon"
          onDone={onChanged}
        />
      </div>
      {err && <p className="text-xs text-destructive">{err}</p>}
    </div>
  );
}

