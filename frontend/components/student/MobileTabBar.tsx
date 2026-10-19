"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, Home, Info, UserCog } from "lucide-react";

/** App-style bottom navigation, shown on phones only. */
export default function MobileTabBar() {
  const pathname = usePathname();
  const [cohort, setCohort] = useState<string | null>(null);

  useEffect(() => {
    setCohort(localStorage.getItem("tt_cohort"));
  }, []);

  const items = [
    { href: "/", label: "Home", icon: Home, match: (p: string) => p === "/" },
    {
      href: cohort ? `/c/${cohort}` : "/",
      label: "My class",
      icon: CalendarDays,
      match: (p: string) => p.startsWith("/c/"),
    },
    { href: "/cr", label: "Class rep", icon: UserCog, match: (p: string) => p.startsWith("/cr") },
    { href: "/about", label: "About", icon: Info, match: (p: string) => p === "/about" },
  ];

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border/70 bg-background/90 backdrop-blur-md md:hidden">
      <ul className="mx-auto flex max-w-md items-stretch justify-around px-2 pb-[env(safe-area-inset-bottom)]">
        {items.map((it) => {
          const active = it.match(pathname);
          const Icon = it.icon;
          return (
            <li key={it.label} className="flex-1">
              <Link
                href={it.href}
                className={`flex flex-col items-center gap-0.5 px-2 py-2 text-xs font-medium transition ${
                  active ? "text-primary" : "text-muted-foreground"
                }`}
              >
                <Icon className="size-5" />
                {it.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
