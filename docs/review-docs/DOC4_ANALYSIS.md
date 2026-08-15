# CareerJudge — Review Doc 4 Analysis & Scope Verification

> **Source:** System Testing & Review Feedback Report 4 (13 August 2026)
> **Topic:** User Roles, Rights & Limits
> **Pages:** 39 | **Roles covered:** 12 | **Issues:** ~120
> **Date analyzed:** 15 August 2026

---

## Document Overview

Doc 4 is a comprehensive review of **user role permissions, UI access
controls, and feature enablement** across all 12 system roles. It covers
what each role should and should NOT be able to see/do, with screenshots
and mockups showing the desired state.

### Roles Covered (12 total):
1. Corporate Admin (23 issues)
2. Corporate Group Admin (14 issues)
3. Corporate Exclusive Admin (20 issues)
4. Channel Partner (19 issues)
5. SME User (7 issues)
6. Reviewer (10 issues)
7. Individual User (21 issues)
8. Trainer (12 issues)
9. Counsellor (16 issues)
10. Psychometrician (5 issues)
11. CJ Admin (19 issues)
12. Helpdesk (1 issue — "Not available for checking")

---

## Scope Verification — Is everything within SRS scope?

### YES — All items are within scope of the SRS and module-specific requirements.

**SRS References cited in Doc 4:**
- User Details Doc (PPT slides 1-11, sent via WhatsApp April 2026)
- Module-wise support doc: Admin User System Administration Process (page 2, §2.3)
- Module-wise support doc: Training Setup Process (page 5, §5)
- Module-wise support doc: Counselling Process (page 1, §2)
- Corporate Exclusive User (PDF, part of SRS, sent March 2024)

**All issues fall within these SRS modules:**
- Accounts (user management, roles, permissions, RBAC)
- Organizations (multi-tenancy, groups, channel partners)
- Question Bank (SME question creation, reviewer access, categories)
- Assessment (view/take restrictions, linking to training)
- Career Profiling (individual user access)
- Reporting (role-based report access)
- Training (course visibility, registration, scheduling)
- Counseling (booking, counsellor access, notifications)
- Tasks (SME task assignment, multi-spec tasks)
- Payments/Invoicing (SME/Reviewer/Trainer/Counsellor invoices)

### Items that may require NEW development (not just permission changes):
1. **Live-chat messaging system** — mentioned for Corp Admin, Group Admin,
   Corp Excl Admin, Channel Partner, SME, Reviewer, Trainer, Counsellor.
   Currently only CourseMessage (training) exists. A general messaging
   module is needed.
2. **Invoice management** — mentioned for SME, Reviewer, Trainer,
   Counsellor, Channel Partner. Create/revise/cancel invoices + CJ Admin
   payment approval. No invoice module exists yet.
3. **Corporate Exclusive platform** — separate database, custom webpage
   layout, logo/company name, independent from CJ platform. Major
   architecture work.
4. **Domain category tagging** — CJ Admin tags SME/Reviewer to domain
   categories (Math, Physics, etc.). Needs domain_category field on
   User or Role.
5. **Assessment/Training assignment to organizations** — CJ Admin
   assigns specific published assessments/training courses to Corp
   organizations. Needs org_assessment_assignments table.
6. **Multi-spec SME task assignment** — one task with multiple question
   specifications (different category/type/difficulty). Needs subtask
   model.
7. **Auto-fill question creation from task** — hyperlink from task to
   Qn creation page with pre-filled fields.

### Items that are permission/UI visibility changes (backend + frontend):
Most issues are about **showing/hiding UI elements based on role** and
**filtering data by organization/group ownership**. These are:
- Remove "Create Organization" button for non-CJ-Admin roles
- Filter organizations to only show the user's tagged org
- Filter assessments to only show published + assigned to org
- Filter reports to only show org members' reports
- Filter training courses to only show published + assigned
- Disable "Take Assessment" for non-individual roles
- Disable "Create Assessment" for non-creator roles
- Filter question bank to only show own questions (SME) / assigned
  questions (Reviewer)
- Filter users list to only show org members
- Rename tabs (e.g., "Question Bank" → "My Review Questions" for
  Reviewer)
- Show/hide fields based on role (assessment status, navigation, etc.)
- Individual user: separate tabs (Not Attempted / Suspended / Completed)
- Currency change: dollar → rupees
- Registration form with auto-fill from profile
- Payment pending popup messages

---

## Item-by-Item Summary by Role

