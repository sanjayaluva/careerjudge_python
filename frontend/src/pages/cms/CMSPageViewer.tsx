/**
 * CMS Page Viewer — renders a published CMS page by slug.
 *
 * Route: /page/:slug (e.g., /page/about-us)
 * Also: /p/:slug (shorter URL)
 */
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { Alert, AlertDescription, PageCard, Spinner } from "@/components/ui";
import { retrievePageBySlug } from "@/api/cms";

export default function CMSPageViewer() {
  const { slug } = useParams<{ slug: string }>();

  const {
    data: page,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["cms", "page", slug],
    queryFn: () => retrievePageBySlug(slug!),
    enabled: !!slug,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !page) {
    return (
      <div className="p-6">
        <Alert variant="error">
          <AlertDescription>
            Page not found.{" "}
            <Link to="/dashboard" className="text-primary-600 hover:underline">
              Go to dashboard
            </Link>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <PageCard>
        <div className="p-6">
          <h1 className="text-2xl font-bold text-slate-900">{page.title}</h1>
          {page.meta_description && (
            <p className="mt-1 text-sm text-slate-500">{page.meta_description}</p>
          )}
          <div
            className="prose prose-slate mt-4 max-w-none"
            dangerouslySetInnerHTML={{ __html: page.body }}
          />
          <div className="mt-6 border-t border-slate-100 pt-4">
            <Link to="/dashboard" className="text-sm text-primary-600 hover:underline">
              ← Back to dashboard
            </Link>
          </div>
        </div>
      </PageCard>
    </div>
  );
}
