# Career Judge — UI design system (cosmetic layer)

Scope: purely visual. Nothing here changes behaviour, data flow, routes,
permissions, handlers, field names, validation or user-visible wording.
Everything is expressed as Tailwind classes on top of the tokens in
`frontend/tailwind.config.ts` and the shared primitives in
`frontend/src/components/ui/*`.

## 1. Tokens

| Token      | Hue      | Use                                                  |
| ---------- | -------- | ---------------------------------------------------- |
| `primary`  | indigo   | brand, primary actions, active nav, links, focus     |
| `success`  | emerald  | completed / published / active / verified / paid     |
| `warning`  | amber    | pending / review / draft / expiring / caution        |
| `danger`   | red      | errors, destructive, rejected / overdue / cancelled  |
| `info`     | sky      | neutral informational notices, "in progress"         |
| `slate`    | grey     | text, borders, surfaces                              |

Never use raw palette names (`red-*`, `green-*`, `blue-*`, `amber-*`,
`emerald-*`, `sky-*`, `indigo-*`) in pages; map them:
`amber→warning`, `red→danger`, `green|emerald→success`, `blue|sky→info`,
`indigo→primary`. (Decorative chart / avatar colours may keep their hue.)

Text colour scale: `text-slate-900` headings · `text-slate-700` body ·
`text-slate-500` secondary/meta · `text-slate-400` placeholders/disabled icons.

Surfaces: page `bg-slate-50`; cards/tables/inputs `bg-white`; muted inset
panels `bg-slate-50` with `border-slate-200`.

Borders: `border-slate-200` on surfaces, `border-slate-300` on inputs.

Elevation (3 levels only): `shadow-card` (resting card) · `shadow-popover`
(dropdowns, toasts, notification panel) · `shadow-modal` (dialogs).

Radius: `rounded-md` controls/inputs/badges-square · `rounded-lg` cards,
popovers, panels · `rounded-xl` modals, auth card · `rounded-full` pills,
avatars, dots.

Focus: `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2`
on anything interactive that is not a shared primitive. A global
`:focus-visible` outline in `index.css` covers the rest.

Motion: `transition-colors` on hover states; `animate-fade-in` for
popovers/tabs/toasts. `prefers-reduced-motion` is honoured globally.

## 2. Typography

| Role                  | Classes                                                       |
| --------------------- | ------------------------------------------------------------- |
| Page title (h1)       | `text-xl font-semibold tracking-tight text-slate-900`         |
| Page subtitle         | `mt-1 text-sm text-slate-500`                                 |
| Section title (h2)    | `text-base font-semibold text-slate-900`                      |
| Card title            | `<CardTitle>` (`text-lg font-semibold tracking-tight`)        |
| Eyebrow / table head  | `text-[11px] font-semibold uppercase tracking-wider text-slate-500` |
| Body                  | `text-sm text-slate-700`                                      |
| Meta                  | `text-xs text-slate-500`                                      |
| Large stat            | `text-2xl font-semibold tabular-nums tracking-tight`          |

Use `tabular-nums` on numeric columns and stats. Use `leading-snug` for
multi-line descriptions, `leading-relaxed` for long reading text.

## 3. Layout recipes

### Module list page (flush)

```tsx
<div className="space-y-6">
  <PageCard>
    <div className="flex flex-col gap-4 p-6 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">Title</h1>
        <p className="mt-1 text-sm text-slate-500">Subtitle</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline">Secondary</Button>
        <Button>Primary</Button>
      </div>
    </div>
    {/* filters */}
    <div className="flex flex-col gap-3 px-6 pb-4 sm:flex-row sm:flex-wrap sm:items-center">
      <Input className="sm:max-w-xs" />
      <Select className="sm:w-44" />
    </div>
    <Table>…</Table>
  </PageCard>
</div>
```

Rules: one primary button per header; the header stacks on mobile; filter
rows wrap (`flex-wrap`) and inputs are `w-full` on mobile, fixed widths from
`sm:`. Never let a row of buttons force horizontal page scroll.

### Detail / editor page (padded)

```tsx
<div className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6">
  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">…header…</div>
  <Card>
    <CardHeader><CardTitle>Section</CardTitle><CardDescription>…</CardDescription></CardHeader>
    <CardContent>…</CardContent>
  </Card>
</div>
```

