import Link from "next/link";
import { cn } from "@/lib/utils";
import { DAY_SHORT, DAYS } from "@/lib/student";
import type { CampusNow } from "@/lib/time";

function link(basePath: string, params: string): string {
  return `${basePath}?${params}`;
}

/** Day / Week segmented switch. */
export function ViewSwitch({ basePath, day, week }: { basePath: string; day: number; week: boolean }) {
  return (
    <nav aria-label="View" className="flex rounded-xl bg-secondary p-1 text-sm font-semibold">
      <ViewTab href={link(basePath, `day=${day}`)} active={!week}>Day</ViewTab>
      <ViewTab href={link(basePath, "view=week")} active={week}>Week</ViewTab>
    </nav>
  );
}

function ViewTab({ href, active, children }: { href: string; active: boolean; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      prefetch={false}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex h-9 items-center rounded-lg px-4 transition",
        active
          ? "bg-card text-foreground shadow-sm"
          : "text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </Link>
  );
}

/** Mon–Fri buttons with dates; today is labelled, the viewed day is filled. */
export function DayStrip({ basePath, day, now }: { basePath: string; day: number; now: CampusNow }) {
  return (
    <nav aria-label="Choose day" className="grid grid-cols-5 gap-2">
      {[1, 2, 3, 4, 5].map((d) => {
        const selected = d === day;
        const isToday = d === now.today;
        return (
          <Link
            key={d}
            prefetch={false}
            href={link(basePath, `day=${d}`)}
            aria-current={selected ? "date" : undefined}
            aria-label={`${DAYS[d]} ${now.weekLabels[d]}${isToday ? ", today" : ""}`}
            className={cn(
              "flex h-16 flex-col items-center justify-center rounded-2xl border transition",
              selected
                ? "border-spotlight bg-spotlight text-spotlight-foreground"
                : "border-border bg-card text-muted-foreground hover:border-primary/40",
            )}
          >
            <span className={cn("text-xs font-medium", selected && "text-spotlight-muted", isToday && !selected && "font-semibold text-primary")}>
              {isToday ? "Today" : DAY_SHORT[d]}
            </span>
            <span className={cn("font-mono text-lg font-semibold tabular-nums", selected ? "text-spotlight-foreground" : "text-foreground")}>
              {now.weekDates[d]}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
