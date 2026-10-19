import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";

function fmtDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
}

export type BannerVersion = {
  label: string;
  is_preview?: boolean;
  source_filename?: string | null;
  published_at?: string | null;
  updated_at?: string | null;
};

export default function VersionBanner({ version }: { version: BannerVersion | null }) {
  if (!version) {
    return (
      <Alert className="border-warning bg-warning/10 text-foreground">
        <AlertDescription>No timetable has been published yet.</AlertDescription>
      </Alert>
    );
  }
  const updated = fmtDate(version.updated_at ?? version.published_at);
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg border border-border bg-card px-4 py-2 text-sm text-muted-foreground">
      <span className="font-medium text-foreground">{version.label}</span>
      {updated && <span>· updated {updated}</span>}
      {version.source_filename && <span className="truncate">· {version.source_filename}</span>}
      {version.is_preview && (
        <Badge className="bg-warning text-warning-foreground">Preview — not published</Badge>
      )}
    </div>
  );
}
