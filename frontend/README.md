# CareerJudge Frontend

The React single-page application for CareerJudge — a modern career assessment, profiling, and counseling platform. Built with **React 18 + Vite 5 + TypeScript 5 + Tailwind CSS 3 + TanStack Query + Zustand + React Router v6**.

This package contains the Phase 1 deliverable: project skeleton, shadcn/ui-style component library, JWT-authenticated API client, role-based navigation, auth pages (login/signup/verify-email/forgot/reset), a dashboard shell, account pages (profile/settings), and admin pages (users / roles / permissions).

---

## Quick start

```bash
# 1. Install dependencies
npm install

# 2. Copy the env template and adjust if needed
cp .env.example .env
#   (defaults to VITE_API_BASE_URL=http://localhost:8000/api)

# 3. Start the dev server (HMR on http://localhost:5173)
npm run dev

# 4. In another terminal, make sure the Django backend is running
#    on http://localhost:8000 (see ../backend/README.md)
```

> The dev server proxies `/api` → `http://localhost:8000` (see `vite.config.ts`), so you can also use relative API URLs in development.

---

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start Vite dev server with HMR |
| `npm run build` | Type-check + production build (`tsc -b && vite build`) |
| `npm run typecheck` | `tsc --noEmit` strict type-check |
| `npm run lint` | ESLint over `src/**/*.{ts,tsx}` |
| `npm run lint:fix` | ESLint with `--fix` |
| `npm run format` | Prettier write |
| `npm run test` | Run unit tests with Vitest (jsdom) |
| `npm run test:watch` | Vitest watch mode |
| `npm run test:e2e` | Run Playwright E2E tests in `e2e/` |

---

## Project structure

```
frontend/
├── e2e/                       # Playwright E2E tests (auth flow)
│   ├── fixtures.ts            # skipIfNoBackend + apiLoginAndVisit helpers
│   ├── auth-login.spec.ts
│   ├── auth-signup.spec.ts
│   └── auth-logout.spec.ts
├── src/
│   ├── api/                   # HTTP layer
│   │   ├── client.ts          # axios instance + JWT interceptor + envelope helpers
│   │   ├── auth.ts            # signup/login/logout/verify/refresh/reset
│   │   ├── me.ts              # GET/PATCH /api/me/ + change-password
│   │   ├── users.ts           # admin user CRUD + assign-role
│   │   ├── roles.ts           # admin roles CRUD + assign-permission + catalog
│   │   ├── types.ts           # shared TS interfaces (User, Role, etc.)
│   │   └── client.test.ts     # unit tests for interceptor + extractApiError
│   ├── components/
│   │   ├── ui/                # shadcn/ui-style primitives (built by hand)
│   │   │   ├── Button.tsx     Input.tsx  Label.tsx  Card.tsx
│   │   │   ├── Alert.tsx      Badge.tsx  Avatar.tsx Spinner.tsx
│   │   │   ├── DropdownMenu.tsx  Modal.tsx  Table.tsx  Tabs.tsx
│   │   │   └── index.ts       # barrel export
│   │   └── layout/
│   │       ├── DashboardShell.tsx  # sidebar + topbar + Outlet
│   │       ├── Sidebar.tsx
│   │       ├── Topbar.tsx          # user dropdown, notifications bell
│   │       ├── RoleBasedNav.tsx    # config-driven, filtered by role
│   │       ├── AuthLayout.tsx      # two-column brand+form layout
│   │       ├── ProtectedRoute.tsx  # + PublicRoute + FullScreenSpinner
│   │       └── AdminRoute.tsx
│   ├── hooks/
│   │   ├── useAuth.ts         # convenience wrapper around store + /me/ query
│   │   └── usePermissions.ts  # can(module) helper, role-based gating
│   ├── lib/
│   │   ├── constants.ts       # RoleName, MODULE_VISIBILITY, NAV_ITEMS
│   │   └── utils.ts           # cn(), getInitials, formatDate, isEmail, ...
│   ├── pages/
│   │   ├── auth/              # LoginPage, SignupPage, VerifyEmailPage,
│   │   │                       # ForgotPasswordPage, ResetPasswordPage
│   │   ├── account/           # ProfilePage, SettingsPage
│   │   ├── admin/             # UsersPage, RolesPage, PermissionsPage
│   │   ├── dashboard/         # DashboardPage
│   │   ├── NotFoundPage.tsx
│   │   └── PlaceholderPage.tsx
│   ├── stores/
│   │   ├── auth.ts            # Zustand store (tokens, user, localStorage)
│   │   └── auth.test.ts
│   ├── test/
│   │   └── setup.ts           # vitest setup (jest-dom, matchMedia stub)
│   ├── App.tsx                # top-level Router + Routes
│   ├── main.tsx               # React entry
│   ├── index.css              # Tailwind + CSS variables
│   └── vite-env.d.ts
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts             # + vitest config (merged)
├── tailwind.config.ts
├── postcss.config.js
├── playwright.config.ts
├── .eslintrc.cjs
├── .prettierrc
├── .env.example
└── .gitignore
```

