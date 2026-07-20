"""Report generation engine.

Builds the rendered_data JSON for a GeneratedReport based on:
  - Report type (descriptive, typological, interpretative, group)
  - Report scope (general, profiling)
  - Data input level (Level0-4, Question)
  - Statistical conversion (percentage, percentile, STEN, STENINE)
  - Cutoffs, bands, typological codes, polar variables
  - Report sections (narratives, charts, etc.)

Per SRS 04_general_report_generation.json + 06_profiling_report_generation.json
"""

from typing import Any

from apps.assessment.models import AssessmentSession


def generate_report_data(report, session: AssessmentSession) -> dict[str, Any]:
    """Generate the full rendered data for a report.

    Args:
        report: The Report model instance with config
        session: The completed AssessmentSession

    Returns:
        dict with all computed data for display
    """
    data: dict[str, Any] = {
        "report_title": report.title,
        "report_type": report.report_type,
        "scope": report.scope,
        "data_input_level": report.data_input_level,
        "stat_conversion": report.stat_conversion,
        "assessment_title": session.assessment.title,
        "candidate": {
            "id": session.candidate.id,
            "name": session.candidate.full_name,
            "email": session.candidate.email,
        },
        "session": {
            "id": session.id,
            "started_at": session.started_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        },
        "scores": {
            "total_score": session.total_score,
            "max_score": session.max_score,
            "percentage": session.percentage,
        },
    }

    # --- Score summary ---
    if report.include_score_summary:
        data["score_summary"] = {
            "total": session.total_score,
            "max": session.max_score,
            "percentage": session.percentage,
            "passed": (session.percentage or 0) >= 40,
        }

    # --- Section breakdown (filtered by data_input_level) ---
    if report.include_section_breakdown:
        data["section_breakdown"] = _build_section_breakdown(report, session)

    # --- Report-type-specific logic ---
    if report.report_type == "descriptive":
        data["descriptive"] = _build_descriptive(report, session)
    elif report.report_type == "typological":
        data["typological"] = _build_typological(report, session)
    elif report.report_type == "interpretative":
        data["interpretative"] = _build_interpretative(report, session)
    elif report.report_type == "group":
        data["group"] = _build_group(report, session)

    # --- Polar variable computation (SRS §4) ---
    if report.polar_variables.exists():
        data["polar"] = _build_polar(report, session)

    # --- Report sections (narratives, charts, etc.) ---
    sections = []
    for rs in report.sections.filter(is_visible=True).order_by("order"):
        sections.append(
            {
                "type": rs.section_type,
                "title": rs.title,
                "content": rs.content,
                "table_graph_config": rs.table_graph_config,
                "order": rs.order,
            }
        )
    data["sections"] = sections

    # --- Profiling report data (FMI, PMI, VMI) ---
    if report.scope == "profiling" and report.profiling_solution:
        data["profiling"] = _build_profiling(report, session)

    return data


def _convert_score(raw: float, max_score: float, conversion: str) -> float:
    """Convert a raw score to the configured statistical conversion type."""
    if max_score <= 0:
        return 0.0
    percentage = (raw / max_score) * 100
    if conversion == "percentage":
        return round(percentage, 2)
    elif conversion == "percentile":
        # Simplified: would need norming data for accurate percentile
        return round(percentage, 2)
    elif conversion == "sten":
        # STEN: 1-10 scale, mean=5.5, SD=2
        return round(max(1, min(10, (percentage / 10) + 0.5)), 1)
    elif conversion == "stenine":
        # STENINE: 1-9 scale, mean=5, SD=2
        return round(max(1, min(9, (percentage / 100) * 8 + 1)), 1)
    return round(percentage, 2)


def _filter_sections_by_level(sections, level: str):
    """Filter section scores by the configured data input level."""
    level_map = {
        "level0": None,  # Entire assessment — no filter
        "level1": 1,
        "level2": 2,
        "level3": 3,
        "level4": 4,
    }
    if level == "question":
        return []  # Question-level handled separately
    target_level = level_map.get(level)
    if target_level is None:
        return sections
    return [s for s in sections if s.section.level == target_level]


def _build_section_breakdown(report, session: AssessmentSession) -> list[dict]:
    """Build per-variable score breakdown, filtered by data input level."""
    all_scores = list(session.section_scores.select_related("section").all())
    filtered = _filter_sections_by_level(all_scores, report.data_input_level)

    result = []
    for ss in filtered:
        converted = _convert_score(ss.raw_score, ss.max_score, report.stat_conversion)
        result.append(
            {
                "section_id": ss.section_id,
                "section_title": ss.section.title,
                "level": ss.section.level,
                "raw_score": ss.raw_score,
                "max_score": ss.max_score,
                "percentage": ss.percentage,
                "converted_score": converted,
                "conversion_type": report.stat_conversion,
            }
        )
    return result


