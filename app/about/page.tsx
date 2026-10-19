import Link from "next/link";
import SiteHeader from "@/components/student/SiteHeader";
import SiteFooter from "@/components/student/SiteFooter";
import MobileTabBar from "@/components/student/MobileTabBar";
import { Button } from "@/components/ui/button";
import { CalendarDays, Radio, RotateCcw, DoorOpen, BellRing } from "lucide-react";

const POINTS = [
  { icon: CalendarDays, title: "Read-only for students", body: "No account needed — just pick your class and go." },
  { icon: Radio, title: "Live class status", body: "Class reps mark sessions live, ended or not held." },
  { icon: RotateCcw, title: "Reschedules", body: "Time and venue changes appear immediately for the class." },
  { icon: BellRing, title: "Venue heads-up", body: "Know when a room is about to be needed so you can leave in time." },
  { icon: DoorOpen, title: "Free-room finder", body: "Class reps can locate an open venue across the institute in seconds." },
];

export default function AboutPage() {
  return (
    <div className="flex min-h-screen flex-col pb-16 md:pb-0">
      <SiteHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 space-y-6 px-4 py-8">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">About</h1>
          <p className="text-muted-foreground">
            Teaching timetable built from the official DIT timetable PDF, designed mobile-first for students.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {POINTS.map((p) => {
            const Icon = p.icon;
            return (
              <div key={p.title} className="rounded-2xl border border-border bg-card p-4">
                <Icon className="size-5 text-primary" />
                <h2 className="mt-3 font-semibold text-foreground">{p.title}</h2>
                <p className="mt-1 text-sm text-muted-foreground">{p.body}</p>
              </div>
            );
          })}
        </div>

        <div className="card space-y-2 text-sm text-muted-foreground">
          <p>
            Class representatives have a separate area to mark sessions live, reschedule when changes occur,
            and post venue heads-ups. Admins import new versions, review, correct, and publish/rollback.
          </p>
          <p>
            Missing values are shown honestly as &ldquo;Not provided&rdquo; — nothing is guessed.
          </p>
          <div className="pt-1">
            <Button asChild variant="outline" size="sm">
              <Link href="/cr">Open Class Rep area</Link>
            </Button>
          </div>
        </div>
      </main>
      <SiteFooter />
      <MobileTabBar />
    </div>
  );
}
