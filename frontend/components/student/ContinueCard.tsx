"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export default function ContinueCard() {
  const [code, setCode] = useState<string | null>(null);

  useEffect(() => {
    setCode(localStorage.getItem("tt_cohort"));
  }, []);

  if (!code) return null;

  return (
    <Link
      href={`/c/${code}`}
      className="flex items-center justify-between rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 transition hover:bg-primary/10"
    >
      <span className="text-sm text-foreground">
        Continue: <span className="font-semibold">{code}</span>
      </span>
      <ArrowRight className="size-4 text-primary" aria-hidden />
    </Link>
  );
}
