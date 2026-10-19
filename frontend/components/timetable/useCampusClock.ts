"use client";

import { useEffect, useState } from "react";
import { campusNow, type CampusNow } from "@/lib/time";

/**
 * Live campus clock. Starts from the server-rendered value (so hydration matches) and then
 * ticks in the browser, so "now", countdowns and past-class dimming stay correct while the
 * page is open — including pages served from the offline cache.
 */
export function useCampusClock(initial: CampusNow): CampusNow {
  const [now, setNow] = useState(initial);

  useEffect(() => {
    const tick = () => setNow(campusNow());
    tick();
    const id = window.setInterval(tick, 30_000);
    return () => window.clearInterval(id);
  }, []);

  return now;
}
