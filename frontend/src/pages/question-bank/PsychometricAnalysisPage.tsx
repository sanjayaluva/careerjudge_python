/**
 * Psychometric Analysis (PSY-1 / SRS 02) — psychometrician-facing screen.
 *
 * Doc 1 §4.1.1 (Report 9 #87/#88): the psychometrician sets filter criteria
 * (category, question ID, time period, region, age range) and clicks
 * "Extract"; the matching questions are listed with their key details, the
 * psychometrician ticks the ones to analyse (or "select all") and runs the
 * analysis on just those. The per-question indices (difficulty, top/bottom-
 * group difficulty, difference, discrimination, item-total correlation) are
 * shown in a table.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  Badge,
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
  type PsychometricExtractRow,
  extractPsychometricQuestions,
  listCategories,
  runPsychometricAnalysis,
} from "@/api/questionBank";

function fmt(n: number | null): string {
  return n === null || n === undefined ? "—" : Number(n).toFixed(3);
}

export default function PsychometricAnalysisPage() {
  const toast = useToast();
  const [categoryId, setCategoryId] = useState("");
  const [questionRef, setQuestionRef] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [region, setRegion] = useState("");
  const [ageMin, setAgeMin] = useState("");
  const [ageMax, setAgeMax] = useState("");

  // The filters used for the last Extract — the run reuses the same data
  // filters so the analysis matches the response counts shown in the list.
  const [extractedWith, setExtractedWith] = useState<PsychometricAnalysisFilters | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const { data: categories } = useQuery({
    queryKey: ["question-bank", "categories", "all"],
    queryFn: () => listCategories(),
  });

  const runMutation = useMutation({
    mutationFn: (filters: PsychometricAnalysisFilters) => runPsychometricAnalysis(filters),
    onError: (err) => toast.error(extractApiError(err)),
  });

  const extractMutation = useMutation({
    mutationFn: (filters: PsychometricAnalysisFilters) => extractPsychometricQuestions(filters),
    onSuccess: (_rows, filters) => {
      setExtractedWith(filters);
      setSelected(new Set());
      runMutation.reset();
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  const extracted: PsychometricExtractRow[] = extractMutation.data ?? [];
  const results = runMutation.data ?? [];
  const titles = new Map(extracted.map((q) => [q.id, q.question_title]));
  const allSelected = extracted.length > 0 && selected.size === extracted.length;

  function handleExtract() {
    if (!categoryId && !questionRef.trim()) {
      toast.error("Select a category or enter a question ID to extract questions.");
      return;
    }
    const filters: PsychometricAnalysisFilters = {};
    if (categoryId) filters.category_id = Number(categoryId);
    if (questionRef.trim()) filters.question_ref = questionRef.trim();
    if (dateFrom) filters.date_from = dateFrom;
    if (dateTo) filters.date_to = dateTo;
    if (region.trim()) filters.region = region.trim();
    if (ageMin.trim()) filters.age_min = Number(ageMin);
    if (ageMax.trim()) filters.age_max = Number(ageMax);
    extractMutation.mutate(filters);
  }

  function handleRun() {
    if (!extractedWith || selected.size === 0) {
      toast.error("Select at least one question to analyse.");
      return;
    }
    // Run on the ticked questions only, with the same data filters
    // (time period, region, age range) used for the extraction.
    runMutation.mutate({
      date_from: extractedWith.date_from,
      date_to: extractedWith.date_to,
      region: extractedWith.region,
      age_min: extractedWith.age_min,
      age_max: extractedWith.age_max,
      question_ids: extracted.filter((q) => selected.has(q.id)).map((q) => q.id),
    });
  }

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected(allSelected ? new Set() : new Set(extracted.map((q) => q.id)));
  }

  return (
    <PageCard>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Psychometric Analysis</h1>
          <p className="text-sm text-slate-500">
            Set the filter criteria and extract the questions, select the ones to analyse, then run
            the analysis.
          </p>
        </div>
        <Link to="/question-bank" className="text-sm text-primary-600 hover:underline">
          ← Back to Question Bank
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>1. Filter criteria</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <Label htmlFor="pa-cat">Category</Label>
              <select
                id="pa-cat"
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
              >
                <option value="">Any category</option>
                {(categories ?? []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.full_path || c.name}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-slate-500">Includes its subcategories.</p>
            </div>
            <div>
              <Label htmlFor="pa-qid">Question ID</Label>
              <Input
                id="pa-qid"
                value={questionRef}
                onChange={(e) => setQuestionRef(e.target.value)}
                placeholder="e.g. 12, 15 or a display ID"
              />
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
            <div className="grid grid-cols-2 gap-2">
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
          </div>
          <div className="mt-4">
            <Button onClick={handleExtract} loading={extractMutation.isPending}>
              Extract
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>
              2. Select questions ({selected.size} of {extracted.length} selected)
            </CardTitle>
            <Button
              onClick={handleRun}
              loading={runMutation.isPending}
              disabled={selected.size === 0}
            >
              Run analysis on selected
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {extractMutation.isPending ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10">
                      <input
                        type="checkbox"
                        aria-label="Select all questions"
                        checked={allSelected}
                        disabled={extracted.length === 0}
                        onChange={toggleAll}
                      />
                    </TableHead>
                    <TableHead>ID</TableHead>
                    <TableHead>Question</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Responses</TableHead>
                    <TableHead>Last analysed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {extracted.length === 0 ? (
                    <TableEmpty colSpan={8}>
                      {extractMutation.isSuccess
                        ? "No questions matched the filter criteria."
                        : "Set the filter criteria and click Extract to list questions."}
                    </TableEmpty>
                  ) : (
                    extracted.map((q) => (
                      <TableRow key={q.id}>
                        <TableCell>
                          <input
                            type="checkbox"
                            aria-label={`Select question ${q.id}`}
                            checked={selected.has(q.id)}
                            onChange={() => toggle(q.id)}
                          />
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-slate-500">
                          #{q.id}
                          {q.question_id_label && (
                            <div className="text-xs">{q.question_id_label}</div>
                          )}
                        </TableCell>
                        <TableCell className="max-w-xs truncate">
                          <Link
                            to={`/question-bank/${q.id}`}
                            className="text-primary-600 hover:underline"
                          >
                            {q.question_title || "(untitled)"}
                          </Link>
                        </TableCell>
                        <TableCell className="text-slate-500">{q.question_type_label}</TableCell>
                        <TableCell className="text-slate-500">{q.category_path || "—"}</TableCell>
                        <TableCell>
                          <Badge variant={q.is_active ? "success" : "default"}>
                            {q.status_label}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-slate-500">{q.n_candidates}</TableCell>
                        <TableCell className="text-slate-500">
                          {q.psychometric_analyzed_at
                            ? new Date(q.psychometric_analyzed_at).toLocaleDateString()
                            : "Never"}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>3. Results ({results.length})</CardTitle>
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
                      Select questions above and run the analysis to see results.
                    </TableEmpty>
                  ) : (
                    results.map((r) => (
                      <TableRow key={r.question_id}>
                        <TableCell className="max-w-xs truncate">
                          <Link
                            to={`/question-bank/${r.question_id}`}
                            className="text-primary-600 hover:underline"
                          >
                            #{r.question_id}
                            {titles.get(r.question_id) ? ` — ${titles.get(r.question_id)}` : ""}
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
