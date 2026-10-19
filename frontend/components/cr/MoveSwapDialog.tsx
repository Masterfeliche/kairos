"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { DAYS, hm, type PublicSession } from "@/lib/student";

/** Tap-based fallback for drag-and-drop: move a class to another day/time, or swap it. */
export default function MoveSwapDialog({
  session,
  siblings,
  onDone,
}: {
  session: PublicSession;
  siblings: PublicSession[];
  onDone: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"move" | "swap">("move");
  const [day, setDay] = useState(String(session.day_of_week));
  const [start, setStart] = useState(session.start_time.slice(0, 5));
  const [end, setEnd] = useState(session.end_time.slice(0, 5));
  const [venue, setVenue] = useState(session.venue || "");
  const [targetId, setTargetId] = useState("");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const swapChoices = useMemo(
    () =>
      siblings
        .filter((s) => s.id !== session.id)
        .sort((a, b) => a.day_of_week - b.day_of_week || a.start_time.localeCompare(b.start_time)),
    [siblings, session.id],
  );

  async function save() {
    setSaving(true);
    setErr(null);
    try {
      if (mode === "move") {
        await api(`/api/v1/cr/sessions/${session.id}/reschedule`, {
          method: "POST",
          body: JSON.stringify({
            start_time: start,
            end_time: end,
            day_of_week: Number(day),
            venue: venue || null,
            reason: reason || null,
          }),
        });
      } else {
        if (!targetId) throw new ApiError(422, "Pick a class to swap with.");
        await api(`/api/v1/cr/sessions/${session.id}/swap`, {
          method: "POST",
          body: JSON.stringify({ with_session_id: targetId, reason: reason || null }),
        });
      }
      setOpen(false);
      onDone();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">Move / swap</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>Move or swap this class</DialogTitle></DialogHeader>
        <p className="text-sm text-muted-foreground">
          {session.course_name} · {DAYS[session.day_of_week]} {hm(session.start_time)}–{hm(session.end_time)}
          {session.venue ? ` · ${session.venue}` : ""}
        </p>

        <div className="flex gap-2">
          <Button size="sm" variant={mode === "move" ? "default" : "outline"} onClick={() => setMode("move")}>
            Move to…
          </Button>
          <Button size="sm" variant={mode === "swap" ? "default" : "outline"} onClick={() => setMode("swap")}>
            Swap with…
          </Button>
        </div>

        {mode === "move" ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="ms-day">Day</Label>
              <Select value={day} onValueChange={setDay}>
                <SelectTrigger id="ms-day"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4, 5].map((d) => (
                    <SelectItem key={d} value={String(d)}>{DAYS[d]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ms-venue">Venue</Label>
              <Input id="ms-venue" value={venue} onChange={(e) => setVenue(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ms-start">Start</Label>
              <Input id="ms-start" value={start} onChange={(e) => setStart(e.target.value)} placeholder="HH:MM" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ms-end">End</Label>
              <Input id="ms-end" value={end} onChange={(e) => setEnd(e.target.value)} placeholder="HH:MM" />
            </div>
          </div>
        ) : (
          <div className="space-y-1.5">
            <Label htmlFor="ms-target">Swap with</Label>
            <Select value={targetId} onValueChange={setTargetId}>
              <SelectTrigger id="ms-target"><SelectValue placeholder="Pick a class" /></SelectTrigger>
              <SelectContent>
                {swapChoices.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {DAYS[s.day_of_week]} {hm(s.start_time)}–{hm(s.end_time)} · {s.course_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {swapChoices.length === 0 && (
              <p className="text-xs text-muted-foreground">No other classes to swap with.</p>
            )}
          </div>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="ms-reason">Reason (optional)</Label>
          <Input id="ms-reason" value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>

        {err && <p className="text-xs text-destructive">{err}</p>}
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={save} disabled={saving || (mode === "swap" && !targetId)}>
            {saving ? "Saving..." : mode === "move" ? "Move class" : "Swap classes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
