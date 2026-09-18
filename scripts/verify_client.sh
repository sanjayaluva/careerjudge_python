#!/usr/bin/env bash
# Client verification runner — Career Judge.
# Runs the automated tests that PROVE each fixed feature area, grouped and
# labelled by the review-report item they correspond to. Green = that behaviour
# is implemented and locked by a test; anything red is a real regression.
#
# Usage:  bash scripts/verify_client.sh
# Needs:  backend/.venv (pytest). Run from the repo root.
set -uo pipefail
cd "$(dirname "$0")/../backend" || exit 1
PY=".venv/bin/python -m pytest -q --no-header"

run () {  # run "<label>" "<pytest -k expr or path>"
  echo ""
  echo "──────────────────────────────────────────────────────────────"
  echo "▶ $1"
  echo "──────────────────────────────────────────────────────────────"
  eval $PY $2 2>&1 | grep -E "passed|failed|error|PASSED|FAILED" | tail -3
}

echo "CAREER JUDGE — AUTOMATED VERIFICATION"
echo "Each block below runs the real test(s) that prove one review-report item."

run "Report 3 §4 / Report 4 Trainer-9 — Assessment links to a SPECIFIC session" \
    "apps/training/tests/test_training.py -k assessment_links_to_specific_session"
run "Report 5 §3.1 — Questions attach only at the last (leaf) section level" \
    "apps/assessment/tests/test_views.py -k 'non_leaf_section or fifth_level'"
run "Report 3 §3 — Assignment deadline override + multi-file submission" \
    "apps/training/tests/test_training.py -k 'deadline or multiple_report_files'"
run "Report 4 SME-4 / Reviewer-5 — SME→Reviewer same-domain routing" \
    "apps/question_bank/tests/test_reviewer_routing.py"
run "Report 4 Individual-2/13/17 — Pay-for-test gate before start" \
    "apps/assessment/tests/test_views.py -k priced_assessment"
run "User Details.pdf — Send Message / Live Chat (messaging)" \
    "apps/messaging/tests/test_messaging.py"
run "Report 4 (empanelled) — Invoice create/revise/cancel + line items" \
    "apps/invoicing/tests/test_invoicing.py"
run "Reporting — question-level data + chart rendering" \
    "apps/reporting/tests/test_question_level_and_charts.py"
run "Question scoring fix (FITB / type-2a no longer always 0)" \
    "apps/assessment -k 'fitb or fuzzy or scoring' "

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "Full backend suite (everything at once):"
eval $PY 2>&1 | grep -E "passed|failed" | tail -1
echo "NOTE: any 'weasyprint' PDF failures are a missing native library in this"
echo "environment (cairo/pango), not a product defect."
echo "══════════════════════════════════════════════════════════════"
