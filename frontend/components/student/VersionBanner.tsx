import { Alert, AlertDescription } from "@/components/ui/alert";
import { CAMPUS_TZ } from "@/lib/time";

function fmtDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString("en-GB", {
    timeZone: CAMPUS_TZ,
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export type BannerVersion = {
  label: string;
  is_preview?: boolean;
  source_filename?: string | null;
  published_at?: string | null;
  updated_at?: string | null;
};

/** One-line trust signal: which timetable this is and when it last changed. */
export default function VersionBanner({ version }: { version: BannerVersion | null }) {
  if (!version) {
    return (
      <Alert className="border-warning bg-warning/10 text-foreground">
        <AlertDescription>No timetable has been published yet.</AlertDescription>
      </Alert>
    );
  }
  const updated = fmtDate(version.updated_at ?? version.published_at);
  const preview = Boolean(version.is_preview);
  return (
    <p
      className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground"
      title={version.source_filename ?? undefined}
    >
      <span className={`size-[7px] shrink-0 rounded-full ${preview ? "bg-warning" : "bg-success"}`} aria-hidden />
      <span>
        <strong className="font-semibold text-foreground">{preview ? "Preview — not published" : "Official"}</strong>
        {" · "}
        {version.label}
        {updated && ` · updated ${updated}`}
      </span>
    </p>
  );
}
