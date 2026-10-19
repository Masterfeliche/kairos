import Link from "next/link";
import { ArrowRight, CalendarDays, Radio, RotateCcw, BellRing, DoorOpen, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import AppPreview from "@/components/landing/AppPreview";

const FEATURES = [
  {
    icon: CalendarDays,
    title: "Today & full week",
    body: "A clean day view with free-time gaps, plus an aligned week grid you can scan at a glance.",
  },
  {
    icon: Radio,
    title: "Live class status",
    body: "Class reps mark sessions live, ended or not held, so you always know what's happening now.",
  },
  {
    icon: RotateCcw,
    title: "Instant reschedules",
    body: "When a room or time changes, the update appears immediately for the whole class.",
  },
  {
    icon: DoorOpen,
    title: "Find a free room",
    body: "Class reps can see which venues are open and plan a move in seconds.",
  },
  {
    icon: BellRing,
    title: "Venue heads-up",
    body: "Know when to leave a room, and never walk into a venue that's about to be taken.",
  },
  {
    icon: Moon,
    title: "Dark by default",
    body: "Easy on the eyes at night, with a one-tap light mode. Built mobile-first for phones.",
  },
];

export default function Hero() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 pb-8 pt-12 sm:pt-16 lg:grid-cols-2 lg:gap-8 lg:pb-20 lg:pt-24">
          <div className="animate-rise text-center lg:text-left">
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur">
              <span className="size-1.5 rounded-full bg-success" />
              Official DIT teaching timetable · 2025/2026 Semester I
            </span>

            <h1 className="mt-5 text-balance text-4xl font-semibold leading-tight tracking-tight text-foreground sm:text-5xl lg:text-6xl">
              Your class timetable
            </h1>

            <p className="mx-auto mt-4 max-w-xl text-pretty text-base text-muted-foreground sm:text-lg lg:mx-0">
              Always in your pocket — see today&apos;s lectures, labs and free periods, with no login.
              Class reps keep it live so you never miss a change.
            </p>

            <div className="mt-7 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-center lg:justify-start">
              <Button asChild size="lg" className="h-11">
                <Link href="#classes">
                  Find my class <ArrowRight className="size-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="h-11">
                <Link href="/cr">I&apos;m a class rep</Link>
              </Button>
            </div>

            <p className="mt-4 text-xs text-muted-foreground">
              Read-only for students · no account needed
            </p>
          </div>

          <div className="animate-rise lg:pl-6">
            <AppPreview />
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-4 py-12 sm:py-16">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
            Built for how students actually use phones
          </h2>
          <p className="mt-2 text-muted-foreground">
            Everything you need to get to the right room at the right time — and nothing you don&apos;t.
          </p>
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="rounded-2xl border border-border bg-card p-5 transition hover:border-primary/40"
              >
                <Icon className="size-5 text-primary" />
                <h3 className="mt-3 font-semibold text-foreground">{f.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{f.body}</p>
              </div>
            );
          })}
        </div>
      </section>
    </>
  );
}
