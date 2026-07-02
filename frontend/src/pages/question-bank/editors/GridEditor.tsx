/**
 * Grid Editor — for type 4 (Grid-List Selection)
 * Define rows/columns, assign correct cells.
 */
import { Input, Label } from "@/components/ui";

interface GridEditorProps {
  data: {
    question_text_1: string;
    grid_rows: string;
    grid_cols: string;
    rowLabels: string[];
    colLabels: string[];
    correctCells: boolean[][];
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
    onChange({ ...data, rowLabels, colLabels, correctCells });
  };

  const toggleCell = (r: number, c: number) => {
    const newCells = data.correctCells.map((row) => [...row]);
    newCells[r][c] = !newCells[r][c];
    onChange({ ...data, correctCells: newCells });
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
          placeholder="Instructions for grid selection..."
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

          {/* Grid rows */}
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
              {Array.from({ length: cols }).map((_, c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => toggleCell(r, c)}
                  className={`h-9 rounded-md border text-xs font-medium transition-colors ${
                    data.correctCells?.[r]?.[c]
                      ? "border-success-600 bg-success-50 text-success-700"
                      : "border-slate-200 bg-white text-slate-400 hover:bg-slate-50"
                  }`}
                >
                  {data.correctCells?.[r]?.[c] ? "✓ Correct" : "Click to mark"}
                </button>
              ))}
            </div>
          ))}
          <p className="text-xs text-slate-500">
            Click cells to mark them as correct. Green = correct answer.
          </p>
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
                  {Array.from({ length: cols }).map((_, c) => (
                    <td key={c} className="border border-slate-200 p-1 text-center">
                      {data.correctCells?.[r]?.[c] ? "☐" : ""}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