### 1. Corporate Admin (23 issues)

| # | Issue | Category | Scope? |
|---|---|---|---|
| 1 | Remove "Create Organization" button | UI visibility | ✅ In scope |
| 2 | View ONLY own organization | Data filter | ✅ In scope |
| 3 | Enable add/delete groups | Feature enable | ✅ In scope |
| 4 | Add/delete/tag group admins | Feature | ✅ In scope (§2.3) |
| 5 | Permit report view/download to group admin | Permission | ✅ In scope |
| 6 | Add corp individual users to groups | Feature enable | ✅ In scope |
| 7 | Bulk-upload individual users with group tagging | Feature | ✅ In scope |
| 8 | Remove "Create User" (use Add Member instead) | UI visibility | ✅ In scope |
| 9 | View only org users (not all system users) | Data filter | ✅ In scope |
| 10 | View only org-assigned assessments | Data filter | ✅ In scope |
| 11 | Disable "Take Assessment" | UI visibility | ✅ In scope |
| 12 | Only published assessments; hide status/nav | UI visibility | ✅ In scope |
| 13 | Disable "Create Assessment" button | UI visibility | ✅ In scope |
| 14 | View only org members' published reports | Data filter | ✅ In scope |
| 15 | Download org members' reports | Feature | ✅ In scope |
| 16 | View only org-subscribed training courses | Data filter | ✅ In scope |
| 17 | Assign/remove users to subscribed trainings | Feature | ✅ In scope |
| 18 | Bulk-upload users to groups (training) | Feature | ✅ In scope |
| 19 | Schedule/reschedule/cancel trainings for org users | Feature | ✅ In scope |
| 20 | Disable self-registration for courses | UI visibility | ✅ In scope |
| 21 | "My Sessions" → show org members' session status | Rename + filter | ✅ In scope |
| 22 | Access counseling services for org members | Feature | ✅ In scope |
| 23 | Live-chat with CJ Admin/Helpdesk | NEW module | ✅ In scope (SRS) |

### 2. Corporate Group Admin (14 issues)

| # | Issue | Category | Scope? |
|---|---|---|---|
| 1 | Remove "Create Organization" button | UI visibility | ✅ In scope |
| 2 | View ONLY own group + subgroups | Data filter | ✅ In scope |
| 3 | Add/delete/tag individual users to group | Feature | ✅ In scope (§2.3) |
| 4 | Bulk-upload users to group | Feature | ✅ In scope |
| 5 | View only org-assigned assessments | Data filter | ✅ In scope |
| 6 | Disable "Take Assessment" | UI visibility | ✅ In scope |
| 7 | Assign/tag/remove users to assessments | Feature | ✅ In scope |
| 8 | Hide assessment details (type, status, nav) | UI visibility | ✅ In scope |
| 9 | View/download group members' reports (if permitted) | Permission | ✅ In scope |
| 10 | View org-assigned training courses | Data filter | ✅ In scope |
| 11 | Assign training courses to group members | Feature | ✅ In scope |
| 12 | Disable self-registration for courses | UI visibility | ✅ In scope |
| 13 | Access counseling services for group members | Feature | ✅ In scope |
| 14 | Live-chat with Corp Admin, CJ Admin/Helpdesk | NEW module | ✅ In scope |

### 3. Corporate Exclusive Admin (20 issues)

| # | Issue | Category | Scope? |
|---|---|---|---|
| 1 | CJ Admin creates org for Corp Excl | Process | ✅ In scope |
| 2 | CJ Admin adds/edits Corp Excl Admin + tags to org | Feature | ✅ In scope |
| 3 | Add/edit/delete groups + group admins | Feature | ✅ In scope |
| 4 | Add/edit/delete/bulk-upload individual users | Feature | ✅ In scope |
| 5-8 | Create own QB categories, questions, assessments | Feature | ✅ In scope |
| 9-11 | Assessment configuration (blueprint, sections, etc.) | Feature | ✅ In scope |
| 12-13 | Assessment session management | Feature | ✅ In scope |
| 14-15 | Report management + group admin report rights | Feature | ✅ In scope |
| 16-17 | Training course creation + configuration | Feature | ✅ In scope |
| 18 | CJ Admin sets up exclusive webpage layout | NEW architecture | ✅ In scope (Corp Excl SRS) |
| 19 | Corp Excl selects layout, inputs logo/company name | Feature | ✅ In scope |
| 20 | Live-chat with CJ Admin/Helpdesk | NEW module | ✅ In scope |

