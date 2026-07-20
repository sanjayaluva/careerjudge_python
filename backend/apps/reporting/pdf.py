"""PDF generation for reports using WeasyPrint.

Renders a GeneratedReport's rendered_data JSON into a downloadable PDF.

The PDF layout is intentionally simple and template-based:
  - Header: report title + candidate name + assessment title + generated date
  - Score summary block (total score, max, percentage, pass/fail)
  - Section breakdown table (per-variable scores)
  - Report-type-specific sections:
    * Descriptive: cutoff table (variable, candidate_score, cutoff, above/below)
    * Typological: top-N type profile + concatenated code
    * Interpretative: band table (variable, score, band, label, description)
    * Group: aggregated stats (candidate_count, avg, pass_rate, distribution)
  - Polar variables (if any)
  - Profiling data (FMI/PMI/VMI if present)
  - Custom narrative sections from ReportSection rows

This is a v1 — the SRS mentions drag-drop layout templates, but for now
we render a clean standard layout that includes all configured data.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def _get_weasyprint_html():
    """Lazy-import WeasyPrint so a missing system library (libgobject,
    libpango, libcairo) doesn't crash the whole app at module load time.

    The import is deferred to the first PDF render request. If the
    native deps are missing, the error is reported on that specific
    request rather than breaking every URL in the app.
    """
    from weasyprint import HTML

    return HTML


def _esc(value: Any) -> str:
    """HTML-escape a value for safe inclusion in the PDF template."""
    if value is None:
        return ""
    s = str(value)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _fmt(value: Any, suffix: str = "") -> str:
    """Format a numeric value for display, returning '—' for None."""
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def render_report_pdf(rendered_data: dict[str, Any]) -> bytes:
    """Render a GeneratedReport.rendered_data dict into a PDF.

    Returns the PDF as bytes. Caller should set Content-Type:
    application/pdf and Content-Disposition headers appropriately.
    """
    html_content = _build_html(rendered_data)
    HTML = _get_weasyprint_html()
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


# ---------------------------------------------------------------------------
# HTML template builder
# ---------------------------------------------------------------------------


def _build_html(data: dict[str, Any]) -> str:
    """Build the full HTML document for the report."""
    report_title = _esc(data.get("report_title", "Report"))
    report_type = _esc(data.get("report_type", ""))
    scope = _esc(data.get("scope", ""))
    assessment_title = _esc(data.get("assessment_title", "—"))
    candidate = data.get("candidate", {}) or {}
    candidate_name = _esc(candidate.get("name") or candidate.get("email") or "—")
    session = data.get("session", {}) or {}
    started_at = _fmt_date(session.get("started_at"))
    completed_at = _fmt_date(session.get("completed_at"))

    # Score summary
    scores = data.get("scores", {}) or {}
    score_summary = data.get("score_summary", {}) or {}

    # Build section blocks
    section_breakdown_html = _build_section_breakdown(data.get("section_breakdown"))
    descriptive_html = _build_descriptive(data.get("descriptive"))
    typological_html = _build_typological(data.get("typological"))
    interpretative_html = _build_interpretative(data.get("interpretative"))
    group_html = _build_group(data.get("group"))
    polar_html = _build_polar(data.get("polar"))
    profiling_html = _build_profiling(data.get("profiling"))
    custom_sections_html = _build_custom_sections(data.get("sections"))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{report_title}</title>
<style>
  @page {{
    size: A4;
    margin: 2cm 1.5cm;
    @bottom-center {{
      content: "Page " counter(page) " of " counter(pages);
      font-size: 9pt;
      color: #64748b;
    }}
  }}
  body {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    color: #1e293b;
    font-size: 10pt;
    line-height: 1.4;
  }}
  h1 {{
    font-size: 20pt;
    color: #0f172a;
    margin: 0 0 4pt 0;
  }}
  h2 {{
    font-size: 13pt;
    color: #0f172a;
    border-bottom: 1pt solid #cbd5e1;
    padding-bottom: 2pt;
    margin: 18pt 0 8pt 0;
  }}
  h3 {{
    font-size: 11pt;
    color: #334155;
    margin: 12pt 0 4pt 0;
  }}
  .meta {{
    color: #64748b;
    font-size: 9pt;
    margin-bottom: 12pt;
  }}
  .meta div {{ margin: 1pt 0; }}
  .score-grid {{
    display: flex;
    gap: 8pt;
    margin: 8pt 0 12pt 0;
  }}
  .score-box {{
    flex: 1;
    border: 0.5pt solid #cbd5e1;
    border-radius: 3pt;
    padding: 6pt 8pt;
    background: #f8fafc;
  }}
  .score-box .label {{
    font-size: 7.5pt;
    text-transform: uppercase;
    color: #64748b;
    letter-spacing: 0.5pt;
  }}
  .score-box .value {{
    font-size: 14pt;
    font-weight: bold;
    color: #0f172a;
    margin-top: 2pt;
  }}
  .pass {{ color: #16a34a; }}
  .fail {{ color: #dc2626; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 6pt 0 10pt 0;
    font-size: 9pt;
  }}
  th {{
    text-align: left;
    background: #f1f5f9;
    padding: 4pt 6pt;
    border-bottom: 0.5pt solid #cbd5e1;
    font-weight: 600;
    color: #334155;
  }}
  td {{
    padding: 4pt 6pt;
    border-bottom: 0.25pt solid #e2e8f0;
  }}
  .badge {{
    display: inline-block;
    padding: 1pt 5pt;
    border-radius: 8pt;
    font-size: 8pt;
    font-weight: 600;
  }}
  .badge-success {{ background: #dcfce7; color: #15803d; }}
  .badge-warning {{ background: #fef3c7; color: #b45309; }}
  .badge-danger  {{ background: #fee2e2; color: #b91c1c; }}
  .narrative {{
    background: #f8fafc;
    border-left: 2pt solid #3b82f6;
    padding: 6pt 10pt;
    margin: 6pt 0;
    font-size: 9pt;
  }}
  .distribution-grid {{
    display: flex;
    gap: 6pt;
    margin: 6pt 0;
  }}
  .dist-box {{
    flex: 1;
    padding: 6pt;
    border-radius: 3pt;
    text-align: center;
  }}
  .dist-box .count {{ font-size: 16pt; font-weight: bold; }}
  .dist-box .label {{ font-size: 7.5pt; }}
  .footer {{
    margin-top: 18pt;
    padding-top: 6pt;
    border-top: 0.5pt solid #cbd5e1;
    color: #64748b;
    font-size: 8pt;
    text-align: center;
  }}
</style>
</head>
<body>
  <h1>{report_title}</h1>
  <div class="meta">
    <div><strong>Candidate:</strong> {candidate_name}</div>
    <div><strong>Assessment:</strong> {assessment_title}</div>
    <div><strong>Report type:</strong> {report_type} &nbsp;|&nbsp; <strong>Scope:</strong> {scope}</div>
    <div><strong>Session started:</strong> {started_at} &nbsp;|&nbsp; <strong>Completed:</strong> {completed_at}</div>
    <div><strong>Generated:</strong> {_fmt_date(datetime.now(UTC).isoformat())}</div>
  </div>

  {_build_score_summary_html(scores, score_summary)}

  {section_breakdown_html}
  {descriptive_html}
  {typological_html}
  {interpretative_html}
  {group_html}
  {polar_html}
  {profiling_html}
  {custom_sections_html}

  <div class="footer">
    Generated by CareerJudge — Confidential candidate report
  </div>
</body>
</html>"""


