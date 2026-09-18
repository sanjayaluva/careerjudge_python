/**
 * Psychometric Analysis (PSY-1 / SRS 02) — psychometrician-facing screen.
 *
 * The psychometrician sets filter criteria (category, date range, region, age
 * band) and runs the automatic analysis; the per-question indices (difficulty,
 * top/bottom-group difficulty, difference, discrimination, item-total
 * correlation) are shown in a table.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  PageCard,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableEmpty,
  TableHead,
  TableHeader,
  TableRow,
  useToast,
} from "@/components/ui";
import { extractApiError } from "@/api/client";
import {
  type PsychometricAnalysisFilters,
  listCategories,
  runPsychometricAnalysis,
} from "@/api/questionBank";

function fmt(n: number | null): string {
  return n === null || n === undefined ? "—" : Number(n).toFixed(3);
}

export default function PsychometricAnalysisPage() {
  const toast = useToast();
  const [categoryId, setCategoryId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [region, setRegion] = useState("");
  const [ageMin, setAgeMin] = useState("");
  const [ageMax, setAgeMax] = useState("");

  const { data: categories } = useQuery({
    queryKey: ["question-bank", "categories", "all"],
    queryFn: () => listCategories(),
  });

  const runMutation = useMutation({
    mutationFn: (filters: PsychometricAnalysisFilters) => runPsychometricAnalysis(filters),
    onError: (err) => toast.error(extractApiError(err)),
  });

  const results = runMutation.data ?? [];

  function handleRun() {
    if (!categoryId) {
      toast.error("Select a category to analyse.");
      return;
    }
    const filters: PsychometricAnalysisFilters = { category_id: Number(categoryId) };
    if (dateFrom) filters.date_from = dateFrom;
    if (dateTo) filters.date_to = dateTo;
    if (region.trim()) filters.region = region.trim();
    if (ageMin.trim()) filters.age_min = Number(ageMin);
    if (ageMax.trim()) filters.age_max = Number(ageMax);
    runMutation.mutate(filters);
  }

  return (
    <PageCard>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Psychometric Analysis</h1>
          <p className="text-sm text-slate-500">
            Set the filter criteria and run the analysis (SRS 02).
          </p>
        </div>
        <Link to="/question-bank" className="text-sm text-primary-600 hover:underline">
          ← Back to Question Bank
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filter criteria</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <Label htmlFor="pa-cat" required>
                Category
              </Label>
              <select
                id="pa-cat"
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
              >
                <option value="">Select category...</option>
                {(categories ?? []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.full_path || c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="pa-from">Date from</Label>
              <Input
                id="pa-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="pa-to">Date to</Label>
              <Input
                id="pa-to"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="pa-region">Region</Label>
              <Input
                id="pa-region"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                placeholder="Optional"
              />
            </div>
            <div>
              <Label htmlFor="pa-agemin">Age min</Label>
              <Input
                id="pa-agemin"
                type="number"
                value={ageMin}
                onChange={(e) => setAgeMin(e.target.value)}
                placeholder="Optional"
              />
            </div>
            <div>
              <Label htmlFor="pa-agemax">Age max</Label>
              <Input
                id="pa-agemax"
                type="number"
                value={ageMax}
                onChange={(e) => setAgeMax(e.target.value)}
                placeholder="Optional"
              />
            </div>
          </div>
          <div className="mt-4">
            <Button onClick={handleRun} loading={runMutation.isPending}>
              Run analysis
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Results ({results.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {runMutation.isPending ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Question</TableHead>
                    <TableHead>N</TableHead>
                    <TableHead>IDI</TableHead>
                    <TableHead>Top DI</TableHead>
                    <TableHead>Bottom DI</TableHead>
                    <TableHead>Diff DI</TableHead>
                    <TableHead>Discrim.</TableHead>
                    <TableHead>Item-total r</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.length === 0 ? (
                    <TableEmpty colSpan={8}>
                      {runMutation.isSuccess
                        ? "No questions matched the filter criteria."
                        : "Set criteria and run the analysis to see results."}
                    </TableEmpty>
                  ) : (
                    results.map((r) => (
                      <TableRow key={r.question_id}>
                        <TableCell>
                          <Link
                            to={`/question-bank/${r.question_id}`}
                            className="text-primary-600 hover:underline"
                          >
                            #{r.question_id}
                          </Link>
                        </TableCell>
                        <TableCell className="text-slate-500">{r.n_candidates}</TableCell>
                        {r.error ? (
                          <TableCell colSpan={6} className="text-xs text-danger">
                            {r.error}
                          </TableCell>
                        ) : (
                          <>
                            <TableCell>{fmt(r.item_difficulty_index)}</TableCell>
                            <TableCell>{fmt(r.top_group_difficulty_index)}</TableCell>
                            <TableCell>{fmt(r.bottom_group_difficulty_index)}</TableCell>
                            <TableCell>{fmt(r.difference_difficulty_index)}</TableCell>
                            <TableCell>{fmt(r.discrimination_index)}</TableCell>
                            <TableCell>{fmt(r.item_total_correlation)}</TableCell>
                          </>
                        )}
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </PageCard>
  );
}
