"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Calendar, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import ThemeToggle from "@/components/theme-toggle";
import { api, ApiError } from "@/lib/api";
import type { CrMe } from "@/lib/cr";

const NAV = [
  { href: "/cr", label: "My class", icon: Calendar },
  { href: "/cr/institute", label: "Institute", icon: Search },
];

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
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <Link href="/cr" className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">
              DIT
            </span>
            <span>Class Rep</span>
          </Link>
          <div className="flex items-center gap-1 text-sm">
            {me && (
              <span className="hidden text-muted-foreground sm:inline">
                {me.display_name || me.email} · {me.cohorts.map((c) => c.code).join(", ")}
              </span>
            )}
            <ThemeToggle />
            <Button variant="outline" size="sm" onClick={logout}>
              <LogOut className="size-3.5" /> <span className="hidden sm:inline">Sign out</span>
            </Button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 md:flex-row md:gap-6">
        <nav className="md:w-44 md:shrink-0">
          <ul className="flex gap-1 overflow-x-auto md:flex-col md:space-y-1">
            {NAV.map((item) => {
              const active = pathname === item.href;
              const Icon = item.icon;
              return (
                <li key={item.href} className="shrink-0">
                  <Link
                    href={item.href}
                    className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                      active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    <Icon className="size-4" /> {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <main className="min-w-0 flex-1">
          {checking ? <p className="text-sm text-muted-foreground">Checking session...</p> : children}
        </main>
      </div>
    </div>
  );
}