---

## Routing

All routes are declared in `src/App.tsx`.

**Public**

| Path | Component |
|---|---|
| `/login` | LoginPage (wrapped in `PublicRoute`) |
| `/signup` | SignupPage (wrapped in `PublicRoute`) |
| `/verify-email/:token` | VerifyEmailPage |
| `/forgot-password` | ForgotPasswordPage |
| `/reset-password/:token` | ResetPasswordPage |

**Protected** (wrapped in `ProtectedRoute` + `DashboardShell`)

| Path | Component | Access |
|---|---|---|
| `/dashboard` | DashboardPage | all roles |
| `/profile` | ProfilePage | all roles |
| `/settings` | SettingsPage | all roles |
| `/admin/users` | UsersPage | `cj_admin`, `corp_admin`, `corp_exclusive` |
| `/admin/roles` | RolesPage | `cj_admin` only |
| `/admin/permissions` | PermissionsPage | `cj_admin` only |
| `/organizations` | PlaceholderPage | role-gated via sidebar |
| `/question-bank` | PlaceholderPage | role-gated |
| `/assessments` | PlaceholderPage | role-gated |
| `/career-profiling` | PlaceholderPage | role-gated |
| `/reports` | PlaceholderPage | role-gated |
| `/training` | PlaceholderPage | role-gated |
| `/counseling` | PlaceholderPage | role-gated |
| `/cms` | PlaceholderPage | `cj_admin` |

---

## Design system

### Color palette (Tailwind tokens)

| Token | Hex | Usage |
|---|---|---|
| `primary-600` | `#4F46E5` (indigo) | primary actions, links, focus rings |
| `slate-50` | `#F8FAFC` | app background |
| `white` | `#FFFFFF` | cards |
| `slate-900` | `#0F172A` | headings |
| `slate-600` | `#475569` | body text |
| `slate-200` | `#E2E8F0` | borders |
| `success` | `#10B981` (emerald) | success states |
| `danger` | `#EF4444` (red) | error / destructive |
| `warning` | `#F59E0B` (amber) | warning states |

### Typography

- **Sans**: Inter (loaded from Google Fonts in `index.html`)
- **Mono**: JetBrains Mono (loaded but only used for code/numbers when needed)

### Radius

- `sm` = 4px · `md` = 6px · `lg` = 8px · `xl` = 12px (modals)

### Shadows

- `shadow-sm` — cards (default)
- `shadow-md` — on hover
- `shadow-lg` — modals

### Tailwind CSS variables

`src/index.css` defines CSS variables for `--background`, `--foreground`, `--primary`, `--border`, etc. The `tailwind.config.ts` theme extends these into Tailwind colors (e.g. `bg-primary-600`, `text-foreground`).

---

## shadcn/ui-style components

The `src/components/ui/` directory contains a hand-built component library modelled on shadcn/ui, but **without** running `npx shadcn add` (which requires network access and interactive prompts).

