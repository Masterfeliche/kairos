import Link from "next/link";
import { LineChart } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-5 px-6 text-center">
      <LineChart className="size-8 text-primary" />
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-foreground">Page not found</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          We couldn&apos;t find the class or page you&apos;re looking for. It may have been renamed or removed.
        </p>
      </div>
      <Button asChild>
        <Link href="/">Back to selection</Link>
      </Button>
    </main>
  );
}
