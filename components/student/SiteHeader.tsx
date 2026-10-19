import Link from "next/link";
import ThemeToggle from "@/components/theme-toggle";

export default function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-card/90 backdrop-blur-md">
      <div className="mx-auto flex h-15 max-w-6xl items-center justify-between gap-3 px-4">
        <Link href="/" className="flex items-center gap-2.5 text-[15px] font-semibold text-foreground">
          <span className="flex size-8 items-center justify-center rounded-[9px] bg-sidebar text-[11px] font-bold text-sidebar-foreground">
            DIT
          </span>
          Smart Timetable
        </Link>

        <nav aria-label="Site" className="hidden items-center gap-1 text-sm font-medium text-muted-foreground md:flex">
          <NavLink href="/">Find class</NavLink>
          <NavLink href="/about">About</NavLink>
          <NavLink href="/cr">Class rep</NavLink>
        </nav>

        <ThemeToggle className="size-11" />
      </div>
    </header>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="flex h-10 items-center rounded-lg px-3 transition hover:bg-muted hover:text-foreground"
    >
      {children}
    </Link>
  );
}
