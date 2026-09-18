# Scope & Estimate — Corporate / Corporate-Exclusive Module

*Signed requirement. Sources: SRS use cases CJ_UC002–006, UC030, UC043; the
**Corporate-Exclusive User** spec (separate mail) CJ_UC052–055; Doc 9 (Admin
Process) §2.1–2.4; Doc 4 (General Report) §"corporate managers view employees".*

> **Status: SIGNED, PARTIALLY FOUNDED, LARGELY UNBUILT.**
> An `organizations` app exists (Organization / Group / OrganizationMember /
> OrganizationAssignment models + generic CRUD API + two React pages + four
> corporate roles seeded). But it is **generic admin CRUD, not a corporate
> self-service platform** — the defining corporate behaviours (per-tenant
> branded websites, page customization, assessment scheduling, org-scoped data
> isolation, org-scoped content visibility, corporate report access) are
> **absent or modelled-but-unwired**. This is the last signed gap after PSY-A1.

---

## 1. Signed requirement inventory

| Clause | Title | Actor | Source |
|---|---|---|---|
| CJ_UC055 | **Create Website** — per-corporate branded site: own URL, **separate database**, generated admin credentials, layout selection | CJ Admin | Corporate-Exclusive spec |
| CJ_UC054 | **Customize page** — layout + logo + company name | Corporate Exclusive Admin | Corporate-Exclusive spec |
| CJ_UC052 | **Create Corporate Group** — Group Name + Region/Division | Corporate Admin | Corporate-Exclusive spec |
| CJ_UC053 | **Schedule Assessment** — pick assessment + date/time, notify employees | Corporate Admin, Group Admin | Corporate-Exclusive spec |
| CJ_UC002 | Add user — corporate admin adds corporate individuals; corporate/corp-exclusive report-view permission | CJ Admin, Corporate Admin | SRS |
| CJ_UC003 | Edit user — corporate users NOT modifiable by CJ Admin | CJ Admin | SRS |
| CJ_UC004 | Delete user — CJ Admin cannot delete corporate individuals | CJ Admin | SRS |
| CJ_UC005 / UC006 | Manage / View Profile (corporate roles) | Corporate Admin, Corp-Exclusive Admin, Channel Partner | SRS |
| CJ_UC030 | Take assessment — Corporate & Corporate-Exclusive individuals (only org-assigned assessments) | Corporate Individuals | SRS |
| CJ_UC043 | Add user – Channel Partner | Channel Partner | SRS |
| Doc 9 §2.1–2.4 | Define corporate roles; corporate onboarding (org name, **PAN/TAN**, corporate address); corporate admin adds group admins + corporate individuals + **bulk upload**; corporate user management | CJ Admin, Corporate Admin | Doc 9 |
| Doc 4 | Corporate managers view **their employees'** assessment performance | Corporate managers | Doc 4 |

## 2. What exists today (foundation)

- **Models** (`apps/organizations/models.py`): `Organization` (name, type corporate/corp_exclusive/channel_partner, status, contact, generic address), `Group` (name + description only), `OrganizationMember` (user↔org↔group, `is_admin`), `OrganizationAssignment` (assign assessment/training/counseling to an org — **defined but never used by any view**), `DomainCategory`.
- **API** (`apps/organizations/`): generic CRUD for orgs / groups / members, gated by `organizations.view/add/change/delete` ModuleRights.
- **Frontend**: `OrganizationsPage.tsx`, `OrganizationDetailPage.tsx` (list/create/delete orgs; add/remove groups & members). Generic admin CRUD.
- **Roles**: `corp_admin`, `corp_exclusive`, `group_admin`, `channel_partner` seeded with ModuleRights; corporate roles have `accounts.add`.

## 3. Gap analysis (current → signed)

| Capability | Status | Gap |
|---|---|---|
| **Create Website** (UC055) | ❌ ABSENT | No tenancy, subdomain, branding, layout, DB routing, or credential generation anywhere. The single biggest piece. |
| **Customize Page** (UC054) | ❌ ABSENT | No logo / company-name / layout / theme fields; no customization UI; no branded-portal rendering. |
| **Create Corporate Group** (UC052) | 🟡 PARTIAL | Group CRUD exists; **Region/Division field missing**; not exposed as a corporate-admin self-service flow. |
| **Schedule Assessment** (UC053) | ❌ ABSENT | No assessment-schedule model, no notify-employees path, no UI. (`assessment.assign` right is seeded to group_admin but no view implements it.) |
| **Corporate user management** (UC002/003/004, Doc 9 §2.3/2.4) | 🟡 PARTIAL | `accounts.add` granted, but user creation is **not org-scoped** (no auto `OrganizationMember` link); **no bulk upload**; edit/inactivate-scoped-to-own-org not enforced; CJ-Admin-cannot-modify-corporate rule not enforced. |
| **Org-scoped data isolation** | ❌ ABSENT | `OrganizationViewSet` returns ALL orgs to any viewer; no queryset is filtered by the requester's org anywhere except the individual-delete guard. |
| **Org-scoped content visibility** (UC030) | 🟡 MODELLED, UNWIRED | `OrganizationAssignment` exists but no serializer/view/queryset uses it — corporate individuals currently see all content, not just assigned. |
| **Corporate report access** (Doc 4) | 🟡 PARTIAL | Corporate roles have `reporting.view`, but reporting views apply **no org filter** — a corporate manager would see everyone, not just their employees. |
| **Onboarding fields** (Doc 9 §2.2) | 🟡 PARTIAL | Missing **Manager name** and **PAN/TAN**; address & contact map to generic fields. |

