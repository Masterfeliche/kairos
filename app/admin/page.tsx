"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, CheckCircle2, Circle, Lock, Upload } from "lucide-react";
import { toast } from "sonner";
import ConfirmDialog from "@/components/admin/ConfirmDialog";
import { api, ApiError, type Admin, type Version, type VersionDetail } from "@/lib/api";
import { cn } from "@/lib/utils";
import { CAMPUS_TZ, campusClockOf } from "@/lib/time";

type DiffSummary = { summary: { added: number; removed: number; changed: number } };
type AuditRow = { id: string; at: string | null; actor: string | null; action: string };
type HistoryRow = { version_id: string; action: string; published_at: string | null };
type Job = { version_id: string; started_at: string | null };

const STATUS: Record<string, { label: string; className: string }> = {
  live: { label: "Live", className: "bg-success text-success-foreground" },
  published: { label: "Published", className: "bg-success/15 text-success" },
  review: { label: "In review", className: "bg-warning/15 text-warning" },
  draft: { label: "Draft", className: "bg-secondary text-secondary-foreground" },
  superseded: { label: "Replaced", className: "bg-muted text-muted-foreground" },
  failed: { label: "Failed", className: "bg-destructive/10 text-destructive" },
};

const ACTIVITY: Record<string, string> = {
  "cr.live_status": "changed a class status",
  "cr.reschedule": "moved a class",
  "cr.swap": "swapped two classes",
  "cr.venue_notice": "posted a venue heads-up",
  "cr.venue_notice_clear": "cleared a venue heads-up",
  "issue.resolve": "resolved an import issue",
  "session.correct": "corrected a session",
  "import.create": "imported a timetable PDF",
  "version.publish": "published a version",
  "version.rollback": "rolled back the live version",
};

const dayKey = (iso: string) =>
  new Date(iso).toLocaleDateString("en-CA", { timeZone: CAMPUS_TZ });
const shortDate = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString("en-GB", { timeZone: CAMPUS_TZ, day: "numeric", month: "short" }) : null;

