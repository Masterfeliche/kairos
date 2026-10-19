"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, DAYS } from "@/lib/api";

type Diff = {
  version_id: string;
  base_version_id: string | null;
  added: DiffRow[];
  removed: DiffRow[];
  changed: {
    key: string;
    session_id: string;
    source_page: number;
    course_code_raw: string | null;
    cohort_codes: string[];
    fields: Record<string, { from: unknown; to: unknown }>;
  }[];
  summary: { added: number; removed: number; changed: number };
};

type DiffRow = {
  day_of_week: number;
  start_time: string;
  course_code_raw: string | null;
  course_name_raw: string;
  cohort_codes: string[];
  source_page: number;
};

function describe(r: DiffRow) {
  return `${DAYS[r.day_of_week] ?? r.day_of_week} ${r.start_time.slice(0, 5)} · ${r.course_code_raw ?? "(no code)"} · ${r.course_name_raw}`;
}

export default function DiffPage() {
  const { id } = useParams<{ id: string }>();
  const [diff, setDiff] = useState<Diff | null>(null);

  useEffect(() => {
    api<Diff>(`/api/v1/admin/versions/${id}/diff`).then(setDiff).catch(() => {});
  }, [id]);

  if (!diff) return <p className="text-sm text-muted-foreground">Loading diff...</p>;

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold md:text-3xl">Diff vs active version</h1>
      <p className="text-sm text-muted-foreground">
        {diff.base_version_id ? (
          <>Compared with active version <code className="text-xs">{diff.base_version_id}</code></>
        ) : (
          "No active version - every session is new."
        )}
      </p>

      <div className="grid grid-cols-3 gap-3">
        <Stat label="Added" value={diff.summary.added} tone="success" />
        <Stat label="Removed" value={diff.summary.removed} tone="destructive" />
        <Stat label="Changed" value={diff.summary.changed} tone="warning" />
      </div>

      <Section title="Changed" empty="No changed sessions.">
        {diff.changed.map((c) => (
          <li key={c.key} className="px-4 py-2 text-sm">
            <span className="text-muted-foreground">p{c.source_page}</span>{" "}
            <span className="font-medium">{c.course_code_raw ?? "(no code)"}</span>
            <ul className="mt-1 space-y-0.5 text-muted-foreground text-xs">
              {Object.entries(c.fields).map(([field, v]) => (
                <li key={field}>
                  <span className="font-mono">{field}</span>:{" "}
                  <span className="text-destructive line-through">{String(v.from)}</span>{" "}
                  &rarr; <span className="text-success">{String(v.to)}</span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </Section>

      <Section title="Added" empty="No added sessions.">
        {diff.added.map((r, i) => (
          <li key={i} className="px-4 py-2 text-sm">
            <span className="text-muted-foreground">p{r.source_page}</span> {describe(r)}
          </li>
        ))}
      </Section>

      <Section title="Removed" empty="No removed sessions.">
        {diff.removed.map((r, i) => (
          <li key={i} className="px-4 py-2 text-sm text-destructive">
            <span className="text-muted-foreground">p{r.source_page}</span> {describe(r)}
          </li>
        ))}
      </Section>
    </div>
  );
}

const TONES: Record<string, string> = {
  success: "text-success",
  destructive: "text-destructive",
  warning: "text-warning",
};

function Stat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="card">
      <p className="text-muted-foreground text-xs font-medium uppercase">{label}</p>
      <p className={`text-2xl font-semibold tabular-nums ${TONES[tone]}`}>{value}</p>
    </div>
  );
}

function Section({ title, empty, children }: { title: string; empty: string; children: React.ReactNode }) {
  const items = Array.isArray(children) ? children : [children];
  const isEmpty = items.flat().filter(Boolean).length === 0;
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold uppercase text-muted-foreground">{title}</h2>
      <div className="card overflow-hidden p-0">
        {isEmpty ? (
          <p className="px-4 py-3 text-sm text-muted-foreground">{empty}</p>
        ) : (
          <ul className="divide-y divide-border">{children}</ul>
        )}
      </div>
    </section>
  );
}
