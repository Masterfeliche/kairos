"use client";

import { useCallback, useEffect, useState } from "react";
import { BellRing, Plus } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import { hm, DAY_SHORT, type VenueNotice } from "@/lib/student";
import VenueNoticeDialog from "@/components/cr/VenueNoticeDialog";

/** The rep's posted venue heads-ups, with Add and Clear. */
export default function NoticesPanel({ reloadKey, defaultDay }: { reloadKey: number; defaultDay: number }) {
  const [notices, setNotices] = useState<VenueNotice[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await api<{ notices: VenueNotice[] }>("/api/v1/cr/venue-notices");
      setNotices(res.notices);
      setErr(null);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Failed to load heads-ups");
    }
  }, []);

  useEffect(() => { load(); }, [load, reloadKey]);

  async function clear(n: VenueNotice) {
    setBusy(n.id);
    try {
      await api(`/api/v1/cr/venue-notices/${n.id}`, { method: "DELETE" });
      toast.success(`Heads-up for ${n.venue} cleared`);
      await load();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Could not clear the heads-up");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section id="heads-ups" aria-labelledby="heads-ups-heading" className="scroll-mt-20 space-y-2">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 id="heads-ups-heading" className="text-[13px] font-semibold uppercase tracking-wider text-muted-foreground">
            Venue heads-ups
          </h2>
          <p className="text-xs text-muted-foreground">Let others know a room is needed so they leave on time.</p>
        </div>
        <VenueNoticeDialog
          defaultDay={defaultDay}
          onDone={load}
          trigger={
            <button
              type="button"
              className="flex h-10 shrink-0 items-center gap-1.5 rounded-xl border border-input bg-card px-3.5 text-sm font-semibold text-foreground transition hover:bg-muted"
            >
              <Plus className="size-4" aria-hidden /> Add
            </button>
          }
        />
      </div>

      {err && <p className="text-xs text-destructive">{err}</p>}
      {notices && notices.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-border bg-card/50 p-4 text-sm text-muted-foreground">
          No active heads-ups.
        </p>
      ) : (
        <ul className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
          {(notices ?? []).map((n) => (
            <li key={n.id} className="flex items-center gap-3 py-2.5 pl-3.5 pr-1.5">
              <BellRing className="size-5 shrink-0 text-warning" aria-hidden />
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold text-foreground">
                  {n.venue} needed at <span className="font-mono">{hm(n.start_time)}</span>
                  {n.end_time && <span className="font-mono">–{hm(n.end_time)}</span>}
                </span>
                <span className="block truncate text-xs text-muted-foreground">
                  {[DAY_SHORT[n.day_of_week] ?? "", n.cohort_code && `for ${n.cohort_code}`, n.note && `“${n.note}”`]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </span>
              <button
                type="button"
                disabled={busy === n.id}
                onClick={() => clear(n)}
                className="h-11 shrink-0 rounded-lg px-3 text-sm font-semibold text-primary transition hover:bg-muted disabled:opacity-50"
              >
                Clear
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