def _fmt_date(iso_str: Any) -> str:
    """Format an ISO date string for display."""
    if not iso_str:
        return "—"
    try:
        # Handle both '2026-07-20T12:34:56.789' and '2026-07-20'
        s = str(iso_str)
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M")
        return s[:10]
    except (ValueError, TypeError):
        return str(iso_str)


def _build_score_summary_html(scores: dict, score_summary: dict) -> str:
    """Build the score summary box grid."""
    if not scores and not score_summary:
        return ""
    total = score_summary.get("total") if score_summary else scores.get("total_score")
    max_score = score_summary.get("max") if score_summary else scores.get("max_score")
    percentage = score_summary.get("percentage") if score_summary else scores.get("percentage")
    passed = score_summary.get("passed")
    pass_class = "pass" if passed else "fail"
    pass_label = "PASS" if passed else "—" if passed is None else "FAIL"
    return f"""
      <h2>Score Summary</h2>
      <div class="score-grid">
        <div class="score-box">
          <div class="label">Total Score</div>
          <div class="value">{_fmt(total)} / {_fmt(max_score)}</div>
        </div>
        <div class="score-box">
          <div class="label">Percentage</div>
          <div class="value">{_fmt(percentage, "%")}</div>
        </div>
        <div class="score-box">
          <div class="label">Result</div>
          <div class="value {pass_class}">{pass_label}</div>
        </div>
      </div>
    """


