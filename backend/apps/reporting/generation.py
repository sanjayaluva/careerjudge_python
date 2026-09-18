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

import statistics
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

    # --- Norm context (H4): drives statistical conversions + thresholds ---
    norm = _build_norm_context(report, session)
    data["stat_conversion_norm"] = {
        "population_size": len(norm.population),
        "mean": round(norm.mean, 4),
        "sd": round(norm.sd, 4),
        "fell_back": norm.fell_back,
    }

    # --- Section breakdown (filtered by data_input_level) ---
    if report.include_section_breakdown:
        data["section_breakdown"] = _build_section_breakdown(report, session, norm)

    # --- Question-level breakdown (SRS 04 §2.3): when the report's data input
    #     level is "question", the section breakdown is empty by design (scores
    #     are per-question, not per-variable). REP-6: populate per-question
    #     rows from the candidate's QuestionAttempts so a question-level report
    #     returns data instead of an empty section.
    if report.data_input_level == "question":
        data["question_breakdown"] = _build_question_breakdown(report, session, norm)

    # --- Report-type-specific logic ---
    if report.report_type == "descriptive":
        data["descriptive"] = _build_descriptive(report, session, norm)
    elif report.report_type == "typological":
        data["typological"] = _build_typological(report, session, norm)
    elif report.report_type == "interpretative":
        data["interpretative"] = _build_interpretative(report, session, norm)
    elif report.report_type == "group":
        data["group"] = _build_group(report, session)

    # --- Polar variable computation (SRS §4) ---
    if report.polar_variables.exists():
        data["polar"] = _build_polar(report, session)

    # --- Report sections (narratives, charts, description/image, table/graph
    #     layout — SRS §2.1.2, §3.1.2/§3.2.2/§3.3.2, §3_layout) ---
    section_breakdown_for_layout = data.get("section_breakdown")
    if section_breakdown_for_layout is None:
        section_breakdown_for_layout = _build_section_breakdown(report, session, norm)
    section_bands_by_id = _section_bands_by_id(report)

    sections = []
    for rs in report.sections.filter(is_visible=True).order_by("order"):
        entry: dict[str, Any] = {
            "type": rs.section_type,
            "title": rs.title,
            "content": rs.content,
            "description": rs.description,
            "image_url": rs.image.url if rs.image else None,
            "image_data_uri": _image_data_uri(rs.image),
            "table_graph_config": rs.table_graph_config,
            "order": rs.order,
        }
        layout = (rs.table_graph_config or {}).get("layout") if rs.table_graph_config else None
        if layout == "table":
            # SRS §3.1.2/§3.2.2/§3.3.2 Table/Graph layout — Table implemented
            # end-to-end: section scores -> table rows (banded where the
            # report defines section-target bands) -> PDF table.
            entry["table"] = _build_layout_table(
                section_breakdown_for_layout, section_bands_by_id, rs.table_graph_config
            )
        elif layout == "graph":
            # SRS §3.1.2/§3.2.2/§3.3.2 Graph layout (REP-1): the same banded
            # section scores as the Table layout, shaped as bar-chart data and
            # rendered as an inline SVG bar chart in the PDF/preview.
            entry["graph"] = _build_layout_graph(
                section_breakdown_for_layout, section_bands_by_id, rs.table_graph_config
            )
        sections.append(entry)
    data["sections"] = sections

    # --- Profiling report data (FMI, PMI, VMI) ---
    if report.scope == "profiling" and report.profiling_solution:
        data["profiling"] = _build_profiling(report, session)

    return data


def _compute_norm(population: list[float]) -> tuple[float, float]:
    """Compute a norm (mean, population SD) from a list of scores.

    Returns (mean, sd). When fewer than two data points are available the SD
    is 0.0 (callers treat sd==0 as "cannot norm" and fall back gracefully).
    """
    values = [float(v) for v in population if v is not None]
    if not values:
        return (0.0, 0.0)
    if len(values) < 2:
        return (values[0], 0.0)
    return (statistics.fmean(values), statistics.pstdev(values))


