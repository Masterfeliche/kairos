import SiteHeader from "@/components/student/SiteHeader";
import SiteFooter from "@/components/student/SiteFooter";
import MobileTabBar from "@/components/student/MobileTabBar";
import VersionBanner from "@/components/student/VersionBanner";
import ContinueCard from "@/components/student/ContinueCard";
import ProgrammePicker from "@/components/student/ProgrammePicker";
import Hero from "@/components/landing/Hero";
import { serverApi } from "@/lib/server-api";
import type { Programme, PublicVersion } from "@/lib/student";

export default async function HomePage() {
  const [programmes, version] = await Promise.all([
    serverApi<Programme[]>("/api/v1/programmes"),
    serverApi<PublicVersion>("/api/v1/versions/active"),
  ]);

  return (
    <div className="flex min-h-screen flex-col pb-16 md:pb-0">
      <SiteHeader />
      <main className="flex-1">
        <Hero />

        {/* Class finder */}
        <section id="classes" className="border-t border-border/70 bg-card/30">
          <div className="mx-auto max-w-3xl scroll-mt-20 px-4 py-12 sm:py-16">
            <div className="text-center">
              <h2 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                Find your class
              </h2>
              <p className="mt-2 text-muted-foreground">
                Choose your programme and section to open the timetable.
              </p>
            </div>

            <div className="mt-8 space-y-4">
              <VersionBanner version={version} />
              <ContinueCard />
              <ProgrammePicker programmes={programmes ?? []} />
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
      <MobileTabBar />
    </div>
  );
}