def _build_section_breakdown(breakdown: Any) -> str:
    """Build the per-variable section breakdown table."""
    if not breakdown or not isinstance(breakdown, list):
        return ""
    rows = ""
    for s in breakdown:
        rows += (
            f"<tr>"
            f"<td>{_esc(s.get('section_title'))}</td>"
            f"<td>{_fmt(s.get('raw_score'))}</td>"
            f"<td>{_fmt(s.get('max_score'))}</td>"
            f"<td>{_fmt(s.get('percentage'), '%')}</td>"
            f"<td>{_fmt(s.get('converted_score'))} <em>({_esc(s.get('conversion_type', ''))})</em></td>"
            f"</tr>"
        )
    return f"""
      <h2>Section Breakdown</h2>
      <table>
        <thead><tr><th>Variable</th><th>Raw</th><th>Max</th><th>%</th><th>Converted</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    """


def _build_descriptive(descriptive: Any) -> str:
    """Build the descriptive report cutoff table."""
    if not descriptive:
        return ""
    cutoffs = descriptive.get("cutoffs") or []
    if not cutoffs:
        return ""
    rows = ""
    for c in cutoffs:
        is_above = c.get("is_above_cutoff")
        badge_class = "badge-success" if is_above else "badge-danger"
        badge_text = "Above" if is_above else "Below"
        rows += (
            f"<tr>"
            f"<td>{_esc(c.get('variable'))}</td>"
            f"<td>{_fmt(c.get('candidate_score'), '%')}</td>"
            f"<td>{_fmt(c.get('cutoff_score'), '%')}</td>"
            f"<td><span class='badge {badge_class}'>{badge_text}</span></td>"
            f"<td>{_esc(c.get('description'))}</td>"
            f"</tr>"
        )
    return f"""
      <h2>Cutoff Comparison</h2>
      <table>
        <thead><tr><th>Variable</th><th>Score</th><th>Cutoff</th><th>Result</th><th>Description</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    """


def _build_typological(typological: Any) -> str:
    """Build the typological report — type profile + top variables."""
    if not typological:
        return ""
    type_profile = typological.get("type_profile", "")
    top_vars = typological.get("top_variables") or []
    rows = ""
    for v in top_vars:
        rows += (
            f"<tr>"
            f"<td>{_esc(v.get('variable'))}</td>"
            f"<td><strong>{_esc(v.get('code'))}</strong></td>"
            f"<td>{_fmt(v.get('score'), '%')}</td>"
            f"</tr>"
        )
    return f"""
      <h2>Personality / Intellectual Type</h2>
      <p><strong>Type Profile:</strong> <span style="font-size:14pt;font-weight:bold;color:#1e40af;">{_esc(type_profile)}</span></p>
      <table>
        <thead><tr><th>Top Variable</th><th>Code</th><th>Score</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    """