def _build_descriptive(report, session: AssessmentSession) -> dict:
    """Build descriptive report data: cutoff comparisons per variable.

    Per SRS §3.1: scores are presented in tables/graphs and explained
    against a cut-off.
    """
    cutoff_data = []
    for cutoff in report.cutoffs.select_related("section").all():
        # Find the candidate's score for this section
        ss = session.section_scores.filter(section=cutoff.section).first()
        candidate_score = ss.percentage if ss else 0
        is_above = candidate_score >= cutoff.cutoff_score

        cutoff_data.append(
            {
                "variable": cutoff.section.title,
                "candidate_score": round(candidate_score, 2),
                "cutoff_score": cutoff.cutoff_score,
                "cutoff_label": cutoff.cutoff_label,
                "is_above_cutoff": is_above,
                "description": cutoff.above_description if is_above else cutoff.below_description,
            }
        )

    return {"cutoffs": cutoff_data}


def _build_typological(report, session: AssessmentSession) -> dict:
    """Build typological report data: top-N type profile.

    Per SRS §3.2: summary scores ordered descending, top N variables'
    codes concatenated to form the type profile.
    """
    codes = list(report.typological_codes.select_related("section").all())
    if not codes:
        return {"type_profile": "", "top_variables": []}

    top_n = codes[0].top_n if codes else 3

    # Get candidate's scores for the coded variables
    scored = []
    for tc in codes:
        ss = session.section_scores.filter(section=tc.section).first()
        score = ss.percentage if ss else 0
        scored.append({"variable": tc.section.title, "code": tc.code, "score": score})

    # Sort by score descending, take top N
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:top_n]

    # Concatenate codes to form the type profile
    type_profile = "".join(item["code"] for item in top)

    return {"type_profile": type_profile, "top_variables": top}


def _build_interpretative(report, session: AssessmentSession) -> dict:
    """Build interpretative report data: band-based interpretation per variable.

    Per SRS §3.3: scores analysed against score ranges defined by bands.
    """
    band_data = []
    for band in report.bands.select_related("section").all():
        # Find the candidate's score for this section
        ss = session.section_scores.filter(section=band.section).first()
        candidate_score = ss.percentage if ss else 0

        if band.contains_score(candidate_score):
            band_data.append(
                {
                    "variable": band.section.title,
                    "candidate_score": round(candidate_score, 2),
                    "band_number": band.band_number,
                    "band_label": band.band_label,
                    "range": f"{band.range_min}-{band.range_max}",
                    "description": band.description,
                    "colour_code": band.colour_code,
                }
            )

    return {"bands": band_data}


def _build_group(report, session: AssessmentSession) -> dict:
    """Build group report data: placeholder for corporate group reports.

    Per SRS: Group reports are used by corporate managers to view their
    employees' performance. Requires multiple sessions aggregated.
    For now, returns the individual session's data — group aggregation
    would need a separate endpoint that takes multiple session IDs.
    """
    return {
        "note": "Group report: individual session data shown. Group aggregation requires multiple sessions.",
        "session_data": {
            "candidate": session.candidate.full_name,
            "total_score": session.total_score,
            "percentage": session.percentage,
        },
    }


def _build_polar(report, session: AssessmentSession) -> dict:
    """Build polar variable data: opposite variable computation.

    Per SRS §4: Opposite = Max Score (100) - Summary Score
    """
    polar_data = []
    for pv in report.polar_variables.select_related("section").all():
        ss = session.section_scores.filter(section=pv.section).first()
        primary_score = ss.percentage if ss else 0
        opposite_score = pv.compute_opposite_score(primary_score)

        polar_data.append(
            {
                "primary_variable": pv.section.title,
                "primary_score": round(primary_score, 2),
                "opposite_variable": pv.opposite_name,
                "opposite_score": opposite_score,
            }
        )

    return {"polar_variables": polar_data}


def _build_profiling(report, session: AssessmentSession) -> dict:
    """Build profiling report data: FMI, PMI, VMI from match indices.

    Per SRS 06_profiling_report_generation.json:
    - FMI: Final Match Index for all criteria
    - PMI: Profile Match Index per assessment per criteria
    - VMI: Variable Match Index per variable per criteria
    """
    from apps.career_profiling.models import MatchIndex

    solution = report.profiling_solution
    match_indices = MatchIndex.objects.filter(solution=solution, candidate=session.candidate).all()

    profiling_data: dict[str, Any] = {}

    if report.include_raw_summary:
        profiling_data["raw_summary"] = {
            "total_score": session.total_score,
            "max_score": session.max_score,
            "percentage": session.percentage,
        }

    if report.include_fmi:
        fmi_data = []
        for mi in match_indices:
            fmi_data.append(
                {
                    "career_title": mi.career_title,
                    "final_match_index": mi.final_match_index,
                    "variable_mapping_index": mi.variable_mapping_index,
                }
            )
        profiling_data["fmi"] = fmi_data

    if report.include_pmi:
        # PMI would be computed per assessment — placeholder
        profiling_data["pmi"] = {
            "note": "PMI computation requires multi-assessment match indices.",
            "match_indices": [
                {"career": mi.career_title, "fmi": mi.final_match_index} for mi in match_indices
            ],
        }

    if report.include_vmi:
        # VMI from variable_details JSON
        vmi_data = []
        for mi in match_indices:
            if mi.variable_details:
                vmi_data.append(
                    {
                        "career_title": mi.career_title,
                        "variable_details": mi.variable_details,
                    }
                )
        profiling_data["vmi"] = vmi_data

    return profiling_data
