"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { History, LayoutDashboard, ListChecks, LogOut, Upload } from "lucide-react";
import { api, ApiError, type Admin } from "@/lib/api";
import { cn } from "@/lib/utils";
import ThemeToggle from "@/components/theme-toggle";

const NAV = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/imports", label: "Imports", icon: Upload },
  { href: "/admin/history", label: "History", icon: History },
  { href: "/admin/audit", label: "Audit log", icon: ListChecks },
];

const ROLE_LABEL: Record<string, string> = { owner: "Owner", admin: "Admin", reviewer: "Reviewer" };

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLogin = pathname === "/admin/login";
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [checking, setChecking] = useState(!isLogin);

  useEffect(() => {
    if (isLogin) return;
    let alive = true;
    api<Admin>("/api/v1/admin/auth/me")
      .then((me) => alive && setAdmin(me))
      .catch((err) => {
        if (!alive) return;
        if (err instanceof ApiError && err.status === 401) router.replace("/admin/login");
      })
      .finally(() => alive && setChecking(false));
    return () => {
      alive = false;
    };
  }, [isLogin, pathname, router]);

  async function logout() {
    try {
      await api("/api/v1/admin/auth/logout", { method: "POST" });
    } finally {
      router.replace("/admin/login");
    }
  }

  if (isLogin)
    return (
      <div className="relative min-h-screen bg-background text-foreground">
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>
        {children}
      </div>
    );

  const initials = admin?.email.slice(0, 2).toUpperCase() ?? "··";

  return (
    <div className="min-h-screen bg-background text-foreground md:flex">
      {/* Navy sidebar on desktop; a top bar with a scrolling tab row on phones. */}
      <aside className="z-40 bg-sidebar text-sidebar-foreground md:sticky md:top-0 md:flex md:h-screen md:w-60 md:shrink-0 md:flex-col md:px-3 md:py-5">
        <div className="flex items-center gap-2.5 px-4 pt-3 md:px-2 md:pt-0 md:pb-5">
          <span className="flex size-8 items-center justify-center rounded-[9px] bg-primary text-[11px] font-bold text-primary-foreground dark:bg-sidebar-primary dark:text-sidebar-primary-foreground">
            DIT
          </span>
          <Link href="/admin" className="flex flex-1 flex-col leading-tight">
            <span className="text-sm font-semibold">Smart Timetable</span>
            <span className="text-xs text-sidebar-foreground/65">Admin console</span>
          </Link>
          <div className="flex items-center md:hidden">
            <ThemeToggle className="size-11 hover:bg-sidebar-accent hover:text-sidebar-foreground" />
            <button
              type="button"
              onClick={logout}
              aria-label="Sign out"
              className="flex size-11 items-center justify-center rounded-lg hover:bg-sidebar-accent"
            >
              <LogOut className="size-5" aria-hidden />
            </button>
          </div>
        </div>

        <nav aria-label="Admin" className="overflow-x-auto px-2 pb-2 md:overflow-visible md:p-0">
          <ul className="flex gap-1 md:flex-col">
            {NAV.map((item) => {
              const active =
                item.href === "/admin"
                  ? pathname === "/admin" || pathname.startsWith("/admin/versions")
                  : pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <li key={item.href} className="shrink-0">
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex h-10 items-center gap-2.5 whitespace-nowrap rounded-[10px] px-3 text-sm transition",
                      active
                        ? "bg-sidebar-accent font-semibold text-sidebar-foreground"
                        : "font-medium text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-foreground",
                    )}
                  >
                    <Icon className="size-[18px]" aria-hidden />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="mt-auto hidden items-center gap-2.5 rounded-xl bg-sidebar-accent p-3 md:flex">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground dark:bg-sidebar-primary dark:text-sidebar-primary-foreground">
            {initials}
          </span>
          <span className="flex min-w-0 flex-1 flex-col leading-tight">
            <span className="truncate text-[13px] font-semibold">{admin?.email ?? "…"}</span>
            <span className="text-xs text-sidebar-foreground/65">{admin ? ROLE_LABEL[admin.role] ?? admin.role : ""}</span>
          </span>
          <ThemeToggle className="size-8 hover:bg-sidebar hover:text-sidebar-foreground" />
          <button
            type="button"
            onClick={logout}
            aria-label="Sign out"
            className="flex size-8 shrink-0 items-center justify-center rounded-lg hover:bg-sidebar"
          >
            <LogOut className="size-4" aria-hidden />
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-4 py-6 md:px-8 md:py-7">
        {checking ? (
          <p className="text-sm text-muted-foreground">Checking session…</p>
        ) : (
          children
        )}
      </main>
    </div>
  );
}
