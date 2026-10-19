import Link from "next/link";
import { notFound } from "next/navigation";
import SiteHeader from "@/components/student/SiteHeader";
import SiteFooter from "@/components/student/SiteFooter";
import MobileTabBar from "@/components/student/MobileTabBar";
import VersionBanner from "@/components/student/VersionBanner";
import VenueNoticeBanner from "@/components/student/VenueNoticeBanner";
import TimetableView from "@/components/timetable/TimetableView";
import ExportCalendarButton from "@/components/timetable/ExportCalendarButton";
import { serverApi } from "@/lib/server-api";
import { campusNow } from "@/lib/time";
import type { TimetableResponse, VenueNotice } from "@/lib/student";

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

  // Campus time (EAT), not the server's clock. At weekends nothing is "today"; open Monday.
  const clock = campusNow();
  const requestedDay = Number(sp.day);
  const day = requestedDay >= 1 && requestedDay <= 5 ? requestedDay : clock.today || 1;
  const week = sp.view === "week";

  const notices =
    (await serverApi<{ notices: VenueNotice[] }>(`/api/v1/venue-notices?day=${day}`))?.notices ?? [];
  const venues = new Set(
    data.sessions.filter((s) => s.day_of_week === day).map((s) => s.venue).filter(Boolean) as string[],
  );

  return (
    <div className="flex min-h-screen flex-col pb-20 md:pb-0">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 space-y-5 px-4 py-5 sm:py-6">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium text-muted-foreground">My class</p>
            <div className="flex items-baseline gap-3">
              <h1 className="font-mono text-xl font-semibold text-foreground sm:text-2xl">{data.cohort.code}</h1>
              <Link href="/#classes" className="text-sm font-medium text-primary hover:underline">
                Change
              </Link>
            </div>
          </div>
          <ExportCalendarButton cohortCode={code} />
        </div>

        <VersionBanner version={data.version} />

        <TimetableView
          sessions={data.sessions}
          basePath={`/c/${code}`}
          day={day}
          view={week ? "week" : "day"}
          clock={clock}
          sourceFilename={data.version.source_filename}
          dayBanner={<VenueNoticeBanner notices={notices} venues={venues} />}
        />
      </main>
      <SiteFooter />
      <MobileTabBar />
    </div>
  );
}
