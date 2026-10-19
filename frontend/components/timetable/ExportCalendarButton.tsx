"use client";

import { useState } from "react";
import { CalendarPlus, Download, Copy, Check } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ExportCalendarButtonProps {
  cohortCode: string;
}

export default function ExportCalendarButton({ cohortCode }: ExportCalendarButtonProps) {
  const [copied, setCopied] = useState(false);

  const icsUrl = `/api/v1/timetable/export.ics?cohort_code=${encodeURIComponent(cohortCode)}`;

  const handleCopyUrl = async () => {
    try {
      const fullUrl = `${window.location.origin}${icsUrl}`;
      await navigator.clipboard.writeText(fullUrl);
      setCopied(true);
      toast.success("Calendar subscription URL copied to clipboard!");
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.error("Failed to copy URL to clipboard.");
    }
  };

  const handleDownload = () => {
    const link = document.createElement("a");
    link.href = icsUrl;
    link.download = `${cohortCode}_timetable.ics`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success(`Downloaded ${cohortCode} calendar (.ics)`);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          aria-label="Add to calendar"
          className="size-11 gap-2 rounded-xl border-border bg-card px-0 text-foreground hover:bg-muted sm:h-10 sm:w-auto sm:px-3.5"
        >
          <CalendarPlus className="size-5 text-primary sm:size-4" aria-hidden="true" />
          <span className="hidden sm:inline">Add to calendar</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem onClick={handleDownload} className="cursor-pointer gap-2 py-2">
          <Download className="size-4 text-primary" aria-hidden="true" />
          <div className="flex flex-col">
            <span className="font-medium text-xs">Download .ics file</span>
            <span className="text-[10px] text-muted-foreground">Apple, Google, Outlook</span>
          </div>
        </DropdownMenuItem>

        <DropdownMenuItem onClick={handleCopyUrl} className="cursor-pointer gap-2 py-2">
          {copied ? (
            <Check className="size-4 text-success" aria-hidden="true" />
          ) : (
            <Copy className="size-4 text-muted-foreground" aria-hidden="true" />
          )}
          <div className="flex flex-col">
            <span className="font-medium text-xs">Copy Calendar Feed Link</span>
            <span className="text-[10px] text-muted-foreground">Subscribe for live updates</span>
          </div>
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <div className="p-2 text-[11px] leading-relaxed text-muted-foreground">
          Import the downloaded file into Google Calendar or Apple Calendar to see all your weekly classes.
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
