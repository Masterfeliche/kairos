"use client";

import { useState } from "react";
import { ArrowLeftRight, BellRing, Ellipsis, Play, RotateCcw, Square, XCircle } from "lucide-react";
import { toast } from "sonner";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import MoveSwapDialog from "@/components/cr/MoveSwapDialog";
import VenueNoticeDialog from "@/components/cr/VenueNoticeDialog";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { LiveStatus, PublicSession } from "@/lib/student";

const DONE_LABEL: Record<LiveStatus, string> = {
  live: "marked live",
  ended: "ended",
  not_held: "marked not held",
  scheduled: "reset to scheduled",
};

const BTN =
  "flex h-12 items-center justify-center gap-2 rounded-xl text-[15px] font-semibold transition disabled:opacity-50";

/**
 * Class-rep controls for one session. `buttons` shows the next likely action as big
 * one-tap buttons (for the current / next class); `menu` is a single ⋯ button for list rows.
 * Every status change can be undone from the confirmation toast.
 */
export default function SessionActions({
  session,
  siblings,
  onChanged,
  layout,
}: {
  session: PublicSession;
  siblings: PublicSession[];
  onChanged: () => void;
  layout: "buttons" | "menu";
}) {
  const [busy, setBusy] = useState(false);
  const [dialog, setDialog] = useState<null | "move" | "notice">(null);
  const status = session.live_status;

  async function setLive(next: LiveStatus, { silent = false } = {}) {
    const previous = status;
    setBusy(true);
    try {
      await api(`/api/v1/cr/sessions/${session.id}/live`, {
        method: "POST",
        body: JSON.stringify({ status: next }),
      });
      onChanged();
      if (!silent) {
        toast.success(`${session.course_name} ${DONE_LABEL[next]}`, {
          action: { label: "Undo", onClick: () => void setLive(previous, { silent: true }) },
          duration: 8000,
        });
      }
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Could not update the class");
    } finally {
      setBusy(false);
    }
  }

  const menu = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          disabled={busy}
          aria-label={`More actions for ${session.course_name}`}
          className={cn(
            "flex shrink-0 items-center justify-center rounded-xl text-muted-foreground transition hover:bg-muted hover:text-foreground disabled:opacity-50",
            layout === "buttons" ? "h-12 w-12 border border-input bg-card" : "size-11",
          )}
        >
          <Ellipsis className="size-5" aria-hidden />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        {status !== "live" && (
          <DropdownMenuItem onSelect={() => setLive("live")} className="py-2">
            <Play aria-hidden /> Start class
          </DropdownMenuItem>
        )}
        {status === "live" && (
          <DropdownMenuItem onSelect={() => setLive("ended")} className="py-2">
            <Square aria-hidden /> End class
          </DropdownMenuItem>
        )}
        {status !== "not_held" && (
          <DropdownMenuItem variant="destructive" onSelect={() => setLive("not_held")} className="py-2">
            <XCircle aria-hidden /> Not held
          </DropdownMenuItem>
        )}
        {status !== "scheduled" && (
          <DropdownMenuItem onSelect={() => setLive("scheduled")} className="py-2">
            <RotateCcw aria-hidden /> Reset to scheduled
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => setDialog("move")} className="py-2">
          <ArrowLeftRight aria-hidden /> Move or swap…
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => setDialog("notice")} className="py-2">
          <BellRing aria-hidden /> Venue heads-up…
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );

  const dialogs = (
    <>
      <MoveSwapDialog
        session={session}
        siblings={siblings}
        onDone={onChanged}
        open={dialog === "move"}
        onOpenChange={(o) => setDialog(o ? "move" : null)}
      />
      <VenueNoticeDialog
        defaultVenue={session.venue ?? ""}
        defaultDay={session.day_of_week}
        defaultStart={session.start_time}
        defaultEnd={session.end_time}
        onDone={onChanged}
        open={dialog === "notice"}
        onOpenChange={(o) => setDialog(o ? "notice" : null)}
      />
    </>
  );

  if (layout === "menu") {
    return (
      <>
        {menu}
        {dialogs}
      </>
    );
  }

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_3rem] gap-2">
      {status === "live" ? (
        <>
          <button type="button" disabled={busy} onClick={() => setLive("ended")}
            className={cn(BTN, "bg-spotlight text-spotlight-foreground hover:bg-spotlight/90")}>
            <Square className="size-4" aria-hidden /> End class
          </button>
          <button type="button" disabled={busy} onClick={() => setDialog("move")}
            className={cn(BTN, "border border-input bg-card text-foreground hover:bg-muted")}>
            <ArrowLeftRight className="size-4" aria-hidden /> Move / swap
          </button>
        </>
      ) : status === "scheduled" ? (
        <>
          <button type="button" disabled={busy} onClick={() => setLive("live")}
            className={cn(BTN, "bg-success text-success-foreground hover:bg-success/90")}>
            <Play className="size-4" aria-hidden /> Start class
          </button>
          <button type="button" disabled={busy} onClick={() => setLive("not_held")}
            className={cn(BTN, "border border-destructive/40 bg-card text-destructive hover:bg-destructive/10")}>
            Not held
          </button>
        </>
      ) : (
        <>
          <button type="button" disabled={busy} onClick={() => setLive("scheduled")}
            className={cn(BTN, "border border-input bg-card text-foreground hover:bg-muted")}>
            <RotateCcw className="size-4" aria-hidden /> Reset
          </button>
          <button type="button" disabled={busy} onClick={() => setDialog("move")}
            className={cn(BTN, "border border-input bg-card text-foreground hover:bg-muted")}>
            <ArrowLeftRight className="size-4" aria-hidden /> Move / swap
          </button>
        </>
      )}
      {menu}
      {dialogs}
    </div>
  );
}
