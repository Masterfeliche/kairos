"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  api,
  ApiError,
  DAYS,
  type Admin,
  type Issue,
  type SessionRow,
  type VersionDetail,
} from "@/lib/api";

const SEVERITY_STYLES: Record<string, string> = {
  error: "bg-destructive text-destructive-foreground",
  warning: "bg-warning text-warning-foreground",
  info: "bg-info text-info-foreground",
};

const EDITABLE: (keyof SessionRow)[] = [
  "course_code_raw",
  "course_name_raw",
  "lecturer_raw",
  "venue_raw",
  "session_type",
  "day_of_week",
  "start_time",
  "end_time",
];

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<VersionDetail | null>(null);
  const [me, setMe] = useState<Admin | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [onlyIssues, setOnlyIssues] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<SessionRow | null>(null);
  const [notice, setNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const loadDetail = useCallback(() => {
    api<VersionDetail>(`/api/v1/admin/versions/${id}`).then(setDetail).catch(() => {});
    api<Issue[]>(`/api/v1/admin/versions/${id}/issues`).then(setIssues).catch(() => {});
  }, [id]);

  const loadSessions = useCallback(() => {
    const params = new URLSearchParams({ page: String(page), size: "25" });
    if (onlyIssues) params.set("only_issues", "true");
    if (query) params.set("q", query);
    api<{ total: number; items: SessionRow[] }>(`/api/v1/admin/versions/${id}/sessions?${params}`)
      .then((r) => { setSessions(r.items); setTotal(r.total); })
      .catch(() => {});
  }, [id, page, onlyIssues, query]);

  useEffect(() => { loadDetail(); api<Admin>("/api/v1/admin/auth/me").then(setMe).catch(() => {}); }, [loadDetail]);
  useEffect(() => { loadSessions(); }, [loadSessions]);

  async function publish() {
    setNotice(null);
    try {
      await api(`/api/v1/admin/versions/${id}/publish`, { method: "POST" });
      setNotice({ kind: "ok", text: "Version published." });
      loadDetail();
    } catch (err) {
      setNotice({ kind: "err", text: err instanceof ApiError ? err.message : "Publish failed" });
    }
  }

  async function rollback() {
    if (!detail) return;
    setNotice(null);
    try {
      await api(`/api/v1/admin/periods/${detail.period_id}/rollback/${id}`, { method: "POST" });
      setNotice({ kind: "ok", text: "Rolled back." });
      loadDetail();
    } catch (err) {
      setNotice({ kind: "err", text: err instanceof ApiError ? err.message : "Rollback failed" });
    }
  }

  async function resolveIssue(issueId: string) {
    await api(`/api/v1/admin/issues/${issueId}/resolve`, { method: "POST" });
    loadDetail();
    loadSessions();
  }

  const totalPages = Math.max(1, Math.ceil(total / 25));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">Review: {detail?.label ?? "..."}</h1>
          {detail && (
            <p className="text-sm text-muted-foreground">
              status <span className="font-medium">{detail.status}</span> · {detail.sessions} sessions ·{" "}
              {detail.open_issues} open issues ({detail.open_errors} errors) · {detail.pages} pages
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <Link className="btn-ghost" href={`/admin/versions/${id}/diff`}>View diff</Link>
          {me?.role === "owner" && (
            <>
              <button className="btn-danger" onClick={rollback}>Rollback to this</button>
              <button className="btn-primary" onClick={publish} disabled={detail?.status === "published"}>
                Publish
              </button>
            </>
          )}
        </div>
      </div>

      {notice && (
        <p className={`rounded px-4 py-3 text-sm ${notice.kind === "ok" ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"}`}>
          {notice.text}
        </p>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="card flex flex-wrap items-end gap-3">
            <div className="flex-1">
              <label className="label" htmlFor="q">Search</label>
              <input id="q" className="input" value={query} placeholder="code, course, lecturer or venue"
                onChange={(e) => { setPage(1); setQuery(e.target.value); }} />
            </div>
            <label className="flex items-center gap-2 pb-1 text-sm text-muted-foreground">
              <input type="checkbox" checked={onlyIssues}
                onChange={(e) => { setPage(1); setOnlyIssues(e.target.checked); }} />
              Only sessions with open issues
            </label>
          </div>

          <div className="card overflow-hidden p-0">
            <table className="w-full text-sm">
              <thead className="bg-muted text-left text-xs font-medium uppercase text-muted-foreground">
                <tr>
                  <th className="px-3 py-2">Day</th>
                  <th className="px-3 py-2">Time</th>
                  <th className="px-3 py-2">Code</th>
                  <th className="px-3 py-2">Course</th>
                  <th className="px-3 py-2">pg</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {sessions.map((s) => (
                  <tr key={s.id}
                    className={`cursor-pointer hover:bg-muted ${selected?.id === s.id ? "bg-primary/10" : ""}`}
                    onClick={() => setSelected(s)}>
                    <td className="px-3 py-2">{DAYS[s.day_of_week] || s.day_of_week}</td>
                    <td className="px-3 py-2 whitespace-nowrap tabular-nums">{s.start_time.slice(0, 5)}-{s.end_time.slice(0, 5)}</td>
                    <td className="px-3 py-2">
                      {s.course_code_raw ?? (
                        <span className="badge bg-destructive text-destructive-foreground">missing</span>
                      )}
                    </td>
                    <td className="px-3 py-2 max-w-[18rem] truncate">{s.course_name_raw}</td>
                    <td className="px-3 py-2 text-muted-foreground">{s.source_page}</td>
                  </tr>
                ))}
                {sessions.length === 0 && (
                  <tr><td className="px-3 py-3 text-muted-foreground" colSpan={5}>No sessions.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>{total} sessions</span>
            <div className="flex items-center gap-2">
              <button className="btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
              <span>page {page} / {totalPages}</span>
              <button className="btn-ghost" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {selected ? (
            <SessionEditor key={selected.id} session={selected} versionId={id}
              onSaved={() => { loadSessions(); loadDetail(); }}
              onClose={() => setSelected(null)} />
          ) : (
            <div className="card text-sm text-muted-foreground">Select a session to review it against the source page.</div>
          )}

          <div className="card space-y-2">
            <h2 className="text-sm font-semibold uppercase text-muted-foreground">Open issues</h2>
            {issues.length === 0 && <p className="text-sm text-muted-foreground">None.</p>}
            <ul className="space-y-1">
              {issues.slice(0, 50).map((i) => (
                <li key={i.id} className="flex items-start justify-between gap-2 text-sm">
                  <span>
                    <span className={`badge ${SEVERITY_STYLES[i.severity]}`}>{i.severity}</span>{" "}
                    <span className="text-muted-foreground">p{i.page} {i.code}</span>
                  </span>
                  <button className="text-xs text-primary hover:underline" onClick={() => resolveIssue(i.id)}>
                    resolve
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function SessionEditor({
  session,
  versionId,
  onSaved,
  onClose,
}: {
  session: SessionRow;
  versionId: string;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState<Record<string, string>>(() => {
    const d: Record<string, string> = {};
    for (const f of EDITABLE) d[f] = session[f] == null ? "" : String(session[f]);
    return d;
  });
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    const changes: Record<string, unknown> = {};
    for (const f of EDITABLE) {
      const before = session[f] == null ? "" : String(session[f]);
      if (draft[f] !== before) {
        if (f === "day_of_week") changes[f] = Number(draft[f]);
        else if (f === "start_time" || f === "end_time") changes[f] = draft[f].slice(0, 5);
        else changes[f] = draft[f] || null;
      }
    }
    try {
      await api(`/api/v1/admin/sessions/${session.id}/correct`, {
        method: "POST",
        body: JSON.stringify({ changes, reason }),
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase text-muted-foreground">Correct session</h2>
        <button className="text-muted-foreground hover:text-foreground" onClick={onClose}>close</button>
      </div>

      <img alt={`Source page ${session.source_page}`}
        className="w-full rounded border border-border"
        src={`/api/v1/admin/versions/${versionId}/pages/${session.source_page}.png`} />

      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="col-span-2">
          <label className="label">Course code</label>
          <input className="input" value={draft.course_code_raw}
            onChange={(e) => setDraft({ ...draft, course_code_raw: e.target.value })} />
        </div>
        <div className="col-span-2">
          <label className="label">Course name</label>
          <input className="input" value={draft.course_name_raw}
            onChange={(e) => setDraft({ ...draft, course_name_raw: e.target.value })} />
        </div>
        <div>
          <label className="label">Day</label>
          <select className="input" value={draft.day_of_week}
            onChange={(e) => setDraft({ ...draft, day_of_week: e.target.value })}>
            {[1, 2, 3, 4, 5].map((d) => <option key={d} value={d}>{DAYS[d]}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Type</label>
          <select className="input" value={draft.session_type}
            onChange={(e) => setDraft({ ...draft, session_type: e.target.value })}>
            <option value="">(none)</option>
            <option value="lecture">lecture</option>
            <option value="practical">practical</option>
            <option value="other">other</option>
          </select>
        </div>
        <div>
          <label className="label">Start</label>
          <input className="input" type="time" value={draft.start_time}
            onChange={(e) => setDraft({ ...draft, start_time: e.target.value })} />
        </div>
        <div>
          <label className="label">End</label>
          <input className="input" type="time" value={draft.end_time}
            onChange={(e) => setDraft({ ...draft, end_time: e.target.value })} />
        </div>
        <div>
          <label className="label">Venue</label>
          <input className="input" value={draft.venue_raw}
            onChange={(e) => setDraft({ ...draft, venue_raw: e.target.value })} />
        </div>
        <div>
          <label className="label">Lecturer</label>
          <input className="input" value={draft.lecturer_raw}
            onChange={(e) => setDraft({ ...draft, lecturer_raw: e.target.value })} />
        </div>
      </div>

      <div>
        <label className="label">Reason (required)</label>
        <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. code read from source PDF page" />
      </div>

      {error && <p className="rounded bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}

      <button className="btn-primary w-full justify-center" onClick={save} disabled={saving || !reason.trim()}>
        {saving ? "Saving..." : "Save correction"}
      </button>
    </div>
  );
}
