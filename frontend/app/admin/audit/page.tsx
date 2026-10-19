"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type AuditRow = {
  id: string;
  at: string | null;
  actor: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  before: string | null;
  after: string | null;
  ip: string | null;
};

export default function AuditPage() {
  const [rows, setRows] = useState<AuditRow[]>([]);

  useEffect(() => {
    api<AuditRow[]>("/api/v1/admin/audit").then(setRows).catch(() => {});
  }, []);

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold md:text-3xl">Audit log</h1>
      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="bg-muted text-left text-xs font-medium uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-2">When</th>
              <th className="px-4 py-2">Actor</th>
              <th className="px-4 py-2">Action</th>
              <th className="px-4 py-2">Entity</th>
              <th className="px-4 py-2">Detail</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="px-4 py-2 whitespace-nowrap tabular-nums text-muted-foreground">
                  {r.at?.slice(0, 19).replace("T", " ") ?? "-"}
                </td>
                <td className="px-4 py-2 text-muted-foreground">{r.actor ?? "-"}</td>
                <td className="px-4 py-2 font-medium">{r.action}</td>
                <td className="px-4 py-2 text-muted-foreground">
                  {r.entity_type} <span className="font-mono text-xs">{r.entity_id.slice(0, 8)}</span>
                </td>
                <td className="px-4 py-2 text-muted-foreground max-w-[22rem] truncate text-xs">
                  {r.after ?? r.before ?? "-"}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-4 py-3 text-muted-foreground" colSpan={5}>
                  No audit events yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