## 4. The decision that drives the estimate — "separate database" → **DECIDED: Option B (logical multi-tenancy)**

CJ_UC055 literally says the system *"creates a website URL, **separate database** and generates credentials for the admin,"* and *"A separate database should [be] maintained for the generated website."*

> **DECISION (19 Sep 2026): Option B — logical multi-tenancy.** The build honours
> "separate database" through **strict row-level org isolation**, not a physical
> database per corporate. Estimate locked at **≈ 24–30 dev-days**.

- **Option B — Logical multi-tenancy (CHOSEN).** One database; each corporate gets its **own subdomain/URL**, **strict row-level org isolation** (every corporate record carries/derives its `organization`, and every corporate-facing queryset is org-scoped), **per-tenant branding** (logo/layout/company name), and **generated corporate-admin credentials**. Delivers everything the corporate customer observes — their own branded site, their own admin, their own isolated data — without per-tenant DB ops. Modern SaaS standard.
- **Option A — Physical multi-tenancy (NOT chosen).** One database per corporate: per-tenant DB provisioning, connection routing, per-tenant migrations, backup/ops per tenant. Heavy, permanent ops burden; +10–15 dev-days. Rejected.

**Note for the client conversation:** we are reading "separate database" as *data
isolation per corporate*, delivered logically. If the client specifically
requires physically separate database instances, this reverts to Option A (see
§5 totals) — worth a one-line written confirmation to avoid a later dispute.

## 5. Target design & work breakdown

| WP | Work | Effort (dev-days, Option B) |
|---|---|---|
| **A. Org-scoping foundation** | Request→organization resolution (via `OrganizationMember`); a reusable org-scoping queryset mixin; wire `OrganizationAssignment` so corporate individuals see only assigned assessments/training/counseling; apply across assessment/reporting/training/counseling views. *Cross-cutting; the spine everything else hangs on.* | 4–5 |
| **B. Corporate user management** | Org-scoped add-user (auto-create `OrganizationMember`); **CSV bulk upload** (Doc 9 §2.3); edit/inactivate scoped to own org; enforce "CJ Admin cannot modify/delete corporate users"; onboarding fields **Manager name + PAN/TAN**; fix the seed/test `organizations.add` inconsistency. | 3–4 |
| **C. Corporate Group completion** | Add **Region/Division** to `Group`; corporate-admin group-management self-service flow. | 1 |
| **D. Schedule Assessment** | New `AssessmentSchedule` (org/group + assessment + datetime + target members); notify employees via the notifications app; corp-admin/group-admin scheduling UI. | 3 |
| **E. Customize Page / branding** | Logo + company-name + layout/theme fields (new `OrganizationBranding` or fields on Organization); customization UI; render the corporate portal with the branding. | 3–4 |
| **F. Create Website / tenancy** | Subdomain/tenant resolution middleware; provision a corporate portal (URL + branding + generated corp-admin credentials); CJ-Admin "Create Website" flow. *(Option A adds per-tenant DB routing + provisioning: +10–15.)* | 5–8 |
| **G. Corporate report access** | Org-scope reporting so corporate managers see only their employees' results (Doc 4). | 2 |
| **H. Tests + FE verification** | Backend tests for scoping/scheduling/branding/tenancy; frontend tsc + vitest; permission-boundary tests. | 3 |
| **Total (Option B)** | | **≈ 24–30 dev-days** |
| **Total (Option A)** | | **≈ 35–45 dev-days** |

## 6. Open questions to confirm with the client

1. ~~**"Separate database"** — logical vs physical isolation?~~ **RESOLVED (19 Sep): Option B, logical multi-tenancy** (§4). *(A written client confirmation that logical isolation satisfies the clause is still advisable.)*
2. **Website hosting** — a subdomain per corporate on the main platform (`acme.careerjudge.…`), or fully separate domains? DNS/SSL ownership?
3. **Bulk upload format** — confirm the CSV columns for corporate individuals (Name, Official Email, Employee ID per Doc 9 §2.3).
4. **Channel Partner** — same corporate flows, or a distinct (reseller) flow? UC043 is thin in the SRS.
5. **Content assignment** — does the CJ Admin assign assessments to a corporate (existing `OrganizationAssignment` intent), or does the corporate admin self-select from a catalogue?

## 7. Recommendation & phasing

Corporate-Exclusive is **signed and owed**; the audit binder must reflect it as SIGNED-PENDING (it currently omits corporate entirely, so the "PASS" is scoped only to the tracked subset). Suggested build order — each phase is independently shippable and testable:

1. **Phase 1 — Foundation & user management (WP-A, B, C):** org-scoping spine + corporate user management + group completion. Makes corporate roles genuinely usable and data-isolated. *(~8–10 dd.)*
2. **Phase 2 — Corporate operations (WP-D, G):** schedule assessments for employees + corporate report access. *(~5 dd.)*
3. **Phase 3 — Branded portals (WP-E, F):** customize page + create website (the multi-tenancy piece, per the Option A/B decision). *(~8–12 dd, Option B.)*

Confirm the Option A/B decision (§4/§6.1) before Phase 3 — it changes the estimate by ~10–15 dev-days.
