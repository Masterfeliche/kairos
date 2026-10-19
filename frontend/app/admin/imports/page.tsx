"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

type ImportResult = {
  version_id: string;
  sessions: number;
  with_code: number;
  issues: number;
  errors: number;
  warnings: number;
};

type Job = {
  id: string;
  version_id: string;
  status: string;
  progress: number;
  summary: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export default function ImportsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [year, setYear] = useState("2025/2026");
  const [semester, setSemester] = useState("1");
  const [label, setLabel] = useState("Semester I");
  const [force, setForce] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);

  const loadJobs = () => api<Job[]>("/api/v1/admin/jobs").then(setJobs).catch(() => {});
  useEffect(() => { loadJobs(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    const form = new FormData();
    form.append("file", file);
    form.append("year_label", year);
    form.append("semester", semester);
    form.append("label", label);
    form.append("force", String(force));
    try {
      const res = await api<ImportResult>("/api/v1/admin/import", { method: "POST", body: form });
      setResult(res);
      loadJobs();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold md:text-3xl">Import timetable PDF</h1>

      <form onSubmit={submit} className="card space-y-4">
        <div>
          <label className="label" htmlFor="file">PDF file</label>
          <input id="file" className="input" type="file" accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)} required />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="label" htmlFor="year">Academic year</label>
            <input id="year" className="input" value={year} onChange={(e) => setYear(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="semester">Semester</label>
            <select id="semester" className="input" value={semester} onChange={(e) => setSemester(e.target.value)}>
              <option value="1">1</option>
              <option value="2">2</option>
              <option value="annual">annual</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="label">Version label</label>
            <input id="label" className="input" value={label} onChange={(e) => setLabel(e.target.value)} />
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
          Force re-import even if this exact PDF was imported before
        </label>
        <button className="btn-primary" disabled={busy || !file}>
          {busy ? "Importing..." : "Upload & extract"}
        </button>
      </form>

      {error && <p className="rounded bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</p>}

      {result && (
        <div className="card space-y-2">
          <p className="text-sm font-medium text-success">
            Imported {result.sessions} sessions ({result.with_code} with a course code).
          </p>
          <p className="text-sm text-muted-foreground">
            {result.errors} errors, {result.warnings} warnings.{" "}
            <Link className="text-primary hover:underline" href={`/admin/versions/${result.version_id}`}>
              Open review
            </Link>
          </p>
        </div>
      )}

      <section className="space-y-2">
        <h2 className="text-sm font-semibold uppercase text-muted-foreground">Recent jobs</h2>
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-muted text-left text-xs font-medium uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Summary</th>
                <th className="px-4 py-2">Started</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td className="px-4 py-2">
                    <span className="badge bg-secondary text-secondary-foreground">{j.status}</span>
                  </td>
                  <td className="px-4 py-2 text-muted-foreground">{j.summary ?? "-"}</td>
                  <td className="px-4 py-2 text-muted-foreground">{j.started_at?.slice(0, 19) ?? "-"}</td>
                  <td className="px-4 py-2 text-right">
                    <Link className="text-primary hover:underline" href={`/admin/versions/${j.version_id}`}>
                      Review
                    </Link>
                  </td>
                </tr>
              ))}
              {jobs.length === 0 && (
                <tr><td className="px-4 py-3 text-muted-foreground" colSpan={4}>No jobs yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