def _percentile_rank(value: float, population: list[float]) -> float:
    """Percentile rank (0..100) of ``value`` within ``population``.

    Uses the mid-rank convention: (count below + 0.5 * count equal) / n * 100,
    so a value equal to the population median maps near 50.
    """
    values = [float(v) for v in population if v is not None]
    if not values:
        return 0.0
    below = sum(1 for v in values if v < value)
    equal = sum(1 for v in values if v == value)
    return round((below + 0.5 * equal) / len(values) * 100, 2)


class _NormContext:
    """Norm statistics for a report, driving statistical conversions (H4).

    The norm population is the set of section-score percentages available for
    the report (for a single-session general report: every SectionScore in the
    session). ``mean``/``sd`` feed STEN/STENINE z-scores; ``population`` feeds
    percentile ranks. ``fell_back`` records whether SD==0 forced a mid-scale
    fallback for STEN/STENINE.
    """

    def __init__(self, population: list[float]):
        self.population = [float(v) for v in population if v is not None]
        self.mean, self.sd = _compute_norm(self.population)
        self.fell_back = self.sd == 0

    def convert(self, value: float | None, conversion: str) -> float:
        return _convert_score(value or 0.0, conversion, self)


def _build_norm_context(report, session: AssessmentSession) -> _NormContext:
    """Build the norm population for a report from the session's section scores.

    Norm-population source (H4 assumption): all SectionScore percentages for
    the session. This is the population of section scores "available for the
    report" for a single-session general report, and it guarantees every
    cutoff/band section is represented in the percentile population.
    """
    percentages = list(session.section_scores.values_list("percentage", flat=True))
    return _NormContext(percentages)


def _convert_score(value: float, conversion: str, norm: "_NormContext | None" = None) -> float:
    """Convert a percentage ``value`` to the configured statistical conversion.

    ``value`` is a percentage in 0..100. Norm-based conversions (percentile,
    STEN, STENINE) require a ``_NormContext`` computed over the report's
    population; when it is missing or degenerate the function falls back
    gracefully (percentile -> the percentage; STEN/STENINE -> mid-scale).

      - percentage : value unchanged (rounded to 2dp)
      - percentile : candidate's percentile rank in the population (0..100)
      - sten       : round(5.5 + 2z) clamped to 1..10 (integer)
      - stenine    : round(5 + 2z)   clamped to 1..9  (integer)

    where z = (value - mean) / sd over the norm population.
    """
    if conversion == "percentage":
        return round(value, 2)

    if conversion == "percentile":
        if norm is None or not norm.population:
            return round(value, 2)
        return _percentile_rank(value, norm.population)

    if conversion in ("sten", "stenine"):
        # degenerate population (no/zero variance) -> mid-scale
        z = (value - norm.mean) / norm.sd if norm is not None and norm.sd > 0 else 0.0
        if conversion == "sten":
            return int(max(1, min(10, round(5.5 + 2 * z))))
        return int(max(1, min(9, round(5 + 2 * z))))

    return round(value, 2)


def _raw_convert_score(raw: float, max_score: float, conversion: str) -> float:
    """Convert a raw/max score pair (percentage conversions only).

    Retained for callers that only need a percentage-scale conversion without
    a norm population.
    """
    if max_score <= 0:
        return 0.0
    return _convert_score((raw / max_score) * 100, conversion, None)


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


def _build_section_breakdown(
    report, session: AssessmentSession, norm: "_NormContext | None" = None
) -> list[dict]:
    """Build per-variable score breakdown, filtered by data input level."""
    if norm is None:
        norm = _build_norm_context(report, session)
    all_scores = list(session.section_scores.select_related("section").all())
    filtered = _filter_sections_by_level(all_scores, report.data_input_level)

    result = []
    for ss in filtered:
        converted = norm.convert(ss.percentage, report.stat_conversion)
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


