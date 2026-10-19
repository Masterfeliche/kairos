"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Version } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-secondary text-secondary-foreground",
  review: "bg-warning text-warning-foreground",
  published: "bg-success text-success-foreground",
  superseded: "bg-muted text-muted-foreground",
  failed: "bg-destructive text-destructive-foreground",
};

export default function DashboardPage() {
  const [versions, setVersions] = useState<Version[] | null>(null);

  useEffect(() => {
    api<Version[]>("/api/v1/admin/versions").then(setVersions).catch(() => setVersions([]));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold md:text-3xl">Versions</h1>
        <Link className="btn-primary" href="/admin/imports">Import PDF</Link>
      </div>

      {versions === null ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : versions.length === 0 ? (
        <div className="card text-sm text-muted-foreground">
          No versions yet.{" "}
          <Link className="text-primary hover:underline" href="/admin/imports">
            Import a timetable PDF
          </Link>
          .
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-muted text-left text-xs font-medium uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-2">Label</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Active</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {versions.map((v) => (
                <tr key={v.id}>
                  <td className="px-4 py-2 font-medium">{v.label}</td>
                  <td className="px-4 py-2">
                    <span className={`badge ${STATUS_STYLES[v.status] || "bg-muted text-muted-foreground"}`}>
                      {v.status}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {v.is_active ? (
                      <span className="text-success">active</span>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Link className="text-primary hover:underline" href={`/admin/versions/${v.id}`}>
                      Review
                    </Link>
                    <span className="px-2 text-muted-foreground/50">|</span>
                    <Link className="text-primary hover:underline" href={`/admin/versions/${v.id}/diff`}>
                      Diff
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