- Built with [`class-variance-authority`](https://cva.style/) for variants + `clsx` + `tailwind-merge` (the `cn()` helper).
- All components are typed, forward-refs, and accessible (focus-visible rings, ARIA attributes where appropriate).
- Variants:
  - **Button**: `primary | secondary | outline | ghost | danger | link` × `sm | md | lg | icon` + `loading` prop.
  - **Badge**: `default | success | warning | danger | outline | primary`.
  - **Alert**: `default | error | success | warning` + `AlertTitle` / `AlertDescription`.
  - **Input**: `hasError` + `inputSize` props; works with `react-hook-form` `register()`.
  - **Modal**: portal-based, ESC + backdrop-close, scroll-lock, 4 sizes.
  - **DropdownMenu**: lightweight context-based menu (no Radix dependency).
  - **Tabs**: simple `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent` triple.

If you want to add a new component, copy the pattern from `Button.tsx` (cva + forwardRef + cn).

---

## API client & auth

`src/api/client.ts` exports `apiClient` — an axios instance configured with:

1. **Request interceptor** — attaches `Authorization: Bearer <access>` when a token is in localStorage.
2. **Response interceptor** — on 401, attempts a single token refresh via `/api/auth/token/refresh`; if it succeeds, retries the original request; if it fails, clears the auth store and redirects to `/login?reason=session_expired`.
3. **Envelope helpers** — `apiGet`, `apiPost`, `apiPatch`, `apiPut`, `apiDelete`, `apiGetPaged` unwrap the standard `{ message, data }` envelope automatically.
4. **Error extraction** — `extractApiError(err)` returns a human-readable message from the envelope, falling back to DRF `detail` / validation-field shape / network message.

The auth state lives in a Zustand store (`src/stores/auth.ts`) that persists to `localStorage` under the key `cj_auth_v1`. The store, the axios interceptor, and the test helpers all read/write the same key — so refreshing the page keeps the user signed in.

---

## Role-based navigation

`src/lib/constants.ts` declares:

- `RoleName` (9 roles: `cj_admin` ... `individual`)
- `MODULE_VISIBILITY` — a static map of which modules each role can see in the sidebar
- `NAV_ITEMS` — the config-driven nav list (label, path, lucide icon, allowed roles)

`<RoleBasedNav />` filters that list against the current user's role and renders `<NavLink>`s. `<AdminRoute module="users" />` guards routes that require access to a specific module — redirecting to `/dashboard?denied=...` if the user lacks the role.

---

## Forms & validation

All forms use [`react-hook-form`](https://react-hook-form.com/) + [`zod`](https://zod.dev/) schemas (`@hookform/resolvers/zod`). Inline error messages appear under each field on submit, plus a top-level `<Alert variant="error">` shows server-side errors extracted from the API envelope.

---

## Tests

### Unit tests (Vitest + Testing Library)

Run: `npm run test`

| File | What it covers |
|---|---|
| `src/api/client.test.ts` | Interceptor attaches Bearer token only when present; `extractApiError` reads envelope/DRF detail/validation shape |
| `src/stores/auth.test.ts` | `login()` persists tokens + user; `clear()` wipes them; `hydrate()` re-reads from localStorage |
| `src/pages/auth/LoginPage.test.tsx` | Renders email + password fields; shows validation errors on empty/invalid submit |
| `src/pages/auth/SignupPage.test.tsx` | Renders all 4 fields; validates password mismatch + weak password |
| `src/components/layout/RoleBasedNav.test.tsx` | `cj_admin` sees all 12 modules; `individual` sees 7 (no Users/Roles/CMS/Organizations/Question Bank); `corp_admin` and `sme_reviewer` subsets verified |

### E2E tests (Playwright)

Run: `npm run test:e2e`

| File | What it covers |
|---|---|
| `e2e/auth-login.spec.ts` | Visit `/login`, fill creds, submit, expect redirect to `/dashboard` |
| `e2e/auth-signup.spec.ts` | Visit `/signup`, fill form, submit, expect "check your email" success screen |
| `e2e/auth-logout.spec.ts` | Sign in via API, click user menu → Logout, expect redirect to `/login` |

E2E tests use a `skipIfNoBackend` fixture (in `e2e/fixtures.ts`) that pings `http://localhost:8000` and skips the suite if the backend isn't reachable — so `npm run test:e2e` won't fail in CI environments where only the frontend is deployed.

The dev server is auto-started by Playwright (see `playwright.config.ts → webServer`). To run E2E against a different URL, change `baseURL` in `playwright.config.ts`.

---

## Environment

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api` | Backend API base URL (no trailing slash) |

Copy `.env.example` to `.env` and adjust as needed.

---

## Notes & conventions

- **TypeScript strict mode** — no `any`. All component props are typed.
- **File naming** — `PascalCase.tsx` for components, `camelCase.ts` for utilities.
- **Accessibility** — every input has a `<Label htmlFor>`, every icon-only button has an `aria-label`, and focus-visible rings are applied via Tailwind `focus-visible:ring-*`.
- **Loading states** — `<Spinner>` for inline loading; `<Button loading>` shows an inline spinner.
- **Empty states** — every list shows a "No users found" / "No roles found" empty row.
- **Error states** — every API-driven view surfaces errors in an `<Alert variant="error">`.
- **Mobile-responsive** — sidebar collapses to a slide-in drawer below `lg:`; tables scroll horizontally; forms stack on small screens.
- **No emojis** in code/UI except the inline spinner (and the textual `CJ` logo).
- **No `npx shadcn` CLI** was used — every UI component was hand-built in `src/components/ui/`.
