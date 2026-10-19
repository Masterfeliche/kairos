import { notFound } from "next/navigation";
import SiteHeader from "@/components/student/SiteHeader";
import SiteFooter from "@/components/student/SiteFooter";
import MobileTabBar from "@/components/student/MobileTabBar";
import VersionBanner from "@/components/student/VersionBanner";
import VenueNoticeBanner from "@/components/student/VenueNoticeBanner";
import TimetableView from "@/components/timetable/TimetableView";
import ExportCalendarButton from "@/components/timetable/ExportCalendarButton";
import { serverApi } from "@/lib/server-api";
import { todayWeekday, type TimetableResponse, type VenueNotice } from "@/lib/student";

type Search = { day?: string; view?: string };

export default async function CohortPage({
  params,
  searchParams,
}: {
  params: Promise<{ cohort: string }>;
  searchParams: Promise<Search>;
}) {
  const { cohort } = await params;
  const sp = await searchParams;
  const code = decodeURIComponent(cohort).toUpperCase();

  const data = await serverApi<TimetableResponse>(
    `/api/v1/timetable?cohort_code=${encodeURIComponent(code)}`,
  );
  if (!data) notFound();

  const today = todayWeekday();
  const requestedDay = Number(sp.day);
  const day = requestedDay >= 1 && requestedDay <= 5 ? requestedDay : today;
  const week = sp.view === "week";

  const notices =
    (await serverApi<{ notices: VenueNotice[] }>(`/api/v1/venue-notices?day=${day}`))?.notices ?? [];
  const venues = new Set(
    data.sessions.filter((s) => s.day_of_week === day).map((s) => s.venue).filter(Boolean) as string[],
  );

  const now = new Date();
  const nowMinutes = now.getHours() * 60 + now.getMinutes();

  return (
    <div className="flex min-h-screen flex-col pb-16 md:pb-0">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 space-y-5 px-4 py-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Class</p>
            <h1 className="text-2xl font-bold text-foreground md:text-3xl">{data.cohort.code}</h1>
          </div>
          <ExportCalendarButton cohortCode={code} />
        </div>

        <VersionBanner version={data.version} />
        {!week && <VenueNoticeBanner notices={notices} venues={venues} />}

        <TimetableView
          sessions={data.sessions}
          basePath={`/c/${code}`}
          day={day}
          view={week ? "week" : "day"}
          today={today}
          nowMinutes={nowMinutes}
          sourceFilename={data.version.source_filename}
        />
      </main>
      <SiteFooter />
      <MobileTabBar />
    </div>
  );
}