def _build_question_breakdown(
    report, session: AssessmentSession, norm: "_NormContext | None" = None
) -> list[dict]:
    """Build a per-question score breakdown (SRS 04 §2.3, REP-6).

    Question-level reports interpret each answered question in its own right.
    Each attempt's score/max_score is converted through the same statistical
    conversion + norm as section scores, so question-level and variable-level
    reports read consistently.
    """
    if norm is None:
        norm = _build_norm_context(report, session)
    attempts = (
        session.question_attempts.select_related("question", "section")
        .order_by("section__order", "question__created_at", "sub_question_index")
    )
    result = []
    for qa in attempts:
        max_score = qa.max_score or 0
        raw_score = qa.score or 0
        percentage = round((raw_score / max_score) * 100, 2) if max_score > 0 else 0.0
        converted = norm.convert(percentage, report.stat_conversion)
        q = qa.question
        label = q.question_title or (q.question_text_1 or "")[:80] or f"Question {q.id}"
        result.append(
            {
                "question_id": qa.question_id,
                "question_label": label,
                "question_id_label": q.question_id_label,
                "section_title": qa.section.title if qa.section else None,
                "sub_question_index": qa.sub_question_index,
                "status": qa.status,
                "raw_score": raw_score,
                "max_score": max_score,
                "percentage": percentage,
                "converted_score": converted,
                "conversion_type": report.stat_conversion,
            }
        )
    return result


def _build_descriptive(
    report, session: AssessmentSession, norm: "_NormContext | None" = None
) -> dict:
    """Build descriptive report data: cutoff comparisons per variable.

    Per SRS §3.1: scores are presented in tables/graphs and explained
    against a cut-off. The candidate's score is expressed in the report's
    selected statistical conversion (H4), and the cutoff (defined by the
    psychometrician in that same scale) is compared against it.
    """
    if norm is None:
        norm = _build_norm_context(report, session)
    cutoff_data = []
    for cutoff in report.cutoffs.select_related("section").all():
        # Find the candidate's score for this section, converted to the
        # selected scale so the cutoff bites on the same units the user chose.
        ss = session.section_scores.filter(section=cutoff.section).first()
        candidate_score = norm.convert(ss.percentage if ss else 0, report.stat_conversion)
        is_above = candidate_score >= cutoff.cutoff_score

        cutoff_data.append(
            {
                "variable": cutoff.section.title,
                "candidate_score": round(candidate_score, 2),
                "cutoff_score": cutoff.cutoff_score,
                "cutoff_label": cutoff.cutoff_label,
                "conversion_type": report.stat_conversion,
                "is_above_cutoff": is_above,
                "description": cutoff.above_description if is_above else cutoff.below_description,
            }
        )

    return {"cutoffs": cutoff_data}


def _build_typological(
    report, session: AssessmentSession, norm: "_NormContext | None" = None
) -> dict:
    """Build typological report data: top-N type profile.

    Per SRS §3.2: summary scores ordered descending, top N variables'
    codes concatenated to form the type profile. Ordering uses the report's
    selected statistical conversion (H4) so the "top" variables are ranked on
    the same scale the user chose.

    Per SRS §3.2.1 'System shows entry fields where user can define bands and
    their description for each specified variable' / 'applies band details':
    each top-scoring variable's (converted) score is matched against the
    report's target_type='section' ``ReportBand`` rows for that variable, so
    the type profile carries a band label/description alongside its code —
    reusing the same ReportBand + target_type machinery as the interpretative
    and profiling builders (H6).
    """
    if norm is None:
        norm = _build_norm_context(report, session)
    codes = list(report.typological_codes.select_related("section").all())
    if not codes:
        return {"type_profile": "", "top_variables": []}

    top_n = codes[0].top_n if codes else 3
    section_bands = _section_bands_by_id(report)

    # Get candidate's scores for the coded variables (converted to the scale)
    scored = []
    for tc in codes:
        ss = session.section_scores.filter(section=tc.section).first()
        score = norm.convert(ss.percentage if ss else 0, report.stat_conversion)
        band = _match_band(section_bands.get(tc.section_id, []), score)
        scored.append({"variable": tc.section.title, "code": tc.code, "score": score, "band": band})

    # Sort by (converted) score descending, take top N
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:top_n]

    # Concatenate codes to form the type profile
    type_profile = "".join(item["code"] for item in top)

    return {"type_profile": type_profile, "top_variables": top}


