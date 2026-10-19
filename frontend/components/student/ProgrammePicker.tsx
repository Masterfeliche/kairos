"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Check, ChevronDown, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { LEVEL_ORDER, LEVEL_SHORT, type Programme } from "@/lib/student";

type Cohort = Programme["cohorts"][number];

/** One row in the picker: classes of a level that share a branch code (e.g. BEng · COE). */
type Group = { key: string; level: string; branch: string; cohorts: Cohort[] };

// BENG24COE-1 → branch "COE". Codes that don't follow the pattern keep their full code.
const CODE_RE = /^[A-Z]+\d{2}([A-Z]+)(?:-\d+)?$/;

function branchOf(code: string): string {
  return CODE_RE.exec(code)?.[1] ?? code;
}

function groupProgrammes(programmes: Programme[]): Group[] {
  const groups = new Map<string, Group>();
  for (const p of programmes) {
    for (const c of p.cohorts) {
      const branch = branchOf(c.code);
      const key = `${p.level}:${branch}`;
      if (!groups.has(key)) groups.set(key, { key, level: p.level, branch, cohorts: [] });
      groups.get(key)!.cohorts.push(c);
    }
  }
  const rank = (lvl: string) => (LEVEL_ORDER.indexOf(lvl) + 1 || 99);
  return [...groups.values()]
    .map((g) => ({ ...g, cohorts: g.cohorts.sort((a, b) => a.code.localeCompare(b.code)) }))
    .sort((a, b) => rank(a.level) - rank(b.level) || a.branch.localeCompare(b.branch));
}

export default function ProgrammePicker({ programmes }: { programmes: Programme[] }) {
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState<string>("all");
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    try {
      setSaved(localStorage.getItem("tt_cohort"));
    } catch {
      /* storage unavailable */
    }
  }, []);

  const groups = useMemo(() => groupProgrammes(programmes), [programmes]);
  const levels = LEVEL_ORDER.filter((l) => groups.some((g) => g.level === l));

  const q = query.trim().toUpperCase();
  const visible = useMemo(
    () =>
      groups
        .filter((g) => level === "all" || g.level === level)
        .map((g) => ({
          ...g,
          cohorts: q && !g.branch.includes(q) ? g.cohorts.filter((c) => c.code.includes(q)) : g.cohorts,
        }))
        .filter((g) => g.cohorts.length > 0),
    [groups, level, q],
  );

  // While searching, show matches without making people expand each row.
  const isOpen = (key: string) => Boolean(q) || open.has(key);
  function toggle(key: string) {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function remember(code: string) {
    try {
      localStorage.setItem("tt_cohort", code);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="space-y-3">
      <label htmlFor="find-class" className="block text-[13px] font-semibold uppercase tracking-wider text-muted-foreground">
        {saved ? "Find another class" : "Find your class"}
      </label>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 size-5 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <input
          id="find-class"
          type="search"
          inputMode="search"
          autoComplete="off"
          placeholder="Class code, e.g. COE or OD24CE-1"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="h-12 w-full rounded-2xl border border-input bg-card pl-11 pr-4 text-[15px] text-foreground outline-none transition placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/30"
        />
      </div>

      {levels.length > 1 && (
        <div role="group" aria-label="Level" className="flex flex-wrap gap-2">
          {["all", ...levels].map((l) => {
            const active = level === l;
            return (
              <button
                key={l}
                type="button"
                aria-pressed={active}
                onClick={() => setLevel(l)}
                className={cn(
                  "h-9 rounded-full border px-3.5 text-[13px] font-semibold transition",
                  active
                    ? "border-spotlight bg-spotlight text-spotlight-foreground"
                    : "border-input bg-card text-foreground hover:border-primary/50",
                )}
              >
                {l === "all" ? "All" : LEVEL_SHORT[l] ?? l}
              </button>
            );
          })}
        </div>
      )}

      {visible.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-border bg-card/50 p-5 text-sm text-muted-foreground">
          No class matches “{query}”. Try just the branch, like <span className="font-mono">COE</span>.
        </p>
      ) : (
        <ul className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
          {visible.map((g) => {
            const expanded = isOpen(g.key);
            const panelId = `cohorts-${g.key}`;
            return (
              <li key={g.key} className={cn(expanded && "bg-elevated")}>
                <button
                  type="button"
                  onClick={() => toggle(g.key)}
                  aria-expanded={expanded}
                  aria-controls={panelId}
                  className="flex min-h-16 w-full items-center gap-3 px-4 py-3 text-left"
                >
                  <span className="min-w-0 flex-1">
                    <span className="block font-mono text-[15px] font-semibold text-foreground">{g.branch}</span>
                    <span className="block text-xs text-muted-foreground">
                      {LEVEL_SHORT[g.level] ?? g.level} · {g.cohorts.length}{" "}
                      {g.cohorts.length === 1 ? "class" : "classes"}
                    </span>
                  </span>
                  <ChevronDown
                    className={cn("size-5 shrink-0 text-muted-foreground transition-transform", expanded && "rotate-180")}
                    aria-hidden
                  />
                </button>
                {expanded && (
                  <div id={panelId} className="grid grid-cols-2 gap-2 px-4 pb-4 sm:grid-cols-3">
                    {g.cohorts.map((c) => {
                      const mine = c.code === saved;
                      return (
                        <Link
                          key={c.id}
                          href={`/c/${c.code}`}
                          onClick={() => remember(c.code)}
                          className={cn(
                            "flex h-11 items-center justify-center gap-1.5 rounded-[10px] border font-mono text-sm font-semibold transition",
                            mine
                              ? "border-[1.5px] border-primary bg-primary/10 text-primary"
                              : "border-input bg-card text-foreground hover:border-primary hover:text-primary",
                          )}
                        >
                          {c.code}
                          {mine && <Check className="size-4" aria-label="your class" />}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
