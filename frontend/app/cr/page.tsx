"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import VersionBanner from "@/components/student/VersionBanner";
import VenueNoticeBanner from "@/components/student/VenueNoticeBanner";
import TimetableView from "@/components/timetable/TimetableView";
import SessionControls from "@/components/cr/SessionControls";
import NoticesPanel from "@/components/cr/NoticesPanel";
import { api, ApiError } from "@/lib/api";
import { toMin, type PublicSession, type VenueNotice } from "@/lib/student";
import { campusNow } from "@/lib/time";
import type { CrTimetable } from "@/lib/cr";

export default function CrPage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Loading timetable...</p>}>
      <CrContent />
    </Suspense>
  );
}

function CrContent() {
  const sp = useSearchParams();
  const [clock] = useState(() => campusNow());
  const requestedDay = Number(sp.get("day"));
  const day = requestedDay >= 1 && requestedDay <= 5 ? requestedDay : clock.today || 1;
  const view = sp.get("view") === "week" ? "week" : "day";

  const [data, setData] = useState<CrTimetable | null>(null);
  const [cohort, setCohort] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notices, setNotices] = useState<VenueNotice[]>([]);
  const [reloadKey, setReloadKey] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async (cohortCode?: string) => {
    setLoading(true);
    setError(null);
    try {
      const params = cohortCode ? `?cohort_code=${encodeURIComponent(cohortCode)}` : "";
      const res = await api<CrTimetable>(`/api/v1/cr/timetable${params}`);
      setData(res);
      const next = cohortCode || cohort || res.my_cohorts[0]?.code || "";
      setCohort(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load timetable");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    let cancelled = false;
    api<{ notices: VenueNotice[] }>(`/api/v1/venue-notices?day=${day}`)
      .then((r) => { if (!cancelled) setNotices(r.notices); })
      .catch(() => { /* ignore */ });
    return () => { cancelled = true; };
  }, [day, reloadKey]);

  const reload = useCallback(() => {
    load(cohort);
    setReloadKey((k) => k + 1);
  }, [cohort, load]);

  const moveSession = useCallback(
    async (s: PublicSession, day: number, startMin: number) => {
      setActionError(null);
      const duration = toMin(s.end_time) - toMin(s.start_time);
      try {
        await api(`/api/v1/cr/sessions/${s.id}/reschedule`, {
          method: "POST",
          body: JSON.stringify({
            day_of_week: day,
            start_time: fmtMin(startMin),
            end_time: fmtMin(startMin + duration),
          }),
        });
        reload();
      } catch (e) {
        setActionError(e instanceof ApiError ? e.message : "Could not move the class");
      }
    },
    [reload],
  );

  const swapSessions = useCallback(
    async (s: PublicSession, target: PublicSession) => {
      setActionError(null);
      try {
        await api(`/api/v1/cr/sessions/${s.id}/swap`, {
          method: "POST",
          body: JSON.stringify({ with_session_id: target.id }),
        });
        reload();
      } catch (e) {
        setActionError(e instanceof ApiError ? e.message : "Could not swap the classes");
      }
    },
    [reload],
  );

  const venues = new Set(
    (data?.sessions ?? [])
      .filter((s) => s.day_of_week === day)
      .map((s) => s.venue)
      .filter(Boolean) as string[],
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground md:text-3xl">My class timetable</h1>
          <p className="text-sm text-muted-foreground">
            Same view as students, plus controls to mark live, reschedule, and post venue heads-ups.
          </p>
        </div>
        {data && data.my_cohorts.length > 1 && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Cohort</span>
            <Select value={cohort} onValueChange={(v) => { setCohort(v); load(v); }}>
              <SelectTrigger className="w-[170px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                {data.my_cohorts.map((c) => (
                  <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      {error && <Card className="p-4 text-sm text-destructive">{error}</Card>}
      {actionError && <Card className="p-3 text-sm text-destructive">{actionError}</Card>}
      {loading && !data && <p className="text-sm text-muted-foreground">Loading...</p>}

      {data && (
        <>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Class</p>
            <h2 className="text-2xl font-semibold text-foreground">{data.cohort.code}</h2>
          </div>

          <VersionBanner version={data.version} />

          <TimetableView
            sessions={data.sessions}
            basePath="/cr"
            day={day}
            view={view}
            clock={clock}
            dayBanner={<VenueNoticeBanner notices={notices} venues={venues} />}
            sourceFilename={data.version.source_filename ?? null}
            onMove={moveSession}
            onSwap={swapSessions}
            renderActions={(s: PublicSession) => (
              <SessionControls session={s} siblings={data.sessions} onChanged={reload} />
            )}
          />

          <NoticesPanel reloadKey={reloadKey} />
        </>
      )}
    </div>
  );
}

function fmtMin(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}