Widths: lists are full width; reading/detail pages `max-w-5xl`; forms and
editors `max-w-3xl`/`max-w-4xl`; auth `max-w-md`; the session player
`max-w-3xl` with generous vertical rhythm and no sidebar chrome.

Back links: `inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-900`.

### Cards and grids

- Card grid: `grid gap-4 sm:grid-cols-2 xl:grid-cols-3`.
- Stat tiles: `rounded-lg border border-slate-200 bg-white p-5 shadow-card`
  with eyebrow label + `text-2xl font-semibold tabular-nums`.
- Inset panel (notes, summaries): `rounded-lg border border-slate-200 bg-slate-50 p-4`.
- Status callout: `<Alert variant="warning|info|success|error">`, or
  `rounded-lg border border-warning-200 bg-warning-50 p-4 text-sm text-warning-800`.

### Tables

Shared `<Table>` already gives header tint, `h-10` heads, `px-4 py-3` cells,
hover rows, and an `overflow-x-auto` wrapper. Per-page rules:

- numeric / date columns: `whitespace-nowrap tabular-nums`;
- action column: `text-right`, actions in `flex justify-end gap-1`, using
  `Button size="sm" variant="ghost|outline"` or `link` style
  `text-sm font-medium text-primary-600 hover:underline`;
- destructive link: `text-danger-600 hover:text-danger-700`;
- primary entity cell: `font-medium text-slate-900`; secondary line below in
  `text-xs text-slate-500`;
- `<TableEmpty colSpan>` for empty bodies.

### Forms

```tsx
<form className="space-y-5">
  <div className="grid gap-5 sm:grid-cols-2">
    <div><Label htmlFor=… required>…</Label><Input id=… /></div>
  </div>
  <p className="mt-1.5 text-xs text-slate-500">Help text</p>
  <p className="mt-1.5 text-xs text-danger-600">Error text</p>
  <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
    <Button variant="outline">Cancel</Button><Button type="submit">Save</Button>
  </div>
</form>
```

Checkbox / radio: `h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500`
inside `flex items-center gap-2 text-sm text-slate-700`.
Textareas: same classes as `Input` plus `min-h-[6rem]`.

### Buttons (hierarchy)

`primary` — the one main action. `outline` — secondary actions. `ghost` —
icon/tertiary row actions. `danger` — destructive confirms. `link` — inline.
`secondary` (tinted) — soft emphasis inside cards. Sizes: `sm` in tables and
toolbars, `md` elsewhere, `lg` only on landing/start screens.

### Badges

`<Badge variant>`: `success` active/published/completed/paid ·
`warning` pending/draft/review · `danger` rejected/overdue/failed/cancelled ·
`info` in-progress/scheduled · `primary` role / category · `outline` neutral
labels · `default` counts.

### Empty / loading states

- Loading: `<div className="flex items-center justify-center py-16"><Spinner /></div>`
  (or `py-8` inside cards). Skeleton rows: `h-4 animate-pulse rounded bg-slate-200`.
- Empty: `rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-12 text-center`
  with the existing text in `text-sm text-slate-500` (keep wording).

### Modals

Shared `<Modal size>`: `sm` confirms · `md` single-column forms · `lg`
two-column forms / pickers · `xl` wide editors. Footer: cancel (`outline`)
left of the primary action. Body uses the form recipe above.

### Tabs

Underline style from the shared `<TabsList>`. Wrap tab lists in
`overflow-x-auto` when there are more than four on mobile.

## 4. Mobile (390px)

- No horizontal page scroll: wrap action rows (`flex-wrap`), stack headers
  (`flex-col sm:flex-row`), make inputs `w-full sm:w-auto`, give `min-w-0`
  to flex children containing long text, `truncate` long single-line text,
  `break-words` long free text.
- Wide tables rely on the `overflow-x-auto` wrapper; never on the page.
- Page padding `p-4 sm:p-6`; grids collapse to one column.

## 5. Session player

Keep the player calm: `max-w-3xl` centred, `bg-slate-50` page, one white
question card (`rounded-lg border shadow-card p-6 sm:p-8`), progress as a
thin `h-1.5 rounded-full bg-slate-200` bar with `bg-primary-600` fill,
large readable prompt (`text-base sm:text-lg leading-relaxed`), options as
full-width `rounded-lg border p-4` rows with a clear selected state
(`border-primary-500 bg-primary-50 ring-1 ring-primary-500`). Navigation
buttons in a sticky bottom bar. No decorative colour.