def _build_interpretative(
    report, session: AssessmentSession, norm: "_NormContext | None" = None
) -> dict:
    """Build interpretative report data: band-based interpretation per variable.

    Per SRS §3.3: scores analysed against score ranges defined by bands. The
    candidate's score is expressed in the report's selected statistical
    conversion (H4), and each band bites on that converted value.

    H6: bands carry a ``target_type``. In a general interpretative report the
    relevant targets are ``section`` (default — the converted section score)
    and ``raw_summary`` (the whole-assessment percentage). FMI/PMI/VMI targets
    require profiling context and are resolved in ``_build_profiling`` instead.
    """
    if norm is None:
        norm = _build_norm_context(report, session)
    band_data = []
    for band in report.bands.select_related("section").all():
        target = band.target_type or "section"
        if target == "raw_summary":
            candidate_score = round(session.percentage or 0, 2)
            variable = "Raw Summary"
        elif target == "section":
            if band.section is None:
                continue
            ss = session.section_scores.filter(section=band.section).first()
            candidate_score = norm.convert(ss.percentage if ss else 0, report.stat_conversion)
            variable = band.section.title
        else:
            # fmi / pmi / vmi bands are profiling-only; not applicable here.
            continue

        if band.contains_score(candidate_score):
            band_data.append(
                {
                    "variable": variable,
                    "target_type": target,
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
    """Build group report data for a single session (legacy path).

    Per SRS: Group reports aggregate multiple employees' sessions. The single-
    session path here is kept for backwards compatibility with the existing
    /generate endpoint, but the real group aggregation lives in
    generate_group_report_data() and is invoked via the /generate-group
    endpoint with a list of session IDs.
    """
    return {
        "note": (
            "Single-session group report. Use POST /reports/<id>/generate-group/ "
            "with a list of session_ids for full group aggregation."
        ),
        "session_data": {
            "candidate": session.candidate.full_name,
            "total_score": session.total_score,
            "percentage": session.percentage,
        },
    }


def generate_group_report_data(report, sessions: list[AssessmentSession]) -> dict[str, Any]:
    """Generate a group report aggregating multiple completed sessions.

    Per SRS 04 group report: corporate managers view their employees'
    performance on the assessment. Aggregates:

      - candidate_count: how many sessions are in the group
      - average_score / average_percentage: mean across sessions
      - min/max score: best and worst performers
      - pass_rate: share of sessions whose percentage >= pass_threshold
        (defaults to 40, matching the descriptive-report convention)
      - section_averages: per-section mean percentage across the group
      - distribution: count of sessions in each percentage band
        (0-40 fail, 40-60 below-avg, 60-80 avg, 80-100 above-avg)

    Args:
        report: The Report instance (must be report_type='group').
        sessions: List of completed AssessmentSession instances to aggregate.

    Returns:
        dict with the aggregated group data.
    """
    if not sessions:
        return {
            "report_title": report.title,
            "candidate_count": 0,
            "note": "No sessions provided for group report.",
        }

    percentages = [s.percentage or 0 for s in sessions]
    total_scores = [s.total_score or 0 for s in sessions]
    n = len(sessions)
    avg_pct = sum(percentages) / n
    pass_threshold = 40.0
    pass_count = sum(1 for p in percentages if p >= pass_threshold)

    # Per-section averages across the group
    section_averages: list[dict[str, Any]] = []
    first_session = sessions[0]
    section_ids = list(first_session.section_scores.values_list("section_id", flat=True))
    for section_id in section_ids:
        scores_for_section: list[float] = []
        section_title: str | None = None
        for s in sessions:
            ss = s.section_scores.filter(section_id=section_id).first()
            if ss is not None:
                scores_for_section.append(ss.percentage or 0)
                if section_title is None:
                    section_title = ss.section.title
        if scores_for_section:
            section_averages.append(
                {
                    "section_id": section_id,
                    "section_title": section_title,
                    "average_percentage": round(
                        sum(scores_for_section) / len(scores_for_section), 2
                    ),
                    "min_percentage": round(min(scores_for_section), 2),
                    "max_percentage": round(max(scores_for_section), 2),
                    "candidate_count": len(scores_for_section),
                }
            )

    # Distribution buckets
    distribution = {
        "fail (0-40)": sum(1 for p in percentages if p < 40),
        "below_avg (40-60)": sum(1 for p in percentages if 40 <= p < 60),
        "average (60-80)": sum(1 for p in percentages if 60 <= p < 80),
        "above_avg (80-100)": sum(1 for p in percentages if p >= 80),
    }

    return {
        "report_title": report.title,
        "report_type": "group",
        "assessment_title": first_session.assessment.title,
        "candidate_count": n,
        "average_score": round(sum(total_scores) / n, 2),
        "average_percentage": round(avg_pct, 2),
        "min_score": round(min(total_scores), 2),
        "max_score": round(max(total_scores), 2),
        "min_percentage": round(min(percentages), 2),
        "max_percentage": round(max(percentages), 2),
        "pass_threshold": pass_threshold,
        "pass_rate": round((pass_count / n) * 100, 2) if n else 0.0,
        "pass_count": pass_count,
        "section_averages": section_averages,
        "distribution": distribution,
        "candidates": [
            {
                "id": s.candidate_id,
                "name": s.candidate.full_name,
                "email": s.candidate.email,
                "total_score": s.total_score,
                "percentage": s.percentage,
                "session_id": s.id,
            }
            for s in sessions
        ],
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

    # H6: group the report's bands by target_type so each profiling data
    # input can be interpreted against the right band set.
    bands_by_target = _bands_by_target(report)

    if report.include_raw_summary:
        rs_band = _match_band(bands_by_target.get("raw_summary", []), session.percentage or 0)
        profiling_data["raw_summary"] = {
            "total_score": session.total_score,
            "max_score": session.max_score,
            "percentage": session.percentage,
            "band": rs_band,
        }

    if report.include_fmi:
        fmi_bands = bands_by_target.get("fmi", [])
        fmi_data = []
        for mi in match_indices:
            fmi_data.append(
                {
                    "career_stream": mi.career_stream,
                    "career_title": mi.career_title,
                    "final_match_index": mi.final_match_index,
                    "variable_mapping_index": mi.variable_mapping_index,
                    "band": _match_band(fmi_bands, mi.final_match_index),
                }
            )
        profiling_data["fmi"] = fmi_data

    if report.include_pmi:
        profiling_data["pmi"] = _build_pmi(report, match_indices, bands_by_target.get("pmi", []))

    if report.include_vmi:
        # VMI from variable_details JSON
        vmi_bands = bands_by_target.get("vmi", [])
        vmi_data = []
        for mi in match_indices:
            if mi.variable_details:
                vmi_data.append(
                    {
                        "career_title": mi.career_title,
                        "variable_details": mi.variable_details,
                        "variable_mapping_index": mi.variable_mapping_index,
                        "band": _match_band(vmi_bands, mi.variable_mapping_index),
                    }
                )
        profiling_data["vmi"] = vmi_data

    return profiling_data


def _bands_by_target(report) -> dict[str, list]:
    """Group a report's bands by ``target_type`` (H6)."""
    grouped: dict[str, list] = {}
    for band in report.bands.all():
        grouped.setdefault(band.target_type or "section", []).append(band)
    return grouped


def _match_band(
    bands: list, value: float | None, assessment_label: str | None = None
) -> dict | None:
    """Return the first band whose range contains ``value`` (reuses
    ReportBand.contains_score). When ``assessment_label`` is given, only bands
    scoped to that label (or with no label = applies to all) are considered.

    Returns a serialisable band dict, or None when no band matches.
    """
    if value is None:
        return None
    for band in bands:
        if (
            assessment_label is not None
            and band.assessment_label
            and band.assessment_label != assessment_label
        ):
            continue
        if band.contains_score(value):
            return {
                "band_number": band.band_number,
                "band_label": band.band_label,
                "range": f"{band.range_min}-{band.range_max}",
                "description": band.description,
                "colour_code": band.colour_code,
            }
    return None


def _section_bands_by_id(report) -> dict[int, list]:
    """Group a report's target_type='section' bands by ``section_id`` (H6).

    Shared by the typological builder (top-N variable banding, SRS §3.2.1)
    and the Table layout builder (SRS §3.1.2/§3.2.2/§3.3.2) so both reuse the
    same ReportBand rows a psychometrician already defines for interpretative
    reports.
    """
    grouped: dict[int, list] = {}
    for band in report.bands.filter(target_type="section").select_related("section"):
        if band.section_id is not None:
            grouped.setdefault(band.section_id, []).append(band)
    return grouped


def _image_data_uri(image_field) -> str | None:
    """Encode an uploaded ImageField as a base64 data URI for PDF embedding.

    ``rendered_data`` is a JSON snapshot computed once at generation time and
    later rendered to PDF without a live request/filesystem context, so the
    image bytes are baked in here rather than referencing a path that may not
    resolve at render time. Returns None when there's no image, or when the
    file can't be read (e.g. missing from storage) — callers treat that as
    "no image" rather than failing report generation.
    """
    if not image_field:
        return None
    try:
        import base64
        import mimetypes

        content_type = mimetypes.guess_type(image_field.name)[0] or "image/png"
        with image_field.open("rb") as fh:
            encoded = base64.b64encode(fh.read()).decode("ascii")
        return f"data:{content_type};base64,{encoded}"
    except Exception:
        return None


def _build_layout_table(
    section_breakdown: list[dict], section_bands_by_id: dict[int, list], config: dict | None
) -> dict:
    """Build the Table layout (SRS §3.1.2/§3.2.2/§3.3.2) for section scores.

    Per the SRS sample table/graph head definition (Table_Graph_Title,
    Variable_Name, Data_Input_Name, Label, Colour_Code, Description): a
    layout section's ``table_graph_config`` supplies the column headers, and
    each row is one section score from the report's data-input-level
    breakdown, banded (when the report defines a target_type='section' band
    for that variable) for its Label/Colour/Description columns.

    This is the "Table" half of the layout stub — Graph rendering is scoped
    out (see the 'graph' branch in generate_report_data).
    """
    config = config or {}
    headers = {
        "table_title": config.get("table_title", ""),
        "variable_label": config.get("variable_label", "Variable"),
        "score_label": config.get("score_label", "Score"),
        "label_label": config.get("label_label", "Label"),
        "colour_label": config.get("colour_label", "Colour"),
        "description_label": config.get("description_label", "Description"),
    }
    rows = []
    for row in section_breakdown:
        bands = section_bands_by_id.get(row.get("section_id"), [])
        band = _match_band(bands, row.get("converted_score"))
        rows.append(
            {
                "variable": row.get("section_title"),
                "score": row.get("converted_score"),
                "label": band["band_label"] if band else "",
                "colour_code": band["colour_code"] if band else "",
                "description": band["description"] if band else "",
            }
        )
    return {"headers": headers, "rows": rows}


def _build_layout_graph(
    section_breakdown: list[dict], section_bands_by_id: dict[int, list], config: dict | None
) -> dict:
    """Build the Graph layout (SRS §3.1.2/§3.2.2/§3.3.2, REP-1) for section scores.

    Returns bar-chart data — one bar per variable, valued by its converted
    score and coloured by the matched section band (falling back to a default
    colour). ``max_value`` scales the axis: the larger of the observed scores
    and 100 (the natural ceiling for percentage/percentile conversions).
    """
    config = config or {}
    default_colour = config.get("bar_colour", "#3b82f6")
    bars = []
    observed_max = 0.0
    for row in section_breakdown:
        bands = section_bands_by_id.get(row.get("section_id"), [])
        band = _match_band(bands, row.get("converted_score"))
        value = row.get("converted_score") or 0
        observed_max = max(observed_max, value)
        bars.append(
            {
                "variable": row.get("section_title"),
                "value": value,
                "colour_code": (band["colour_code"] if band and band.get("colour_code") else default_colour),
                "label": band["band_label"] if band else "",
            }
        )
    return {
        "title": config.get("table_title", ""),
        "value_label": config.get("score_label", "Score"),
        "bars": bars,
        "max_value": max(observed_max, 100.0),
    }


def _pmi_by_assessment(mi) -> dict[str, float]:
    """Extract {assessment_label: PMI} from a MatchIndex's variable_details.

    Each variable_details entry carries the per-assessment ``pmi`` (constant
    across that assessment's variables — it is the AssessmentResult.pmi) plus
    the ``assessment`` label. We take the first non-null pmi seen per label.
    """
    result: dict[str, float] = {}
    for entry in mi.variable_details or []:
        label = entry.get("assessment")
        pmi = entry.get("pmi")
        if label and pmi is not None and label not in result:
            result[label] = pmi
    return result


def _build_pmi(report, match_indices, pmi_bands: list) -> dict[str, Any]:
    """Build the PMI report section (SRS 06 §3.3) + PMI-D gap index (§3.3.3).

    PMI is the per-assessment profile match. For each assessment we list the
    careers with that assessment's PMI (ordered by PMI descending) and, when
    PMI bands are defined for that assessment, the matching band.

    PMI-D = A1PMI - A2PMI per career (§3.3.3), which may be negative. The
    subtraction order (A1, A2) comes from the report's configured
    pmi_d_first/second_assessment; when unset it falls back to the first two
    assessment labels encountered. PMI-D careers are ordered by gap descending
    (largest positive gap first, largest negative last), matching the §3.3.4
    band layout that runs from ">40" down to "<-40".
    """
    # Collect per-assessment PMI per career, preserving label encounter order.
    labels: list[str] = []
    by_assessment: dict[str, list[dict]] = {}
    per_career: list[tuple] = []  # (mi, {label: pmi})
    for mi in match_indices:
        pmis = _pmi_by_assessment(mi)
        per_career.append((mi, pmis))
        for label, pmi in pmis.items():
            if label not in by_assessment:
                by_assessment[label] = []
                labels.append(label)
            by_assessment[label].append(
                {
                    "career_stream": mi.career_stream,
                    "career_title": mi.career_title,
                    "career_code": mi.career_code,
                    "pmi": pmi,
                    "band": _match_band(pmi_bands, pmi, assessment_label=label),
                }
            )

    # Order careers within each assessment by PMI descending.
    for label in by_assessment:
        by_assessment[label].sort(
            key=lambda c: c["pmi"] if c["pmi"] is not None else float("-inf"), reverse=True
        )

    pmi_section: dict[str, Any] = {
        "assessments": labels,
        "by_assessment": by_assessment,
    }

    # --- PMI-D gap index (§3.3.3) ---
    a1 = report.pmi_d_first_assessment or (labels[0] if labels else None)
    a2 = report.pmi_d_second_assessment or (labels[1] if len(labels) > 1 else None)
    if a1 and a2 and a1 != a2:
        gap_careers = []
        for mi, pmis in per_career:
            a1_pmi = pmis.get(a1)
            a2_pmi = pmis.get(a2)
            if a1_pmi is None or a2_pmi is None:
                continue
            pmi_d = round(a1_pmi - a2_pmi, 2)
            gap_careers.append(
                {
                    "career_stream": mi.career_stream,
                    "career_title": mi.career_title,
                    "career_code": mi.career_code,
                    "a1_pmi": a1_pmi,
                    "a2_pmi": a2_pmi,
                    "pmi_d": pmi_d,
                }
            )
        # Order by gap descending; band each PMI-D against its own bands.
        gap_careers.sort(key=lambda c: c["pmi_d"], reverse=True)
        pmid_bands = _bands_by_target(report).get("pmi_d", [])
        for c in gap_careers:
            c["band"] = _match_band(pmid_bands, c["pmi_d"])
        pmi_section["gap_index"] = {
            "first_assessment": a1,
            "second_assessment": a2,
            "formula": f"PMI-D = {a1}-PMI - {a2}-PMI",
            "careers": gap_careers,
        }

    return pmi_section


def select_profiling_data(
    match_indices: list,
    data_type: str = "HFMI",
    extraction_mode: str = "system",
    fmi_range: tuple[float, float] | None = None,
    n_categories: int = 0,
    n_criterions: int = 0,
    selected_career_titles: list[str] | None = None,
) -> dict[str, Any]:
    """Filter / sort profiling MatchIndex records per SRS 06 SRS 2.2.

    Two data types (one or both can be requested):
      HFMI - Data of criterions with HIGHEST FMIs
      LFMI - Data of criterions with LOWEST FMIs

    Two extraction modes:
      user   - User specifies an FMI range (e.g., 85-100) and manually selects
               which categories/careers to include from the filtered list.
      system - System auto-selects the top N careers by FMI (HFMI) or bottom N
               (LFMI), grouped by career_stream (category).

    Args:
        match_indices: list of MatchIndex records (already computed for the
            candidate + solution).
        data_type: "HFMI" or "LFMI".
        extraction_mode: "user" or "system".
        fmi_range: optional (min, max) FMI range for user-initiated selection.
        n_categories: how many career streams to include (system mode).
        n_criterions: how many careers per stream to include (system mode).
        selected_career_titles: when extraction_mode='user', the careers the
            user manually selected from the filtered list. When None in user
            mode, returns the filtered list WITHOUT final selection (so the
            UI can present it to the user for selection).

    Returns:
        dict with: data_type, extraction_mode, total_available, selected_count,
        selected (list of career dicts with stream/title/code/fmi).
    """
    # Sort: HFMI = descending by FMI, LFMI = ascending by FMI
    reverse = data_type == "HFMI"
    sorted_indices = sorted(match_indices, key=lambda m: m.final_match_index or 0, reverse=reverse)

    # User-initiated: filter by FMI range, optionally apply manual selection
    if extraction_mode == "user":
        if fmi_range:
            lo, hi = fmi_range
            filtered = [m for m in sorted_indices if lo <= (m.final_match_index or 0) <= hi]
        else:
            filtered = sorted_indices
        if selected_career_titles is not None:
            filtered = [m for m in filtered if m.career_title in selected_career_titles]
        return {
            "data_type": data_type,
            "extraction_mode": extraction_mode,
            "fmi_range": list(fmi_range) if fmi_range else None,
            "total_available": len(sorted_indices),
            "selected_count": len(filtered),
            "selected": [_match_index_to_dict(m) for m in filtered],
        }

    # System-initiated: group by career_stream, pick top N categories by their
    # best FMI (HFMI) or worst FMI (LFMI), then pick top/bottom N careers
    # within each selected category.
    by_stream: dict[str, list] = {}
    for m in sorted_indices:
        by_stream.setdefault(m.career_stream or "Uncategorised", []).append(m)

    # Rank streams by their best (HFMI) or worst (LFMI) FMI
    def stream_key(item):
        stream, indices = item
        fmis = [i.final_match_index or 0 for i in indices]
        return max(fmis) if reverse else min(fmis)

    ranked_streams = sorted(by_stream.items(), key=stream_key, reverse=reverse)
    selected_streams = ranked_streams[:n_categories] if n_categories > 0 else ranked_streams

    selected: list[dict] = []
    for _stream, indices in selected_streams:
        top_in_stream = indices[:n_criterions] if n_criterions > 0 else indices
        selected.extend(_match_index_to_dict(m) for m in top_in_stream)

    return {
        "data_type": data_type,
        "extraction_mode": extraction_mode,
        "n_categories": n_categories,
        "n_criterions": n_criterions,
        "total_available": len(sorted_indices),
        "selected_count": len(selected),
        "selected": selected,
    }


def _match_index_to_dict(m) -> dict[str, Any]:
    return {
        "id": m.id,
        "career_stream": m.career_stream,
        "career_title": m.career_title,
        "career_code": m.career_code,
        "fmi": m.final_match_index,
        "vmi": m.variable_mapping_index,
    }