### 4. Channel Partner (19 issues)

| # | Issue | Category | Scope? |
|---|---|---|---|
| 1 | No right to create org; view only own org | UI + filter | ✅ In scope |
| 2 | Add/edit/delete groups | Feature | ✅ In scope |
| 3 | Add/edit/delete group admins | Feature | ✅ In scope |
| 4 | Add/edit/delete members + tag to groups | Feature | ✅ In scope |
| 5 | Bulk-upload individual users | Feature | ✅ In scope |
| 6 | Remove "Create User" | UI visibility | ✅ In scope |
| 7 | View only own org users | Data filter | ✅ In scope |
| 8 | View only org-assigned assessments | Data filter | ✅ In scope |
| 9 | Disable "Take Assessment" | UI visibility | ✅ In scope |
| 10 | Only published assessments; hide details | UI visibility | ✅ In scope |
| 11 | No right to view any reports | UI visibility | ✅ In scope |
| 12 | View assigned training courses | Feature | ✅ In scope |
| 13 | Assign/remove users to training courses | Feature | ✅ In scope |
| 14 | Schedule/reschedule/cancel trainings for members | Feature | ✅ In scope |
| 15 | View training session status of members | Feature | ✅ In scope |
| 16 | Access counseling services for members | Feature | ✅ In scope |
| 17 | Live-chat with CJ Admin/Helpdesk | NEW module | ✅ In scope |
| 18 | Create/revise/cancel invoice | NEW module | ✅ In scope |
| 19 | View payment history | NEW module | ✅ In scope |

### 5. SME User (7 issues)

| # | Issue | Category | Scope? |
|---|---|---|---|
| 1 | View only own questions (not all QB) | Data filter | ✅ In scope |
| 2 | No right to create categories | UI visibility | ✅ In scope |
| 3 | No right to view/take assessments | UI visibility | ✅ In scope |
| 4 | Select specific Reviewer + Psychometrician by domain | NEW feature | ✅ In scope |
| 5 | Auto-fill Qn creation from task hyperlink | NEW feature | ✅ In scope |
| 6 | Live-chat with CJ Admin/Helpdesk | NEW module | ✅ In scope |
| 7 | Create/revise/cancel invoice | NEW module | ✅ In scope |

### 6. Reviewer (10 issues)