export default function DashboardPage() {
  const [versions, setVersions] = useState<Version[] | null>(null);
  const [me, setMe] = useState<Admin | null>(null);
  const [live, setLive] = useState<VersionDetail | null>(null);
  const [pending, setPending] = useState<VersionDetail | null>(null);
  const [diff, setDiff] = useState<DiffSummary["summary"] | null>(null);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [confirm, setConfirm] = useState<null | { kind: "publish" } | { kind: "rollback"; version: Version }>(null);

  const load = useCallback(async () => {
    const list = await api<Version[]>("/api/v1/admin/versions").catch(() => [] as Version[]);
    setVersions(list);
    const active = list.find((v) => v.is_active);
    const waiting = list.find((v) => v.status === "review" || v.status === "draft");
    const [liveDetail, pendingDetail, pendingDiff] = await Promise.all([
      active ? api<VersionDetail>(`/api/v1/admin/versions/${active.id}`).catch(() => null) : null,
      waiting ? api<VersionDetail>(`/api/v1/admin/versions/${waiting.id}`).catch(() => null) : null,
      waiting ? api<DiffSummary>(`/api/v1/admin/versions/${waiting.id}/diff`).catch(() => null) : null,
    ]);
    setLive(liveDetail);
    setPending(pendingDetail);
    setDiff(pendingDiff?.summary ?? null);
  }, []);

  useEffect(() => {
    load();
    api<Admin>("/api/v1/admin/auth/me").then(setMe).catch(() => {});
    api<AuditRow[]>("/api/v1/admin/audit?limit=200").then(setAudit).catch(() => {});
    api<HistoryRow[]>("/api/v1/admin/history").then(setHistory).catch(() => {});
    api<Job[]>("/api/v1/admin/jobs").then(setJobs).catch(() => {});
  }, [load]);

  // All versions of a period share a label, so number them oldest-first.
  const number = (id: string) => (versions ? versions.length - versions.findIndex((v) => v.id === id) : 0);
  const name = (v: { id: string; label: string }) => `${v.label} · v${number(v.id)}`;
  const isOwner = me?.role === "owner";

  const publishedAt = live && history.find((h) => h.version_id === live.id)?.published_at;
  const importedAt = pending && jobs.find((j) => j.version_id === pending.id)?.started_at;

  const today = dayKey(new Date().toISOString());
  const crToday = audit.filter((a) => a.at && a.action.startsWith("cr.") && a.action !== "cr.login" && dayKey(a.at) === today);
  const crCounts = {
    status: crToday.filter((a) => a.action === "cr.live_status").length,
    moves: crToday.filter((a) => a.action === "cr.reschedule" || a.action === "cr.swap").length,
    notices: crToday.filter((a) => a.action.startsWith("cr.venue_notice")).length,
  };
  const activity = audit.filter((a) => ACTIVITY[a.action]).slice(0, 6);

  async function publish() {
    if (!pending) return;
    try {
      await api(`/api/v1/admin/versions/${pending.id}/publish`, { method: "POST" });
      toast.success(`${name(pending)} is now live for students`);
      await load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Publish failed");
    }
  }

  async function rollback(v: Version) {
    try {
      await api(`/api/v1/admin/periods/${v.period_id}/rollback/${v.id}`, { method: "POST" });
      toast.success(`Rolled back to ${name(v)}`);
      await load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Rollback failed");
    }
  }

  if (versions === null) return <p className="text-sm text-muted-foreground">Loading…</p>;

  const errorsLeft = pending?.open_errors ?? 0;
  const warnings = pending ? pending.open_issues - pending.open_errors : 0;
  const canPublish = Boolean(pending && errorsLeft === 0 && isOwner);

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[1.75rem] font-bold leading-tight tracking-tight text-foreground">Dashboard</h1>
          <p className="text-sm text-muted-foreground">{live ? live.label : "No live timetable yet"}</p>
        </div>
        <Link
          href="/admin/imports"
          className="flex h-11 items-center gap-2 rounded-[10px] bg-primary px-4 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
        >
          <Upload className="size-[18px]" aria-hidden /> Import timetable PDF
        </Link>
      </div>

      {/* Status cards */}
      <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard eyebrow="Live for students">
          {live ? (
            <>
              <p className="flex items-center gap-2 text-lg font-semibold text-foreground">
                <span className="size-2 rounded-full bg-success" aria-hidden /> {name(live)}
              </p>
              <p className="text-[13px] text-muted-foreground">
                {publishedAt ? `Published ${shortDate(publishedAt)} · ` : ""}
                <span className="font-mono">{live.sessions.toLocaleString()}</span> sessions
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Nothing published yet.</p>
          )}
        </StatCard>

        <StatCard eyebrow="Waiting for review" tone={pending ? "warning" : undefined}>
          {pending ? (
            <>
              <p className="text-lg font-semibold text-foreground">{name(pending)}</p>
              <p className="text-[13px] text-muted-foreground">
                {importedAt ? `Imported ${shortDate(importedAt)} · ` : ""}
                {errorsLeft > 0 ? (
                  <span className="font-semibold text-destructive">
                    {errorsLeft} blocking {errorsLeft === 1 ? "error" : "errors"}
                  </span>
                ) : (
                  <span className="font-semibold text-success">Ready to publish</span>
                )}
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No draft waiting.</p>
          )}
        </StatCard>

        <StatCard eyebrow="Class reps today">
          <p className="text-lg font-semibold text-foreground">
            <span className="font-mono">{crToday.length}</span> {crToday.length === 1 ? "update" : "updates"}
          </p>
          <p className="text-[13px] text-muted-foreground">
            {crCounts.status} status · {crCounts.moves} moves · {crCounts.notices} heads-ups
          </p>
        </StatCard>
      </div>

      {/* Publish checklist */}
      {pending ? (
        <section aria-labelledby="ready-heading" className="rounded-2xl border border-border bg-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 id="ready-heading" className="text-lg font-semibold text-foreground">
                Get {name(pending)} ready to publish
              </h2>
              <p className="text-[13px] text-muted-foreground">
                {live ? `Students keep seeing ${name(live)} until you publish.` : "Students see nothing until you publish."}
              </p>
            </div>
            <button
              type="button"
              disabled={!canPublish}
              onClick={() => setConfirm({ kind: "publish" })}
              className={cn(
                "flex h-11 items-center gap-2 rounded-[10px] px-4 text-sm font-semibold transition",
                canPublish
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "cursor-not-allowed bg-secondary text-muted-foreground",
              )}
              title={!isOwner ? "Only an owner can publish" : errorsLeft > 0 ? "Fix the blocking errors first" : undefined}
            >
              {!canPublish && <Lock className="size-4" aria-hidden />}
              Publish {`v${number(pending.id)}`}
            </button>
          </div>

          <ol className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Step state="done" title="1 · Imported">
              <span className="font-mono">{pending.sessions.toLocaleString()}</span> sessions
              {pending.pages ? ` from ${pending.pages} pages` : ""}
            </Step>
            <Step
              state={errorsLeft > 0 ? "blocked" : "done"}
              title="2 · Fix errors"
              href={`/admin/versions/${pending.id}`}
              linkLabel="Review issues"
            >
              {errorsLeft > 0 ? `${errorsLeft} ${errorsLeft === 1 ? "error" : "errors"} left` : "No blocking errors"}
              {` · ${warnings} ${warnings === 1 ? "warning" : "warnings"}`}
            </Step>
            <Step state="todo" title="3 · Check changes" href={`/admin/versions/${pending.id}/diff`} linkLabel="View diff">
              {diff ? (
                <span className="font-mono">
                  +{diff.added} · −{diff.removed} · {diff.changed} changed
                </span>
              ) : (
                "Compare with the live version"
              )}
            </Step>
            <Step state={canPublish ? "todo" : "locked"} title="4 · Publish">
              {!isOwner
                ? "Only an owner can publish."
                : errorsLeft > 0
                  ? "Unlocks when errors are fixed."
                  : "Ready — you'll be asked to confirm."}
            </Step>
          </ol>
        </section>
      ) : (
        <section className="rounded-2xl border border-dashed border-border bg-card/60 p-5 text-sm text-muted-foreground">
          No draft is waiting. When the timetable office sends a new PDF,{" "}
          <Link href="/admin/imports" className="font-semibold text-primary hover:underline">import it</Link> to start a review.
        </section>
      )}

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        {/* Versions */}
        <section aria-labelledby="versions-heading" className="overflow-hidden rounded-2xl border border-border bg-card">
          <h2 id="versions-heading" className="px-5 pb-3 pt-4 text-base font-semibold text-foreground">Versions</h2>
          {versions.length === 0 ? (
            <p className="px-5 pb-5 text-sm text-muted-foreground">No versions yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[440px] text-sm">
                <thead className="bg-elevated text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-5 py-2.5">Version</th>
                    <th className="px-3 py-2.5">Status</th>
                    <th className="px-5 py-2.5"><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {versions.map((v) => {
                    const st = STATUS[v.is_active ? "live" : v.status] ?? STATUS.draft;
                    const canRollback = isOwner && !v.is_active && (v.status === "published" || v.status === "superseded");
                    return (
                      <tr key={v.id}>
                        <td className={cn("px-5 py-3 font-semibold", v.status === "superseded" ? "text-muted-foreground" : "text-foreground")}>
                          {name(v)}
                        </td>
                        <td className="px-3 py-3">
                          <span className={cn("inline-flex h-[22px] items-center gap-1.5 rounded-full px-2.5 text-xs font-semibold", st.className)}>
                            {v.is_active && <span className="size-1.5 rounded-full bg-current" aria-hidden />}
                            {st.label}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-5 py-3 text-right">
                          <Link className="font-semibold text-primary hover:underline" href={`/admin/versions/${v.id}`}>Review</Link>
                          <span className="px-1.5 text-muted-foreground" aria-hidden>·</span>
                          <Link className="font-semibold text-primary hover:underline" href={`/admin/versions/${v.id}/diff`}>Diff</Link>
                          {canRollback && (
                            <>
                              <span className="px-1.5 text-muted-foreground" aria-hidden>·</span>
                              <button
                                type="button"
                                onClick={() => setConfirm({ kind: "rollback", version: v })}
                                className="font-semibold text-destructive hover:underline"
                              >
                                Roll back…
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Activity */}
        <section aria-labelledby="activity-heading" className="rounded-2xl border border-border bg-card px-5 py-4">
          <h2 id="activity-heading" className="mb-3 text-base font-semibold text-foreground">Recent activity</h2>
          {activity.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nothing yet.</p>
          ) : (
            <ul className="space-y-3 text-[13px]">
              {activity.map((a) => (
                <li key={a.id} className="flex gap-2.5">
                  <span className="w-12 shrink-0 font-mono text-muted-foreground">
                    {a.at ? (dayKey(a.at) === today ? campusClockOf(a.at) : shortDate(a.at)) : ""}
                  </span>
                  <span className="min-w-0 text-foreground">
                    <strong className="font-semibold">{a.actor ?? "System"}</strong> {ACTIVITY[a.action]}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <Link href="/admin/audit" className="mt-4 inline-flex text-[13px] font-semibold text-primary hover:underline">
            Full audit log →
          </Link>
        </section>
      </div>

      <ConfirmDialog
        open={confirm?.kind === "publish"}
        onOpenChange={(o) => !o && setConfirm(null)}
        title={pending ? `Publish ${name(pending)}?` : "Publish?"}
        description="Every student and class rep will see this version immediately."
        confirmLabel="Publish now"
        onConfirm={publish}
      >
        {diff && (
          <p className="rounded-lg bg-elevated px-3 py-2 font-mono text-sm text-foreground">
            +{diff.added} added · −{diff.removed} removed · {diff.changed} changed
          </p>
        )}
      </ConfirmDialog>

      <ConfirmDialog
        open={confirm?.kind === "rollback"}
        onOpenChange={(o) => !o && setConfirm(null)}
        title={confirm?.kind === "rollback" ? `Roll back to ${name(confirm.version)}?` : "Roll back?"}
        description="Students will immediately see this older version instead of the current live one."
        confirmLabel="Roll back"
        destructive
        onConfirm={() => (confirm?.kind === "rollback" ? rollback(confirm.version) : Promise.resolve())}
      />
    </div>
  );
}

function StatCard({
  eyebrow, tone, children,
}: {
  eyebrow: string; tone?: "warning"; children: React.ReactNode;
}) {
  return (
    <div className={cn("rounded-2xl border bg-card p-4", tone === "warning" ? "border-warning/40" : "border-border")}>
      <p className={cn("mb-2 text-xs font-semibold uppercase tracking-wider", tone === "warning" ? "text-warning" : "text-muted-foreground")}>
        {eyebrow}
      </p>
      {children}
    </div>
  );
}

function Step({
  state, title, href, linkLabel, children,
}: {
  state: "done" | "blocked" | "todo" | "locked";
  title: string;
  href?: string;
  linkLabel?: string;
  children: React.ReactNode;
}) {
  const Icon = state === "done" ? CheckCircle2 : state === "blocked" ? AlertTriangle : state === "locked" ? Lock : Circle;
  return (
    <li
      className={cn(
        "rounded-xl border p-3.5",
        state === "done" && "border-success/30 bg-success/8",
        state === "blocked" && "border-destructive/30 bg-destructive/8",
        (state === "todo" || state === "locked") && "border-border bg-elevated",
      )}
    >
      <p
        className={cn(
          "flex items-center gap-2 text-sm font-semibold",
          state === "done" && "text-success",
          state === "blocked" && "text-destructive",
          state === "todo" && "text-foreground",
          state === "locked" && "text-muted-foreground",
        )}
      >
        <Icon className="size-[18px]" aria-hidden /> {title}
      </p>
      <p className="mt-1.5 text-[13px] text-muted-foreground">{children}</p>
      {href && linkLabel && (
        <Link href={href} className="mt-2 inline-flex text-[13px] font-semibold text-primary hover:underline">
          {linkLabel} →
        </Link>
      )}
    </li>
  );
}
