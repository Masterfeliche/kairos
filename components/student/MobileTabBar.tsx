"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { CalendarDays, Clock, Ellipsis, Search } from "lucide-react";
import { cn } from "@/lib/utils";

/** App-style bottom navigation, shown on phones only. */
export default function MobileTabBar() {
  return (
    <Suspense fallback={null}>
      <TabBar />
    </Suspense>
  );
}

function TabBar() {
  const pathname = usePathname();
  const isWeek = useSearchParams().get("view") === "week";
  const [cohort, setCohort] = useState<string | null>(null);

  useEffect(() => {
    try {
      setCohort(localStorage.getItem("tt_cohort"));
    } catch {
      /* storage unavailable */
    }
  }, []);

  // On a class page, Today/Week stay on that class; elsewhere they open the saved class.
  const onClass = pathname.startsWith("/c/");
  const classPath = onClass ? pathname : cohort ? `/c/${cohort}` : null;

  const items = [
    {
      href: classPath ?? "/#classes",
      label: "Today",
      icon: Clock,
      active: onClass && !isWeek,
    },
    {
      href: classPath ? `${classPath}?view=week` : "/#classes",
      label: "Week",
      icon: CalendarDays,
      active: onClass && isWeek,
    },
    { href: "/#classes", label: "Classes", icon: Search, active: pathname === "/" },
    { href: "/about", label: "More", icon: Ellipsis, active: pathname === "/about" },
  ];

  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 backdrop-blur-md md:hidden"
    >
      <ul className="mx-auto grid max-w-md grid-cols-4 pb-[env(safe-area-inset-bottom)]">
        {items.map((it) => {
          const Icon = it.icon;
          return (
            <li key={it.label}>
              <Link
                href={it.href}
                prefetch={false}
                aria-current={it.active ? "page" : undefined}
                className={cn(
                  "flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-semibold transition",
                  it.active ? "text-primary" : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="size-5" aria-hidden />
                {it.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
