"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { LEVEL_LABELS, LEVEL_ORDER, type Programme } from "@/lib/student";

export default function ProgrammePicker({ programmes }: { programmes: Programme[] }) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return programmes;
    return programmes
      .map((p) => ({
        ...p,
        cohorts: p.cohorts.filter((c) => c.code.toLowerCase().includes(q)),
      }))
      .filter(
        (p) =>
          p.cohorts.length > 0 ||
          p.name.toLowerCase().includes(q) ||
          p.code.toLowerCase().includes(q),
      );
  }, [programmes, query]);

  const byLevel = useMemo(() => {
    const groups: Record<string, Programme[]> = {};
    for (const p of filtered) (groups[p.level] ??= []).push(p);
    return groups;
  }, [filtered]);

  function remember(code: string) {
    try {
      localStorage.setItem("tt_cohort", code);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="search">Find your class</Label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="search"
            className="pl-8"
            placeholder="Search programme or cohort, e.g. OD24COE"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      {LEVEL_ORDER.filter((lvl) => byLevel[lvl]?.length).map((level) => (
        <section key={level} className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {LEVEL_LABELS[level] ?? level}
          </h2>
          <div className="space-y-2">
            {byLevel[level].map((p) => (
              <details
                key={p.id}
                className="card"
                open={p.cohorts.some((c) => c.code === query.toUpperCase())}
              >
                <summary className="cursor-pointer list-none font-medium text-foreground">
                  {p.name}
                  <span className="ml-2 text-xs text-muted-foreground">{p.cohorts.length} classes</span>
                </summary>
                <div className="mt-3 flex flex-wrap gap-2">
                  {p.cohorts.map((c) => (
                    <Link key={c.id} href={`/c/${c.code}`} onClick={() => remember(c.code)}>
                      <Badge
                        variant="outline"
                        className="h-auto px-3 py-1.5 text-sm hover:border-primary hover:text-primary"
                      >
                        {c.code}
                      </Badge>
                    </Link>
                  ))}
                </div>
              </details>
            ))}
          </div>
        </section>
      ))}

      {filtered.length === 0 && (
        <p className="text-sm text-muted-foreground">No programme or class matches “{query}”.</p>
      )}
    </div>
  );
}
