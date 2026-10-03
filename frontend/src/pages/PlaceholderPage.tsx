import { useSearchParams } from "react-router-dom";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui";

export interface PlaceholderPageProps {
  title: string;
  description?: string;
}

/**
 * Placeholder for Phase 2+ module routes. Shows a "coming soon" card.
 */
export default function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  const [searchParams] = useSearchParams();
  return (
    <div className="p-4 sm:p-6">
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>
            {description ?? "This module is part of a future release."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-slate-600">
            This page is a placeholder. Full functionality will be delivered in a later phase of the
            CareerJudge roadmap.
          </p>
          {searchParams.toString() && (
            <p className="mt-2 break-words text-xs text-slate-400">
              Query: {searchParams.toString()}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
