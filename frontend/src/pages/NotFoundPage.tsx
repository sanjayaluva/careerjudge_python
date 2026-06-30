import { Link } from "react-router-dom";

import { Button, Card, CardContent } from "@/components/ui";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-md text-center">
        <CardContent className="p-8">
          <p className="text-5xl font-bold text-primary-600">404</p>
          <h1 className="mt-4 text-xl font-semibold text-slate-900">Page not found</h1>
          <p className="mt-2 text-sm text-slate-500">
            The page you&apos;re looking for doesn&apos;t exist or has been moved.
          </p>
          <div className="mt-6">
            <Link to="/">
              <Button>Go home</Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
