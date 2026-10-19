"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

export default function VenueNoticeDialog({
  defaultVenue = "",
  defaultDay,
  defaultStart = "",
  defaultEnd = "",
  triggerLabel = "Venue soon",
  onDone,
}: {
  defaultVenue?: string;
  defaultDay?: number;
  defaultStart?: string;
  defaultEnd?: string;
  triggerLabel?: string;
  onDone?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [venue, setVenue] = useState(defaultVenue);
  const [start, setStart] = useState(defaultStart.slice(0, 5));
  const [end, setEnd] = useState(defaultEnd.slice(0, 5));
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setErr(null);
    try {
      await api("/api/v1/cr/venue-notices", {
        method: "POST",
        body: JSON.stringify({
          venue,
          day_of_week: defaultDay,
          start_time: start,
          end_time: end || null,
          note: note || null,
        }),
      });
      setOpen(false);
      setNote("");
      onDone?.();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Failed");
    } finally {
      setSaving(false);
    }
  }

  if (!defaultDay) return null;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">{triggerLabel}</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Heads-up: this venue will be occupied</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Others will see this so they know when to leave and do not take the venue by mistake.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5 sm:col-span-2">
            <Label>Venue</Label>
            <Input value={venue} onChange={(e) => setVenue(e.target.value)} placeholder="e.g. LR 12" />
          </div>
          <div className="space-y-1.5">
            <Label>From (they should leave by)</Label>
            <Input value={start} onChange={(e) => setStart(e.target.value)} placeholder="HH:MM" />
          </div>
          <div className="space-y-1.5">
            <Label>Until (optional)</Label>
            <Input value={end} onChange={(e) => setEnd(e.target.value)} placeholder="HH:MM" />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label>Note (optional)</Label>
            <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Why / who needs it" />
          </div>
        </div>
        {err && <p className="text-xs text-destructive">{err}</p>}
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={save} disabled={saving || !venue.trim()}>
            {saving ? "Saving..." : "Post heads-up"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
