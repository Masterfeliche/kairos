import Link from "next/link";

export default function SiteFooter() {
  return (
    <footer className="border-t border-border/70 bg-card/40">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <p className="font-semibold text-foreground">DIT Smart Timetable</p>
          <p className="text-xs">Built from the official teaching timetable PDF · 2025/2026 Semester I.</p>
        </div>
        <nav className="flex flex-wrap gap-x-4 gap-y-1">
          <Link className="hover:text-foreground" href="/">Home</Link>
          <Link className="hover:text-foreground" href="/about">About</Link>
          <Link className="hover:text-foreground" href="/cr">Class rep</Link>
          <Link className="hover:text-foreground" href="/admin">Admin</Link>
        </nav>
      </div>
    </footer>
  );
}
