"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

type HistoryRow = {
  id: string;
  version_id: string;
  label: string;
  action: string;
  published_at: string | null;
  previous_version_id: string | null;
  diff_summary: string | null;
};

export default function HistoryPage() {
  const [rows, setRows] = useState<HistoryRow[]>([]);

  useEffect(() => {
    api<HistoryRow[]>("/api/v1/admin/history").then(setRows).catch(() => {});
  }, []);

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold md:text-3xl">Publication history</h1>
      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="bg-muted text-left text-xs font-medium uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-2">When</th>
              <th className="px-4 py-2">Action</th>
              <th className="px-4 py-2">Version</th>
              <th className="px-4 py-2">Diff</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="px-4 py-2 tabular-nums text-muted-foreground">
                  {r.published_at?.slice(0, 19).replace("T", " ") ?? "-"}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`badge ${
                      r.action === "publish"
                        ? "bg-success text-success-foreground"
                        : "bg-warning text-warning-foreground"
                    }`}
                  >
                    {r.action}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <Link className="text-primary hover:underline" href={`/admin/versions/${r.version_id}`}>
                    {r.label}
                  </Link>
                </td>
                <td className="px-4 py-2 text-muted-foreground text-xs">{r.diff_summary ?? "-"}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-4 py-3 text-muted-foreground" colSpan={4}>
                  Nothing published yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
