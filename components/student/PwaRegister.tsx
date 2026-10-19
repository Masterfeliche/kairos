"use client";

import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";

export default function PwaRegister() {
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    // Register Service Worker
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        navigator.serviceWorker
          .register("/sw.js")
          .catch((err) => console.debug("SW registration skipped/failed:", err));
      });
    }

    // Monitor online/offline state
    const updateOnlineStatus = () => {
      setIsOffline(!navigator.onLine);
    };

    updateOnlineStatus();
    window.addEventListener("online", updateOnlineStatus);
    window.addEventListener("offline", updateOnlineStatus);

    return () => {
      window.removeEventListener("online", updateOnlineStatus);
      window.removeEventListener("offline", updateOnlineStatus);
    };
  }, []);

  if (!isOffline) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="sticky top-0 z-50 flex items-center justify-center gap-2 bg-warning px-4 py-2 text-xs font-semibold text-warning-foreground shadow-sm"
    >
      <WifiOff className="size-3.5 shrink-0" aria-hidden="true" />
      <span>You’re offline — showing the last saved timetable.</span>
    </div>
  );
}