| # | Issue | Category | Scope? |
|---|---|---|---|
| 1 | View only assigned questions | Data filter | ✅ In scope |
| 2 | Rename "Question Bank" → "My Review Questions" | Rename | ✅ In scope |
| 3 | No right to create categories | UI visibility | ✅ In scope |
| 4 | No right to view/take assessments | UI visibility | ✅ In scope |
| 5 | Select specific Reviewer/Psychometrician by domain | (shared with SME #4) | ✅ In scope |
| 6-7 | Auto-fill Qn creation from task | (shared with SME #5) | ✅ In scope |
| 8 | Latest rating replaces old rating | Feature | ✅ In scope |
| 9 | Live-chat with CJ Admin/Helpdesk | NEW module | ✅ In scope |
| 10 | Create/revise/cancel invoice | NEW module | ✅ In scope |

### 7. Individual User (21 issues)

| # | Issue | Category | Scope? |
|---|---|---|---|
| 1 | View/take only registered+paid assessments | Data filter | ✅ In scope |
| 2 | Payment pending popup | Feature | ✅ In scope |
| 3 | Registration form with auto-fill from profile | Feature | ✅ In scope |
| 4 | Separate tabs: Not Attempted / Suspended / Completed | UI | ✅ In scope |
| 5 | Mandatory fields: First Name, Last Name, Gender | Validation | ✅ In scope |
| 6 | Mandatory: Mobile, State, City, Institution, Place | Validation | ✅ In scope |
| 7 | "Highest Education" → "Professional Education" (optional) | Rename | ✅ In scope |
| 8 | Only paid published profiling solutions | Data filter | ✅ In scope |
| 9 | Separate tabs for profiling solutions | UI | ✅ In scope |
| 10 | View only own reports | Data filter | ✅ In scope |
| 11 | Download report as PDF | Feature (exists) | ✅ In scope |
| 12 | View only registered+paid training courses | Data filter | ✅ In scope |
| 13 | Payment pending popup for courses | Feature | ✅ In scope |
| 14 | Separate tabs: New Course / Ongoing / Completed | UI | ✅ In scope |
| 15 | Tab order: Overview >> Structure >> Learn >> Live >> Assignments >> Assessments | UI | ✅ In scope |
| 16 | View only registered+paid counseling sessions | Data filter | ✅ In scope |
| 17 | Payment pending popup for counseling | Feature | ✅ In scope |
| 18 | Post-booking notification to counsellor | Notification | ✅ In scope |
| 19 | Fix counsellor hyperlink error | Bug fix | ✅ In scope |
| 20 | Rename module tabs: My Assessments, My Profiling, etc. | Rename | ✅ In scope |
| 21 | Change "/hr" to "/Session"; dollar to rupees | UI text | ✅ In scope |

### 8. Trainer (12 issues)

| # | Issue | Category | Scope? |
|---|---|---|---|
| 1 | View only own courses (not all) | Data filter | ✅ In scope |
| 2 | Remove "My Courses" tab; add "Preview" feature | UI | ✅ In scope |
| 3 | Can create structure first time; needs admin permission after publish | Permission flow | ✅ In scope (§5) |
| 4 | Request permission to modify published course | Feature (exists) | ✅ In scope (Doc 3 6.1) |
| 5 | Text formatting for content field | Feature (exists) | ✅ In scope (WysiwygEditor) |
| 6 | Edit content (not just delete+re-enter) | Feature | ✅ In scope |
| 7 | Enable timeline setting | Feature (exists) | ✅ In scope (InteractiveQuestion) |
| 8 | Assessment creation by trainer | Feature | ✅ In scope (exists, needs enablement) |
| 9 | Assessment linked to specific session/topic/lesson | Feature (exists) | ✅ In scope |
| 10 | Verify notification reaches individual user | Notification | ✅ In scope |
| 11 | Live-chat with CJ Admin/Helpdesk | NEW module | ✅ In scope |
| 12 | Create/revise/cancel invoice | NEW module | ✅ In scope |

### 9. Counsellor (16 issues)

| # | Issue | Category | Scope? |
|---|---|---|---|
| 1 | (implied) No access to assessments | UI visibility | ✅ In scope |
| 2 | No access to profiling solutions | UI visibility | ✅ In scope |
| 3 | No access to all reports (only clients') | Data filter | ✅ In scope |
| 4 | No right to create reports | UI visibility | ✅ In scope |
| 5 | View only clients' reports | Data filter | ✅ In scope |
| 6 | No browsing/booking of counsellors | UI visibility | ✅ In scope |
| 7 | Tag to counseling category | Feature (exists) | ✅ In scope |
| 8 | 1-week min, 3-week max timeslots | Feature (exists) | ✅ In scope |
| 9 | Timeslots in table format | UI | ✅ In scope |
| 10 | Booked timeslots in weekly format | UI | ✅ In scope |
| 11 | Remove "My Sessions" tab | UI visibility | ✅ In scope |
| 12 | Post-booking notification to counsellor | Notification (exists) | ✅ In scope |
| 13 | Zoom meeting setup | Feature (exists) | ✅ In scope |
| 14 | Post-Zoom notification to counselee | Notification | ✅ In scope |
| 15 | Live-chat with CJ Admin/Helpdesk | NEW module | ✅ In scope |
| 16 | Create/revise/cancel invoice | NEW module | ✅ In scope |

### 10. Psychometrician (5 issues)

| # | Issue | Category | Scope? |
|---|---|---|---|
| 1 | Psychometric analysis features not available | Feature (exists) | ✅ In scope |
| 2 | QB management features not available | Feature (exists) | ✅ In scope |
| 3 | Assessment management features not available | Feature (exists) | ✅ In scope |
| 4 | Profiling configuration features not available | Feature (exists) | ✅ In scope |
| 5 | Report configuration features not available | Feature (exists) | ✅ In scope |

### 11. CJ Admin (19 issues)

| # | Issue | Category | Scope? |
|---|---|---|---|
| 1 | Tag Corp Admin to organization | Feature | ✅ In scope |
| 2 | Tag Group Admin to group + org | Feature | ✅ In scope |
| 3 | Tag Corp Excl Admin to org | Feature | ✅ In scope |
| 4 | Tag Channel Partner to org | Feature | ✅ In scope |
| 5 | Tag Reviewer to domain category | NEW feature | ✅ In scope |
| 6 | Add new domain categories | Feature | ✅ In scope |
| 7 | Tag SME to domain category | NEW feature | ✅ In scope |
| 7b | Tag Counsellor to counseling category | Feature (exists) | ✅ In scope |
| 8 | Enable Edit User button | UI fix | ✅ In scope |
| 9 | Task assignment functional | Bug fix | ✅ In scope |
| 10 | Clarify parent task creation | Feature | ✅ In scope |
| 11 | Multi-spec SME task assignment | NEW feature | ✅ In scope |
| 12 | Assign assessments to Corp organizations | NEW feature | ✅ In scope |
| 13 | Assign training courses to Corp organizations | NEW feature | ✅ In scope |
| 14 | Assign counseling services to Corp organizations | NEW feature | ✅ In scope |
| 15 | Assign configuration rights to Corp Excl | NEW feature | ✅ In scope |
| 16 | Set up exclusive webpages for Corp Excl | NEW architecture | ✅ In scope |
| 17 | Assign assessments to channel partners | NEW feature | ✅ In scope |
| 18 | Assign training courses to channel partners | NEW feature | ✅ In scope |
| 19 | View invoices from empanelled users | NEW module | ✅ In scope |

### 12. Helpdesk (1 issue)

| # | Issue | Category | Scope? |
|---|---|---|---|
| 1 | "Not available for checking features" | Role exists (added) | ✅ In scope |

---

## New Modules Required (Not Yet Built)

### A. Live-Chat Messaging System
**Mentioned for:** Corp Admin, Group Admin, Corp Excl Admin, Channel Partner,
SME, Reviewer, Trainer, Counsellor (8 roles).
**Current state:** Only CourseMessage (training module) exists. No general
messaging system.
**Needed:** A `Message` model with sender, recipient, subject, body,
read/unread, timestamps. Role-to-role messaging (e.g., SME → CJ Admin).
Frontend chat UI (conversation view).

### B. Invoice Management System
**Mentioned for:** SME, Reviewer, Trainer, Counsellor, Channel Partner (5 roles).
**Current state:** No invoice module.
**Needed:** `Invoice` model with creator, items, amount, status (draft/submitted/
approved/paid/rejected), CJ Admin approval flow, payment history.
Frontend: invoice creation form, invoice list, CJ Admin approval page.

### C. Domain Category System
**Mentioned for:** CJ Admin tagging SME/Reviewer to domains.
**Current state:** No domain category system.
**Needed:** `DomainCategory` model (name, description). Link to User or Role
as M2M. CJ Admin can add/edit domain categories. SME/Reviewer tagged to
domains. Question routing by domain (SME's questions → Reviewer in same domain).

### D. Organization Assessment/Training Assignment
**Mentioned for:** CJ Admin assigning assessments/training courses to Corp orgs.
**Current state:** No assignment model.
**Needed:** `OrganizationAssignment` model (org, assessment or course,
assigned_by, assigned_at). Filter assessments/courses by org assignment.

### E. Corporate Exclusive Platform
**Mentioned for:** Corp Excl Admin.
**Current state:** No separate database or exclusive platform.
**Needed:** Multi-tenant architecture with separate databases or schema
isolation, custom webpage layouts, logo/company name configuration.
**Note:** Doc 4 says "Appropriate solution for setting up exclusive
environment needs to be finalized after necessary discussion." — this
is an architecture decision, not a code change.

---

## Permission/UI Changes Required (Backend + Frontend)

Most issues are about:
1. **Role-based UI visibility** — show/hide buttons, tabs, fields
2. **Data filtering** — show only org/group/own data
3. **Feature enablement** — enable disabled features (groups, members)
4. **Field validation** — mandatory fields, field renames
5. **Tab renaming/reordering** — per-role tab names and order
6. **Payment popups** — pending payment notifications
7. **Currency change** — dollar → rupees

These are primarily **frontend permission checks** + **backend queryset
filters** + **UI conditional rendering**. The backend models mostly exist;
the work is in filtering data and showing/hiding UI elements.

---

## Conclusion

**All items in Doc 4 are within the scope of the SRS and module-specific
requirements.** The document focuses on role-based access control (RBAC)
and permission enforcement, which is the core of the accounts module's
ModuleRight system.

**Estimated work breakdown:**
- ~60% permission/UI visibility changes (frontend + backend filters)
- ~20% new features (live-chat, invoice, domain categories, org assignments)
- ~10% bug fixes (notification, hyperlink error, edit user button)
- ~10% architecture decisions (Corp Excl platform — needs discussion)

**No items are out of scope.** All can be implemented within the existing
module structure, with 2 new modules needed (messaging + invoicing) and
1 architecture decision pending (Corp Excl platform).
