"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api, ApiError, type Admin } from "@/lib/api";
import ThemeToggle from "@/components/theme-toggle";

const NAV = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/imports", label: "Imports" },
  { href: "/admin/history", label: "History" },
  { href: "/admin/audit", label: "Audit log" },
];

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

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-border bg-card/60 backdrop-blur">
        <div className="flex items-center justify-between px-4 py-3">
          <Link href="/admin" className="text-sm font-semibold text-foreground">
            DIT Smart Timetable <span className="text-primary">Admin</span>
          </Link>
          <div className="flex items-center gap-4 text-sm">
            {admin && (
              <span className="hidden text-muted-foreground sm:inline">
                {admin.email}{" "}
                <span className="badge bg-secondary text-secondary-foreground">{admin.role}</span>
              </span>
            )}
            <ThemeToggle />
            <button className="btn-ghost" onClick={logout}>
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="flex">
        <nav className="w-44 shrink-0 border-r border-sidebar-border bg-sidebar py-4 text-sidebar-foreground">
          <ul className="space-y-1 px-2">
            {NAV.map((item) => {
              const active =
                item.href === "/admin" ? pathname === "/admin" : pathname.startsWith(item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`block rounded-md px-3 py-2 text-sm font-medium ${
                      active
                        ? "bg-sidebar-primary/15 text-sidebar-primary"
                        : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <main className="min-w-0 flex-1 px-4 py-6">
          {checking ? (
            <p className="text-sm text-muted-foreground">Checking session...</p>
          ) : (
            children
          )}
        </main>
      </div>
    </div>
  );
}
