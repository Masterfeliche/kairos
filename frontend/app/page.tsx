import SiteHeader from "@/components/student/SiteHeader";
import SiteFooter from "@/components/student/SiteFooter";
import MobileTabBar from "@/components/student/MobileTabBar";
import VersionBanner from "@/components/student/VersionBanner";
import ContinueCard from "@/components/student/ContinueCard";
import ProgrammePicker from "@/components/student/ProgrammePicker";
import { serverApi } from "@/lib/server-api";
import type { Programme, PublicVersion } from "@/lib/student";

export default async function HomePage() {
  const [programmes, version] = await Promise.all([
    serverApi<Programme[]>("/api/v1/programmes"),
    serverApi<PublicVersion>("/api/v1/versions/active"),
  ]);

  return (
    <div className="flex min-h-screen flex-col pb-20 md:pb-0">
      <SiteHeader />
      <main className="mx-auto w-full max-w-2xl flex-1 space-y-6 px-4 py-6 sm:py-10">
        <div>
          <h1 className="text-[1.625rem] font-bold leading-tight tracking-tight text-foreground sm:text-3xl">
            Your class timetable
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Official DIT teaching timetable · no login needed
          </p>
        </div>

        <ContinueCard />

        <section id="classes" aria-label="Find a class" className="scroll-mt-20">
          <ProgrammePicker programmes={programmes ?? []} />
        </section>

        <VersionBanner version={version} />
      </main>

      <SiteFooter />
      <MobileTabBar />
    </div>
  );
}
