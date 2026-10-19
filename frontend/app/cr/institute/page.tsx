"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api";
import { DAYS, hm, type LiveStatus } from "@/lib/student";
import type { CrSession, Institute, VenueAvail } from "@/lib/cr";
import { LiveBadge } from "@/components/timetable/SessionCard";

export default function CrInstitutePage() {
  const [inst, setInst] = useState<Institute | null>(null);
  const [day, setDay] = useState("1");
  const [start, setStart] = useState("10:00");
  const [end, setEnd] = useState("11:00");
  const [avail, setAvail] = useState<VenueAvail[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [aLoading, setALoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function loadInst(d: string) {
    setLoading(true); setErr(null);
    try {
      const res = await api<Institute>(`/api/v1/cr/institute?day=${encodeURIComponent(d)}`);
      setInst(res);
    } catch (e) { if (e instanceof ApiError) setErr(e.message); else setErr("Failed"); }
    finally { setLoading(false); }
  }

  async function loadAvail() {
    setALoading(true);
    try {
      const res = await api<{ day:number; start:string; end:string; venues:VenueAvail[] }>(
        `/api/v1/cr/availability?day=${encodeURIComponent(day)}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
      setAvail(res.venues);
    } catch (e) { /* ignore */ }
    finally { setALoading(false); }
  }

  useEffect(() => { loadInst(day); }, [day]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-foreground md:text-3xl">Institute timetable</h1>
        <p className="text-sm text-muted-foreground">
          All sessions for the selected day (across all cohorts). Use room availability to find a free slot to reschedule into.
        </p>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-end gap-2">
          <div className="space-y-1.5">
            <span className="text-xs text-muted-foreground">Day</span>
            <Select value={day} onValueChange={(v)=>setDay(v)}>
              <SelectTrigger className="w-[140px]"><SelectValue/></SelectTrigger>
              <SelectContent>
                {[1,2,3,4,5].map(d => <SelectItem key={d} value={String(d)}>{DAYS[d]}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <span className="text-xs text-muted-foreground">Start</span>
            <Input value={start} onChange={(e)=>setStart(e.target.value)} className="w-[90px]" />
          </div>
          <div className="space-y-1.5">
            <span className="text-xs text-muted-foreground">End</span>
            <Input value={end} onChange={(e)=>setEnd(e.target.value)} className="w-[90px]" />
          </div>
          <Button onClick={loadAvail} disabled={aLoading}>Find free rooms</Button>
        </div>

        {avail && (
          <div className="mt-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Venue</TableHead>
                  <TableHead>Free</TableHead>
                  <TableHead>Heads-up</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {avail.map(v => (
                  <TableRow key={v.venue}>
                    <TableCell className="font-mono">{v.venue}</TableCell>
                    <TableCell>
                      {v.free
                        ? <span className="text-success">Yes</span>
                        : <span className="text-destructive">No</span>}
                    </TableCell>
                    <TableCell className="text-warning text-xs">
                      {v.notice
                        ? `${hm(v.notice.start_time)}${v.notice.end_time ? `–${hm(v.notice.end_time)}` : ""}${
                            v.notice.note ? ` · ${v.notice.note}` : ""
                          }`
                        : v.free ? "" : "Occupied"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>

      <Card className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Course</TableHead>
              <TableHead>Venue</TableHead>
              <TableHead>Cohorts</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {inst?.sessions.map(s => (
              <TableRow key={s.id}>
                <TableCell className="tabular-nums">{hm(s.start_time)}–{hm(s.end_time)}</TableCell>
                <TableCell>
                  <div className="font-medium">{s.course_name}</div>
                  {s.course_code && <div className="text-xs text-muted-foreground font-mono">{s.course_code}</div>}
                </TableCell>
                <TableCell>{s.venue || "-"}</TableCell>
                <TableCell className="text-xs">{s.cohorts.join(", ")}</TableCell>
                <TableCell><LiveBadge status={s.live_status} /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {loading && <p className="p-4 text-sm text-muted-foreground">Loading...</p>}
        {err && <p className="p-4 text-sm text-destructive">{err}</p>}
      </Card>
    </div>
  );
}
