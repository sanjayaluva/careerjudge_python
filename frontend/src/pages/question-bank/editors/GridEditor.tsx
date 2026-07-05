/**
 * Grid Editor — for type 4 (Grid-List Selection)
 *
 * The candidate sees a grid of cells. Each cell can contain text or an image.
 * The candidate selects cells (checkboxes) to answer the question.
 * The SME configures:
 *   - Number of rows/columns
 *   - Row labels and column labels
 *   - Cell content (text or image) for each cell
 *   - Which cells are "correct" (the right answer)
 *
 * At delivery time, the candidate sees the grid with cell content and
 * checkboxes. They check the correct cells to answer.
 */
import { useState } from "react";
import { Input, Label, MediaManager } from "@/components/ui";

interface GridCell {
  text: string;
  image: string;
  is_correct: boolean;
}

interface GridEditorProps {
  data: {
    question_text_1: string;
    grid_rows: string;
    grid_cols: string;
    rowLabels: string[];
    colLabels: string[];
    correctCells: boolean[][];
    cellContent: GridCell[][];
  };
  onChange: (data: GridEditorProps["data"]) => void;
}

export function GridEditor({ data, onChange }: GridEditorProps) {
  const rows = parseInt(data.grid_rows) || 0;
  const cols = parseInt(data.grid_cols) || 0;

  const updateGridSize = () => {
    const newRows = parseInt(data.grid_rows) || 2;
    const newCols = parseInt(data.grid_cols) || 2;
    const rowLabels = Array(newRows)
      .fill("")
      .map((_, i) => data.rowLabels[i] || "");
    const colLabels = Array(newCols)
      .fill("")
      .map((_, i) => data.colLabels[i] || "");
    const correctCells = Array(newRows)
      .fill(false)
      .map((_, r) =>
        Array(newCols)
          .fill(false)
          .map((_, c) => data.correctCells?.[r]?.[c] || false),
      );
    // Initialize or resize cellContent
    const cellContent = Array(newRows)
      .fill(null)
      .map((_, r) =>
        Array(newCols)
          .fill(null)
          .map((_, c) => data.cellContent?.[r]?.[c] || { text: "", image: "", is_correct: false }),
      );
    onChange({ ...data, rowLabels, colLabels, correctCells, cellContent });
  };

  const toggleCell = (r: number, c: number) => {
    // Guard: ensure correctCells and cellContent are initialized
    if (!data.correctCells || !data.correctCells[r]) return;
    const newCells = data.correctCells.map((row) => [...row]);
    newCells[r][c] = !newCells[r][c];
    // Sync is_correct into cellContent too
    const newContent = (data.cellContent || []).map((row) => row.map((cell) => ({ ...cell })));
    // Ensure newContent has enough rows/cols
    while (newContent.length <= r) newContent.push([]);
    if (!newContent[r]) newContent[r] = [];
    if (!newContent[r][c]) newContent[r][c] = { text: "", image: "", is_correct: false };
    newContent[r][c].is_correct = newCells[r][c];
    onChange({ ...data, correctCells: newCells, cellContent: newContent });
  };

  const updateRowLabel = (i: number, val: string) => {
    const newLabels = [...data.rowLabels];
    newLabels[i] = val;
    onChange({ ...data, rowLabels: newLabels });
  };

  const updateColLabel = (i: number, val: string) => {
    const newLabels = [...data.colLabels];
    newLabels[i] = val;
    onChange({ ...data, colLabels: newLabels });
  };

  const updateCellContent = (r: number, c: number, field: "text" | "image", val: string) => {
    const newContent = (data.cellContent || []).map((row) => row.map((cell) => ({ ...cell })));
    // Ensure enough rows
    while (newContent.length <= r) newContent.push([]);
    if (!newContent[r]) newContent[r] = [];
    if (!newContent[r][c]) newContent[r][c] = { text: "", image: "", is_correct: false };
    newContent[r][c][field] = val;
    onChange({ ...data, cellContent: newContent });
  };

  const [editingCell, setEditingCell] = useState<{ r: number; c: number } | null>(null);

  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="qtext1" required>
          Question text
        </Label>
        <textarea
          id="qtext1"
          rows={3}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          value={data.question_text_1}
          onChange={(e) => onChange({ ...data, question_text_1: e.target.value })}
          placeholder="Instructions for grid selection (e.g. 'Select all cells that match...')"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="grows">Grid rows</Label>
          <Input
            id="grows"
            type="number"
            min="2"
            max="10"
            value={data.grid_rows}
            onChange={(e) => onChange({ ...data, grid_rows: e.target.value })}
            onBlur={updateGridSize}
          />
        </div>
        <div>
          <Label htmlFor="gcols">Grid columns</Label>
          <Input
            id="gcols"
            type="number"
            min="2"
            max="10"
            value={data.grid_cols}
            onChange={(e) => onChange({ ...data, grid_cols: e.target.value })}
            onBlur={updateGridSize}
          />
        </div>
      </div>

      {rows > 0 && cols > 0 && (
        <div className="space-y-3">
          {/* Column labels */}
          <div className="grid gap-2" style={{ gridTemplateColumns: `120px repeat(${cols}, 1fr)` }}>
            <span className="text-xs font-medium text-slate-500">Row \ Col</span>
            {Array.from({ length: cols }).map((_, c) => (
              <Input
                key={c}
                value={data.colLabels[c] || ""}
                onChange={(e) => updateColLabel(c, e.target.value)}
                placeholder={`Col ${c + 1}`}
                className="text-xs"
              />
            ))}
          </div>

          {/* Grid rows with cell content */}
          {Array.from({ length: rows }).map((_, r) => (
            <div
              key={r}
              className="grid gap-2"
              style={{ gridTemplateColumns: `120px repeat(${cols}, 1fr)` }}
            >
              <Input
                value={data.rowLabels[r] || ""}
                onChange={(e) => updateRowLabel(r, e.target.value)}
                placeholder={`Row ${r + 1}`}
                className="text-xs"
              />
              {Array.from({ length: cols }).map((_, c) => {
                const cell = data.cellContent?.[r]?.[c];
                const isCorrect = data.correctCells?.[r]?.[c];
                return (
                  <div
                    key={c}
                    className={`flex min-h-[60px] flex-col items-center justify-center rounded-md border p-1 text-center ${
                      isCorrect ? "border-success-600 bg-success-50" : "border-slate-200 bg-white"
                    }`}
                  >
                    {/* Cell content display */}
                    {cell?.image ? (
                      <img
                        src={cell.image}
                        alt={`Cell ${r + 1},${c + 1}`}
                        className="mb-1 max-h-10 max-w-full object-contain"
                      />
                    ) : cell?.text ? (
                      <span className="text-xs font-medium text-slate-700">{cell.text}</span>
                    ) : (
                      <span className="text-xs text-slate-400">(empty)</span>
                    )}

                    {/* Action buttons */}
                    <div className="mt-1 flex gap-1">
                      <button
                        type="button"
                        onClick={() => setEditingCell({ r, c })}
                        className="rounded border border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-600 hover:bg-slate-50"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleCell(r, c)}
                        className={`rounded border px-1.5 py-0.5 text-[10px] ${
                          isCorrect
                            ? "border-success-600 bg-success-100 text-success-700"
                            : "border-slate-200 text-slate-600 hover:bg-slate-50"
                        }`}
                      >
                        {isCorrect ? "✓ Correct" : "Mark"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
          <p className="text-xs text-slate-500">
            Click "Edit" to assign text/image to a cell. Click "Mark" to mark it as a correct
            answer. Green = correct.
          </p>
        </div>
      )}

      {/* Cell content editor modal */}
      {editingCell && (
        <div className="rounded-md border border-slate-300 bg-slate-50 p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-medium text-slate-700">
              Edit cell [{editingCell.r + 1}, {editingCell.c + 1}] — Row{" "}
              {data.rowLabels[editingCell.r] || editingCell.r + 1}, Col{" "}
              {data.colLabels[editingCell.c] || editingCell.c + 1}
            </p>
            <button
              type="button"
              onClick={() => setEditingCell(null)}
              className="rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-200"
            >
              ✕ Close
            </button>
          </div>
          <div className="space-y-3">
            <div>
              <Label htmlFor="cell-text">Cell text (optional)</Label>
              <Input
                id="cell-text"
                value={data.cellContent?.[editingCell.r]?.[editingCell.c]?.text || ""}
                onChange={(e) =>
                  updateCellContent(editingCell.r, editingCell.c, "text", e.target.value)
                }
                placeholder="Text to show in this cell..."
              />
            </div>
            <div>
              <Label>Cell image (optional)</Label>
              <MediaManager
                label="Cell image"
                accept="image/*"
                modes={["upload", "url", "gallery"]}
                value={data.cellContent?.[editingCell.r]?.[editingCell.c]?.image || ""}
                onChange={(url) => updateCellContent(editingCell.r, editingCell.c, "image", url)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Preview */}
      <div className="rounded-md border border-primary-200 bg-primary-50/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary-700">
          Preview
        </p>
        <p className="mb-2 text-sm text-slate-900">{data.question_text_1 || "(no instructions)"}</p>
        {rows > 0 && cols > 0 && (
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className="border border-slate-200 p-1"></th>
                {Array.from({ length: cols }).map((_, c) => (
                  <th key={c} className="border border-slate-200 p-1 text-slate-600">
                    {data.colLabels[c] || `Col ${c + 1}`}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: rows }).map((_, r) => (
                <tr key={r}>
                  <td className="border border-slate-200 p-1 font-medium text-slate-600">
                    {data.rowLabels[r] || `Row ${r + 1}`}
                  </td>
                  {Array.from({ length: cols }).map((_, c) => {
                    const cell = data.cellContent?.[r]?.[c];
                    return (
                      <td key={c} className="border border-slate-200 p-1 text-center">
                        {cell?.image ? (
                          <img
                            src={cell.image}
                            alt=""
                            className="mx-auto max-h-10 object-contain"
                          />
                        ) : cell?.text ? (
                          cell.text
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="mt-2 text-xs text-slate-500">
          At delivery time, each cell shows a checkbox. Green cells above indicate correct answers.
        </p>
      </div>
    </div>
  );
}
