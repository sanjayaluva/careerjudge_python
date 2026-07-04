/**
 * PageCard — Card variant for main module list pages.
 *
 * Main module pages (Question Bank, Users, Organizations, Dashboard, etc.)
 * have their root Card flush to the page edges with no outer padding.
 * To avoid a doubled border at the left/top/right edges (against the
 * sidebar/topbar boundary), this component hides those borders and keeps
 * only the bottom border — creating a clean 1px horizontal separator
 * between stacked sections.
 *
 * Usage:
 *   <PageCard>
 *     <CardHeader>...</CardHeader>
 *     <CardContent>...</CardContent>
 *   </PageCard>
 *
 * For inner/detail pages that have p-6 padding (QuestionDetailPage,
 * QuestionEditorPage, etc.), use the regular <Card> component instead —
 * all 4 borders should show there since the Card is not flush to the edge.
 *
 * Future modules: use <PageCard> as the root container for the main
 * list/landing page so border styling is consistent across the entire app
 * without needing to remember to add 'border-l-0 border-t-0 border-r-0'.
 */
import { forwardRef, type HTMLAttributes } from "react";

import { cn } from "@/lib/utils";
import { Card } from "./Card";

export const PageCard = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <Card ref={ref} className={cn("border-l-0 border-r-0 border-t-0", className)} {...props} />
  ),
);
PageCard.displayName = "PageCard";
