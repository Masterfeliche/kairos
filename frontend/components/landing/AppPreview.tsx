import { courseAccentStyle } from "@/lib/student";

const DEMO = [
  { time: "08:00", code: "COE 1101", name: "Engineering Mathematics I", venue: "LR 12", type: "Lecture", live: false },
  { time: "10:00", code: "COE 1103", name: "Web Application Development", venue: "Multimedia Lab 1", type: "Practical", live: true },
  { time: "12:00", code: "COE 1105", name: "Digital Electronics", venue: "E2 LAB 1", type: "Lecture", live: false },
];

/** A phone mockup with a mini timetable, inspired by modern timetable apps. */
export default function AppPreview() {
  return (
    <div className="relative mx-auto w-[290px] max-w-full">
      <div className="rounded-[2.5rem] border border-border bg-card p-2.5 shadow-lg">
        <div className="rounded-[2rem] bg-background p-4">
          <div className="mx-auto mb-4 h-1.5 w-16 rounded-full bg-muted" aria-hidden />

          <div className="mb-3 flex items-end justify-between">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Today</p>
              <p className="text-lg font-semibold text-foreground">Monday</p>
            </div>
            <span className="inline-flex items-center gap-1 rounded-full bg-success/15 px-2 py-1 text-[10px] font-semibold text-success">
              <span className="size-1.5 animate-pulse rounded-full bg-success" /> Live now
            </span>
          </div>

          <div className="mb-4 flex gap-1.5">
            {["M", "T", "W", "T", "F"].map((d, i) => (
              <span
                key={d + i}
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ${
                  i === 0 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                }`}
              >
                {d}
              </span>
            ))}
          </div>

          <div className="space-y-2.5">
            {DEMO.map((s) => (
              <div
                key={s.code}
                className="flex gap-3 rounded-xl border border-border border-l-4 p-3"
                style={courseAccentStyle(s.code)}
              >
                <div className="w-10 shrink-0 text-xs font-semibold tabular-nums text-foreground">
                  {s.time}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-foreground">{s.name}</p>
                  <p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                    <span className="font-mono">{s.code}</span>
                    <span>· {s.venue}</span>
                  </p>
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                      {s.type}
                    </span>
                    {s.live && (
                      <span className="rounded-full bg-success/15 px-1.5 py-0.5 text-[10px] font-semibold text-success">
                        Live
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