def _build_interpretative(interpretative: Any) -> str:
    """Build the interpretative report — band table."""
    if not interpretative:
        return ""
    bands = interpretative.get("bands") or []
    if not bands:
        return ""
    rows = ""
    for b in bands:
        rows += (
            f"<tr>"
            f"<td>{_esc(b.get('variable'))}</td>"
            f"<td>{_fmt(b.get('candidate_score'), '%')}</td>"
            f"<td>{_esc(b.get('band_label'))}</td>"
            f"<td>{_esc(b.get('range'))}</td>"
            f"<td>{_esc(b.get('description'))}</td>"
            f"</tr>"
        )
    return f"""
      <h2>Band Interpretation</h2>
      <table>
        <thead><tr><th>Variable</th><th>Score</th><th>Band</th><th>Range</th><th>Description</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    """


def _build_group(group: Any) -> str:
    """Build the group report — aggregated stats."""
    if not group:
        return ""
    if "candidate_count" not in group:
        # Single-session placeholder path
        return ""
    distribution = group.get("distribution", {}) or {}
    section_averages = group.get("section_averages") or []
    candidates = group.get("candidates") or []

    dist_html = ""
    colors = {
        "fail (0-40)": "#fee2e2",
        "below_avg (40-60)": "#ffedd5",
        "average (60-80)": "#fef3c7",
        "above_avg (80-100)": "#dcfce7",
    }
    for key, color in colors.items():
        dist_html += (
            f"<div class='dist-box' style='background:{color};'>"
            f"<div class='count'>{distribution.get(key, 0)}</div>"
            f"<div class='label'>{key.replace('_', ' ').title()}</div>"
            f"</div>"
        )

    section_rows = ""
    for s in section_averages:
        section_rows += (
            f"<tr>"
            f"<td>{_esc(s.get('section_title'))}</td>"
            f"<td>{_fmt(s.get('average_percentage'), '%')}</td>"
            f"<td>{_fmt(s.get('min_percentage'), '%')}</td>"
            f"<td>{_fmt(s.get('max_percentage'), '%')}</td>"
            f"<td>{_fmt(s.get('candidate_count'))}</td>"
            f"</tr>"
        )

    cand_rows = ""
    for c in candidates:
        cand_rows += (
            f"<tr>"
            f"<td>{_esc(c.get('name'))}</td>"
            f"<td>{_esc(c.get('email'))}</td>"
            f"<td>{_fmt(c.get('total_score'))}</td>"
            f"<td>{_fmt(c.get('percentage'), '%')}</td>"
            f"</tr>"
        )

    return f"""
      <h2>Group Report — {len(candidates)} Candidates</h2>
      <div class="score-grid">
        <div class="score-box"><div class="label">Avg Score</div><div class="value">{_fmt(group.get('average_score'))}</div></div>
        <div class="score-box"><div class="label">Avg %</div><div class="value">{_fmt(group.get('average_percentage'), '%')}</div></div>
        <div class="score-box"><div class="label">Pass Rate</div><div class="value pass">{_fmt(group.get('pass_rate'), '%')}</div></div>
        <div class="score-box"><div class="label">Min / Max %</div><div class="value">{_fmt(group.get('min_percentage'), '%')} / {_fmt(group.get('max_percentage'), '%')}</div></div>
      </div>
      <h3>Distribution</h3>
      <div class="distribution-grid">{dist_html}</div>
      {f"<h3>Section Averages</h3><table><thead><tr><th>Section</th><th>Avg</th><th>Min</th><th>Max</th><th>N</th></tr></thead><tbody>{section_rows}</tbody></table>" if section_rows else ""}
      {f"<h3>Candidates</h3><table><thead><tr><th>Name</th><th>Email</th><th>Score</th><th>%</th></tr></thead><tbody>{cand_rows}</tbody></table>" if cand_rows else ""}
    """


