"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import VersionBanner from "@/components/student/VersionBanner";
import VenueNoticeBanner from "@/components/student/VenueNoticeBanner";
import TimetableView from "@/components/timetable/TimetableView";
import CrDayView from "@/components/cr/CrDayView";
import SessionActions from "@/components/cr/SessionActions";
import NoticesPanel from "@/components/cr/NoticesPanel";
import { api, ApiError } from "@/lib/api";
import { toMin, type PublicSession, type VenueNotice } from "@/lib/student";
import { campusNow, fmtClock } from "@/lib/time";
import type { CrTimetable } from "@/lib/cr";

export default function CrPage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Loading timetable…</p>}>
      <CrContent />
    </Suspense>
  );
}

function CrContent() {
  const sp = useSearchParams();
  const [clock] = useState(() => campusNow());
  const requestedDay = Number(sp.get("day"));
  const day = requestedDay >= 1 && requestedDay <= 5 ? requestedDay : clock.today || 1;
  const week = sp.get("view") === "week";

  const [data, setData] = useState<CrTimetable | null>(null);
  const [cohort, setCohort] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [notices, setNotices] = useState<VenueNotice[]>([]);
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async (cohortCode?: string) => {
    setError(null);
    try {
      const params = cohortCode ? `?cohort_code=${encodeURIComponent(cohortCode)}` : "";
      const res = await api<CrTimetable>(`/api/v1/cr/timetable${params}`);
      setData(res);
      setCohort(cohortCode || res.cohort.code || res.my_cohorts[0]?.code || "");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load timetable");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    let cancelled = false;
    api<{ notices: VenueNotice[] }>(`/api/v1/venue-notices?day=${day}`)
      .then((r) => { if (!cancelled) setNotices(r.notices); })
      .catch(() => { /* heads-ups are optional */ });
    return () => { cancelled = true; };
  }, [day, reloadKey]);

  const reload = useCallback(() => {
    load(cohort);
    setReloadKey((k) => k + 1);
  }, [cohort, load]);

  const moveSession = useCallback(
    async (s: PublicSession, toDay: number, startMin: number) => {
      const duration = toMin(s.end_time) - toMin(s.start_time);
      try {
        await api(`/api/v1/cr/sessions/${s.id}/reschedule`, {
          method: "POST",
          body: JSON.stringify({
            day_of_week: toDay,
            start_time: fmtClock(startMin),
            end_time: fmtClock(startMin + duration),
          }),
        });
        toast.success(`${s.course_name} moved for this week`);
        reload();
      } catch (e) {
        toast.error(e instanceof ApiError ? e.message : "Could not move the class");
      }
    },
    [reload],
  );

  const swapSessions = useCallback(
    async (s: PublicSession, target: PublicSession) => {
      try {
        await api(`/api/v1/cr/sessions/${s.id}/swap`, {
          method: "POST",
          body: JSON.stringify({ with_session_id: target.id }),
        });
        toast.success(`Swapped ${s.course_name} and ${target.course_name} for this week`);
        reload();
      } catch (e) {
        toast.error(e instanceof ApiError ? e.message : "Could not swap the classes");
      }
    },
    [reload],
  );

  if (error) {
    return <p className="rounded-2xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">{error}</p>;
  }
  if (!data) return <p className="text-sm text-muted-foreground">Loading timetable…</p>;

  const venues = new Set(
    data.sessions.filter((s) => s.day_of_week === day).map((s) => s.venue).filter(Boolean) as string[],
  );
  const banner = <VenueNoticeBanner notices={notices} venues={venues} />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Class</span>
          {data.my_cohorts.length > 1 ? (
            <Select value={cohort} onValueChange={(v) => { setCohort(v); load(v); }}>
              <SelectTrigger className="h-10 w-[180px] font-mono font-semibold" aria-label="Choose class">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {data.my_cohorts.map((c) => (
                  <SelectItem key={c.code} value={c.code} className="font-mono">{c.code}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <span className="font-mono font-semibold text-foreground">{data.cohort.code}</span>
          )}
        </div>
        <VersionBanner version={data.version} />
      </div>

      {week ? (
        <TimetableView
          sessions={data.sessions}
          basePath="/cr"
          day={day}
          view="week"
          clock={clock}
          sourceFilename={data.version.source_filename ?? null}
          onMove={moveSession}
          onSwap={swapSessions}
          renderActions={(s: PublicSession) => (
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-muted-foreground">Class rep actions</span>
              <SessionActions session={s} siblings={data.sessions} onChanged={reload} layout="menu" />
            </div>
          )}
        />
      ) : (
        <CrDayView sessions={data.sessions} day={day} clock={clock} banner={banner} onChanged={reload} />
      )}

      <NoticesPanel reloadKey={reloadKey} defaultDay={clock.today || day} />
    </div>
  );
}
