"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { campusNow } from "@/lib/time";
import { hm, nowAndNext, type TimetableResponse } from "@/lib/student";

/** Returning students land here first: their saved class and what's on right now. */
export default function ContinueCard() {
  const [code, setCode] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    let saved: string | null = null;
    try {
      saved = localStorage.getItem("tt_cohort");
    } catch {
      /* storage unavailable */
    }
    setCode(saved);
    if (!saved) return;

    let alive = true;
    api<TimetableResponse>(`/api/v1/timetable?cohort_code=${encodeURIComponent(saved)}`)
      .then((data) => {
        if (!alive) return;
        const clock = campusNow();
        if (!clock.today) return setStatus("No classes today — it's the weekend");
        const today = data.sessions
          .filter((s) => s.day_of_week === clock.today)
          .sort((a, b) => a.start_time.localeCompare(b.start_time));
        const { current, next } = nowAndNext(today, clock.minutes);
        if (current) setStatus(`Now: ${current.course_name}${current.venue ? ` · ${current.venue}` : ""}`);
        else if (next) setStatus(`Next at ${hm(next.start_time)}: ${next.course_name}`);
        else setStatus(today.length ? "No more classes today" : "No classes today");
      })
      .catch(() => {
        /* offline or unknown class: the link still works from cache */
      });
    return () => {
      alive = false;
    };
  }, []);

  if (!code) return null;

  return (
    <Link
      href={`/c/${code}`}
      className="flex flex-col gap-3 rounded-[1.125rem] bg-spotlight p-4 text-spotlight-foreground transition hover:bg-spotlight/90"
    >
      <span className="flex items-center justify-between gap-3">
        <span className="flex flex-col">
          <span className="text-xs font-semibold tracking-wider text-sidebar-primary">CONTINUE</span>
          <span className="font-mono text-xl font-semibold">{code}</span>
        </span>
        <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground dark:bg-sidebar-primary dark:text-sidebar-primary-foreground">
          <ArrowRight className="size-5" aria-hidden />
        </span>
      </span>
      {status && (
        <span className="flex items-center gap-2 rounded-xl bg-spotlight-accent px-3 py-2.5 text-[13px]">
          <span
            className={`size-[7px] shrink-0 rounded-full ${status.startsWith("Now") ? "bg-[#86efac]" : "bg-sidebar-primary"}`}
            aria-hidden
          />
          <span className="truncate">{status}</span>
        </span>
      )}
    </Link>
  );
}