def _build_polar(polar: Any) -> str:
    """Build polar variable section."""
    if not polar:
        return ""
    polar_vars = polar.get("polar_variables") or []
    if not polar_vars:
        return ""
    rows = ""
    for p in polar_vars:
        rows += (
            f"<tr>"
            f"<td>{_esc(p.get('primary_variable'))}</td>"
            f"<td>{_fmt(p.get('primary_score'), '%')}</td>"
            f"<td>{_esc(p.get('opposite_variable'))}</td>"
            f"<td>{_fmt(p.get('opposite_score'), '%')}</td>"
            f"</tr>"
        )
    return f"""
      <h2>Polar Variables</h2>
      <table>
        <thead><tr><th>Primary</th><th>Score</th><th>Opposite</th><th>Score</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    """


def _build_profiling(profiling: Any) -> str:
    """Build profiling section (FMI/PMI/VMI)."""
    if not profiling:
        return ""
    parts = []
    if "raw_summary" in profiling:
        rs = profiling["raw_summary"]
        parts.append(
            f"<h3>Raw Summary</h3>"
            f"<p>Total: {_fmt(rs.get('total_score'))} / {_fmt(rs.get('max_score'))} "
            f"({_fmt(rs.get('percentage'), '%')})</p>"
        )
    if "fmi" in profiling:
        fmi_list = profiling["fmi"] or []
        if fmi_list:
            rows = ""
            for f in fmi_list:
                fmi = f.get("final_match_index")
                badge_class = (
                    "badge-success"
                    if fmi is not None and fmi >= 75
                    else "badge-warning" if fmi is not None and fmi >= 50 else "badge-danger"
                )
                rows += (
                    f"<tr>"
                    f"<td>{_esc(f.get('career_title'))}</td>"
                    f"<td><span class='badge {badge_class}'>{_fmt(fmi)}</span></td>"
                    f"<td>{_fmt(f.get('variable_mapping_index'))}</td>"
                    f"</tr>"
                )
            parts.append(
                f"<h3>Final Match Index (FMI)</h3>"
                f"<table><thead><tr><th>Career</th><th>FMI</th><th>VMI</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>"
            )
    if "vmi" in profiling:
        vmi_list = profiling["vmi"] or []
        if vmi_list:
            parts.append("<h3>Variable Match Index (VMI)</h3>")
            for v in vmi_list:
                parts.append(f"<p><strong>{_esc(v.get('career_title'))}:</strong></p>")
                details = v.get("variable_details") or []
                if details:
                    rows = ""
                    for d in details:
                        rows += (
                            f"<tr>"
                            f"<td>{_esc(d.get('variable'))}</td>"
                            f"<td>{_esc(d.get('assessment'))}</td>"
                            f"<td>{_esc(d.get('criterion_band'))}</td>"
                            f"<td>{_esc(d.get('candidate_band'))}</td>"
                            f"<td>{_fmt(d.get('vmi'))}</td>"
                            f"</tr>"
                        )
                    parts.append(
                        f"<table><thead><tr><th>Variable</th><th>Assessment</th>"
                        f"<th>Criterion</th><th>Candidate</th><th>VMI</th></tr></thead>"
                        f"<tbody>{rows}</tbody></table>"
                    )
    if not parts:
        return ""
    return "<h2>Profiling Results</h2>" + "".join(parts)


def _build_custom_sections(sections: Any) -> str:
    """Build custom narrative sections from ReportSection rows."""
    if not sections or not isinstance(sections, list):
        return ""
    parts = []
    for s in sections:
        if not s.get("is_visible", True):
            continue
        title = _esc(s.get("title"))
        content = _esc(s.get("content"))
        stype = _esc(s.get("section_type"))
        if not content and not title:
            continue
        parts.append(
            f"<div class='narrative'>"
            f"<div style='font-size:8pt;color:#64748b;text-transform:uppercase;'>{stype}</div>"
            f"<strong>{title}</strong>"
            f"<p style='margin:4pt 0 0 0;'>{content}</p>"
            f"</div>"
        )
    if not parts:
        return ""
    return "<h2>Additional Sections</h2>" + "".join(parts)
