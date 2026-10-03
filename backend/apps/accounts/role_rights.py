"""Module rights of the built-in (system) roles — the single source of truth.

``seed_demo`` and the ``sync_system_role_rights`` data migrations both apply
this table EXACTLY: rights listed here are granted and any other right on a
system role is removed. Custom roles are never touched.

Changing a right therefore takes two steps: edit this table, and add a data
migration that syncs the system roles to the new table (copy the table into
the migration so it stays frozen at that point in history). A test compares
this table with a freshly migrated database to catch drift.

Basis: signed User Details.pdf role maps, SRS, Docs 1-9, and the client's
Report 4 (13 Aug 2026) / Report 9 (1 Oct 2026) rights clarifications.
"""

ROLE_PERMISSIONS: dict[str, list[tuple[str, str]]] = {
    "cj_admin": [
        ("accounts", "view"),
        ("accounts", "add"),
        ("accounts", "change"),
        ("accounts", "delete"),
        ("organizations", "view"),
        ("organizations", "add"),
        ("organizations", "change"),
        ("organizations", "delete"),
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        ("question_bank", "delete"),
        ("question_bank", "approve"),
        ("question_bank", "reject"),
        ("question_bank", "review"),
        ("assessment", "view"),
        ("assessment", "add"),
        ("assessment", "change"),
        ("assessment", "delete"),
        # Report 9 #89/90/118/119: CJ Admin could open Profiling and Reports
        # but not create or set anything up in them.
        ("career_profiling", "view"),
        ("career_profiling", "add"),
        ("career_profiling", "change"),
        ("career_profiling", "delete"),
        ("reporting", "view"),
        ("reporting", "add"),
        ("reporting", "change"),
        ("reporting", "delete"),
        ("reporting", "generate_report"),
        ("training", "view"),
        ("training", "add"),
        ("training", "change"),
        ("training", "delete"),
        ("counseling", "view"),
        ("counseling", "add"),
        ("counseling", "change"),
        ("counseling", "delete"),
        ("cms", "view"),
        ("cms", "add"),
        ("cms", "change"),
        ("cms", "delete"),
        ("notifications", "view"),
        ("tasks", "view"),
        ("tasks", "add"),
        ("tasks", "change"),
        ("tasks", "delete"),
        ("tasks", "assign"),
        ("tasks", "approve"),
        # H14: CJ Admin reviews/approves/rejects/pays every invoice.
        ("invoicing", "view"),
        ("invoicing", "add"),
        ("invoicing", "approve"),
        ("invoicing", "reject"),
        ("invoicing", "change"),
    ],
    "helpdesk": [
        # Doc 8 §4: Help Desk is a liaison with the "minimum user role".
        # Report 9 #115/#117 (rights audit, 3 Oct 2026): booked sessions are
        # VIEW ONLY — no 'change' (it let him confirm any pending session)
        # and no booking.
        ("training", "view"),
        ("counseling", "view"),
        ("notifications", "view"),
        ("accounts", "view"),
        # Report 9 #112-#114: VIEW-ONLY access to every organization,
        # assessment and profiling solution (no write rights).
        ("organizations", "view"),
        ("assessment", "view"),
        ("career_profiling", "view"),
    ],
    "corp_admin": [
        # User Details p.3 + Report 9 #1-#14: manages his own organization's
        # members, schedules and reports only (scoped in the viewsets); he
        # cannot create organizations, assessments or courses.
        ("accounts", "view"),
        ("accounts", "add"),
        ("accounts", "change"),
        # Doc 9 §2.4 / Report 9 #5 (rights audit, 3 Oct 2026): deletes his
        # own organization's users — never himself, other managers or staff
        # (guarded in views_admin.UserViewSet.destroy).
        ("accounts", "delete"),
        ("organizations", "view"),
        ("organizations", "change"),
        ("assessment", "view"),
        ("reporting", "view"),
        ("reporting", "generate_report"),
        ("training", "view"),
        ("counseling", "view"),
    ],
    "corp_exclusive": [
        # Report 9 #35-#37, #45, #46, #49: runs his own organization (members,
        # groups, schedules, website branding), scoped in the viewsets.
        ("accounts", "view"),
        ("accounts", "add"),
        ("accounts", "change"),
        # Report 4 CE-4 / Report 9 #36 (rights audit, 3 Oct 2026): deletes
        # his own organization's users (same destroy guard as Corp Admin).
        ("accounts", "delete"),
        # Report 9 #34: creates his own organizations (visible only to him).
        ("organizations", "view"),
        ("organizations", "add"),
        ("organizations", "change"),
        # Report 9 #39-#44/#47: authors his organization's PRIVATE question
        # bank, assessments, reports and courses (scoped to his organization).
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        ("question_bank", "delete"),
        ("assessment", "view"),
        ("assessment", "add"),
        ("assessment", "change"),
        ("assessment", "delete"),
        ("reporting", "view"),
        ("reporting", "add"),
        ("reporting", "change"),
        ("reporting", "delete"),
        ("reporting", "generate_report"),
        ("training", "view"),
        ("training", "add"),
        ("training", "change"),
        ("training", "delete"),
    ],
    "psychometrician": [
        # Psychometrician: full QB access (configures psychometric properties)
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        # Report 9 #107 (rights audit, 3 Oct 2026): his delete of a question
        # or category only FILES a deletion request for CJ Admin (the route
        # needs this right; QuestionViewSet/CategoryViewSet.destroy never
        # delete directly for him).
        ("question_bank", "delete"),
        ("question_bank", "review"),
        # Psychometrician is the primary assessment author per SRS UC029
        # "Prepare Assessment Blueprint" — full CRUD on assessments.
        ("assessment", "view"),
        ("assessment", "add"),
        ("assessment", "change"),
        ("assessment", "delete"),
        # Doc 5 §1 / Doc 4 / User Details p.10 "Design Report": the
        # psychometrician builds profiling solutions and report designs
        # (Report 9 #89/#90).
        ("career_profiling", "view"),
        ("career_profiling", "add"),
        ("career_profiling", "change"),
        # Report 9 #107: his delete of a profiling solution files a request
        # for CJ Admin (ProfilingSolutionViewSet.destroy) — never direct.
        ("career_profiling", "delete"),
        ("reporting", "view"),
        ("reporting", "add"),
        ("reporting", "change"),
        ("reporting", "generate_report"),
        # H14: empanelled role — bills CJ Admin for review work (Doc 4).
        ("invoicing", "view"),
        ("invoicing", "add"),
    ],
    "sme": [
        # SME: creates/edits/deletes OWN questions (unreviewed only).
        # Once reviewed, can only request_delete (admin approves).
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        ("question_bank", "delete"),
        ("question_bank", "request_delete"),
        # Report 4 SME-3 / Report 9 #64: SME has no right to view/take assessments.
        # H14: empanelled role — bills CJ Admin for question authoring (Doc 4).
        ("invoicing", "view"),
        ("invoicing", "add"),
    ],
    "reviewer": [
        # Reviewer: reviews questions, approves/rejects. No create/edit/delete.
        ("question_bank", "view"),
        ("question_bank", "review"),
        ("question_bank", "approve"),
        ("question_bank", "reject"),
        # Report 4 Reviewer-4: reviewer has no right to view/take assessments.
        # H14: empanelled role — bills CJ Admin for review work (Doc 4).
        ("invoicing", "view"),
        ("invoicing", "add"),
    ],
    "trainer": [
        ("training", "view"),
        ("training", "add"),
        ("training", "change"),
        ("training", "delete"),
        # Rights audit (3 Oct 2026): no document gives a Trainer user access
        # — ("accounts", "view") returned the whole CJ user list; removed.
        ("assessment", "view"),
        # Report 3 §4.1: trainers author their own course assessments using
        # the CJ Question Bank (scoped to created_by in the viewsets).
        ("assessment", "add"),
        ("assessment", "change"),
        ("assessment", "delete"),
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        # Rights audit (3 Oct 2026, user decision): a trainer deletes his OWN
        # DRAFT questions only (QuestionViewSet.destroy).
        ("question_bank", "delete"),
        # H14: empanelled role — bills CJ Admin for training delivery (Doc 4).
        ("invoicing", "view"),
        ("invoicing", "add"),
    ],
    "group_admin": [
        # Works inside his own group only (scoped in the viewsets): members
        # and assessment schedules for his group (Report 9 #26).
        ("accounts", "view"),
        # Report 9 #24: adds (and bulk-uploads) Corporate Individuals into
        # his own group only.
        ("accounts", "add"),
        ("assessment", "view"),
        ("assessment", "assign"),
        ("organizations", "view"),
        ("organizations", "change"),
        # Report 9 #27: views/downloads his group members' reports when the
        # Corp Admin permits it (the permission is checked in the views).
        ("reporting", "view"),
    ],
    "counsellor": [
        ("counseling", "view"),
        ("counseling", "add"),
        ("counseling", "change"),
        # Rights audit (3 Oct 2026): no document gives the Counsellor user
        # access — ("accounts", "view") returned the whole CJ user list; removed.
        # Report 4 Counsellor-1/2 + Report 9 #85/#86: no assessment, profiling
        # or report access.
        # H14: empanelled role — bills CJ Admin for counselling delivery (Doc 4).
        ("invoicing", "view"),
        ("invoicing", "add"),
    ],
    "channel_partner": [
        # Channel Partner: manages the individual users of his own organization
        # (scoped in the viewsets). Report 9 #57/#58: no assessment authoring
        # and no access to users' reports.
        ("accounts", "view"),
        ("accounts", "add"),
        ("accounts", "change"),
        # Report 4 CP-4 / Report 9 #56 (rights audit, 3 Oct 2026): deletes
        # his own organization's users (same destroy guard as Corp Admin).
        ("accounts", "delete"),
        # Report 9 #53: creates his own organizations (visible only to him).
        ("organizations", "view"),
        ("organizations", "add"),
        ("organizations", "change"),
        ("assessment", "view"),
        # H14: empanelled role — bills CJ Admin for commission (Doc 4).
        ("invoicing", "view"),
        ("invoicing", "add"),
    ],
    "individual": [
        ("assessment", "view"),  # can take assessments
        # Report 9 #76: browses PUBLISHED profiling solutions (scoped in the view).
        ("career_profiling", "view"),
        ("reporting", "view"),  # can view own reports
        ("training", "view"),  # can browse + register for courses
        ("training", "add"),  # can register (register action = 'add')
        ("training", "change"),  # can track progress (progress action = 'change')
        ("counseling", "view"),  # can browse counsellors
        ("counseling", "add"),  # can book sessions
        ("counseling", "change"),  # can submit feedback
    ],
}


def sync_role_rights(role_model, right_model, table) -> dict[str, tuple[int, int]]:
    """Make every system role's rights match ``table`` exactly.

    Works with real or historical (migration) models. Returns
    ``{role_name: (added, removed)}`` for logging.
    """
    changes: dict[str, tuple[int, int]] = {}
    for role_name, perms in table.items():
        role = role_model.objects.filter(name=role_name).first()
        if role is None:
            continue
        wanted = set(perms)
        current = {(r.module, r.action): r for r in right_model.objects.filter(role=role)}
        added = 0
        for module, action in wanted - current.keys():
            right_model.objects.create(role=role, module=module, action=action)
            added += 1
        stale = [current[key].pk for key in current.keys() - wanted]
        if stale:
            right_model.objects.filter(pk__in=stale).delete()
        changes[role_name] = (added, len(stale))
    return changes
