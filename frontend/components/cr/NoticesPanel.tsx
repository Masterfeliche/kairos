"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import { hm, DAYS, type VenueNotice } from "@/lib/student";
import VenueNoticeDialog from "@/components/cr/VenueNoticeDialog";

export default function NoticesPanel({ reloadKey }: { reloadKey: number }) {
  const [notices, setNotices] = useState<VenueNotice[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await api<{ notices: VenueNotice[] }>("/api/v1/cr/venue-notices");
      setNotices(res.notices);
      setErr(null);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Failed to load notices");
    }
  }, []);

  useEffect(() => { load(); }, [load, reloadKey]);

  async function clear(id: string) {
    setBusy(id);
    try {
      await api(`/api/v1/cr/venue-notices/${id}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card className="space-y-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Venue heads-ups</h2>
          <p className="text-xs text-muted-foreground">
            Tell others a venue is about to be needed so they can leave in time and not take it by mistake.
          </p>
        </div>
        <VenueNoticeDialog defaultDay={1} triggerLabel="Add heads-up" onDone={load} />
      </div>

      {err && <p className="text-xs text-destructive">{err}</p>}
      {notices.length === 0 ? (
        <p className="text-sm text-muted-foreground">No active heads-ups.</p>
      ) : (
        <ul className="divide-y divide-border">
          {notices.map((n) => (
            <li key={n.id} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span>
                <span className="font-medium">{n.venue}</span>
                <span className="text-muted-foreground">
                  {" · "}{DAYS[n.day_of_week]} {hm(n.start_time)}
                  {n.end_time ? `–${hm(n.end_time)}` : ""}
                  {n.cohort_code ? ` · ${n.cohort_code}` : ""}
                  {n.note ? ` · ${n.note}` : ""}
                </span>
              </span>
              <Button variant="ghost" size="sm" disabled={busy === n.id} onClick={() => clear(n.id)}>
                Clear
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
