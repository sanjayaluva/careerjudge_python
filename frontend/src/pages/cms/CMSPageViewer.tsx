/**
 * CMS Page Viewer — renders a published CMS page by slug.
 *
 * Route: /:slug (e.g., /about-us)
 * Wrapped in PublicLayout so it has header navigation + footer.
 */
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { Alert, AlertDescription, Spinner } from "@/components/ui";
import { PublicLayout } from "@/components/layout/PublicLayout";
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

  return (
    <PublicLayout>
      {isLoading ? (
        <div className="flex min-h-[50vh] items-center justify-center">
          <Spinner size="lg" />
        </div>
      ) : error || !page ? (
        <div className="mx-auto max-w-4xl p-6">
          <Alert variant="error">
            <AlertDescription>
              Page not found.{" "}
              <Link to="/" className="text-primary-600 hover:underline">
                Go home
              </Link>
            </AlertDescription>
          </Alert>
        </div>
      ) : (
        <div className="mx-auto max-w-4xl p-6">
          <h1 className="text-3xl font-bold text-slate-900">{page.title}</h1>
          {page.meta_description && (
            <p className="mt-1 text-sm text-slate-500">{page.meta_description}</p>
          )}
          <div
            className="prose prose-slate mt-6 max-w-none"
            dangerouslySetInnerHTML={{ __html: page.body }}
          />
        </div>
      )}
    </PublicLayout>
  );
}
