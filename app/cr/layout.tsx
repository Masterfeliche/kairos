"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { BellRing, CalendarDays, Clock, LogOut, MapPin } from "lucide-react";
import ThemeToggle from "@/components/theme-toggle";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CrMe } from "@/lib/cr";

export default function CrShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLogin = pathname === "/cr/login";
  const [me, setMe] = useState<CrMe | null>(null);
  const [checking, setChecking] = useState(!isLogin);

  useEffect(() => {
    if (isLogin) return;
    let alive = true;
    api<CrMe>("/api/v1/cr/auth/me")
      .then((v) => alive && setMe(v))
      .catch((err) => {
        if (!alive) return;
        if (err instanceof ApiError && err.status === 401) router.replace("/cr/login");
      })
      .finally(() => alive && setChecking(false));
    return () => { alive = false; };
  }, [isLogin, pathname, router]);

  async function logout() {
    try { await api("/api/v1/cr/auth/logout", { method: "POST" }); } finally { router.replace("/cr/login"); }
  }

  if (isLogin) return <>{children}</>;

  return (
    <div className="min-h-screen pb-20 md:pb-0">
      <header className="sticky top-0 z-40 bg-spotlight text-spotlight-foreground">
        <div className="mx-auto flex h-15 max-w-6xl items-center gap-3 px-4">
          <Link href="/cr" className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-[9px] bg-primary text-[11px] font-bold text-primary-foreground dark:bg-sidebar-primary dark:text-sidebar-primary-foreground">
              DIT
            </span>
            <span className="flex flex-col leading-tight">
              <span className="text-[11px] font-semibold tracking-wider text-spotlight-muted">CLASS REP</span>
              <span className="text-sm font-semibold">{me ? me.display_name || me.email : "Smart Timetable"}</span>
            </span>
          </Link>

          <Suspense fallback={null}>
            <DesktopNav />
          </Suspense>

          <span className="flex-1" />
          <ThemeToggle className="size-11 text-spotlight-foreground hover:bg-spotlight-accent hover:text-spotlight-foreground" />
          <button
            type="button"
            onClick={logout}
            aria-label="Sign out"
            className="flex size-11 items-center justify-center rounded-lg transition hover:bg-spotlight-accent"
          >
            <LogOut className="size-5" aria-hidden />
          </button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl px-4 py-5 sm:py-6 lg:max-w-5xl">
        {checking ? <p className="text-sm text-muted-foreground">Checking session…</p> : children}
      </main>

      <Suspense fallback={null}>
        <CrTabBar />
      </Suspense>
    </div>
  );
}

function useNavItems() {
  const pathname = usePathname();
  const isWeek = useSearchParams().get("view") === "week";
  const onToday = pathname === "/cr";
  return [
    { href: "/cr", label: "Today", icon: Clock, active: onToday && !isWeek },
    { href: "/cr?view=week", label: "Week", icon: CalendarDays, active: onToday && isWeek },
    { href: "/cr/institute", label: "Rooms", icon: MapPin, active: pathname === "/cr/institute" },
    { href: "/cr#heads-ups", label: "Heads-ups", icon: BellRing, active: false },
  ];
}

function DesktopNav() {
  const items = useNavItems();
  return (
    <nav aria-label="Class rep" className="ml-4 hidden items-center gap-1 text-sm font-medium md:flex">
      {items.map((it) => (
        <Link
          key={it.label}
          href={it.href}
          aria-current={it.active ? "page" : undefined}
          className={cn(
            "flex h-10 items-center rounded-lg px-3 transition",
            it.active ? "bg-spotlight-accent text-spotlight-foreground" : "text-spotlight-muted hover:text-spotlight-foreground",
          )}
        >
          {it.label}
        </Link>
      ))}
    </nav>
  );
}

function CrTabBar() {
  const items = useNavItems();
  return (
    <nav
      aria-label="Class rep"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 backdrop-blur-md md:hidden"
    >
      <ul className="mx-auto grid max-w-md grid-cols-4 pb-[env(safe-area-inset-bottom)]">
        {items.map((it) => {
          const Icon = it.icon;
          return (
            <li key={it.label}>
              <Link
                href={it.href}
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
