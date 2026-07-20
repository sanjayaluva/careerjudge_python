"""Question configuration validation.

Validates that each question type has the required configuration
before it can be submitted for review or confirmed. Called from:
  - QuestionViewSet.submit_for_review (blocks submission if invalid)
  - QuestionViewSet.update (warns but doesn't block — authors can save drafts)
  - Frontend question editor (shows validation warnings in real-time)

Validation rules per question type:
  MCQ (1a-1h): ≥2 options, ≥1 correct, question_text_1
  FITB (2a-2d): ≥1 option with correct_answers, question_text_1
  Match (3): ≥2 MATCH_A options + ≥2 MATCH_B options, all with match_pair_id
  Grid (4): grid_rows ≥1, grid_cols ≥1, ≥1 DRAG_POOL option
  Hotspot (5a/5b): image required, ≥1 hotspot_area with is_correct=True
                   5a: ≥1 correct area, 5b: ≥2 correct areas
  Rank (6a/6b): ≥2 RANK options
  Rating (7): rating_scale_points ≥2
  Forced Choice (8a/8b): ≥2 FORCED_CHOICE options with predefined_score
"""

from apps.question_bank.models import Question


def validate_question_config(question: Question) -> list[str]:
    """Validate that a question has all required configuration.

    Returns a list of error messages. Empty list = valid.
    """
    errors = []
    q = question
    qtype = q.question_type

    # --- Common validations (all types) ---
    if not q.question_title or not q.question_title.strip():
        errors.append("Question title is required.")
    if not q.question_text_1 or not q.question_text_1.strip():
        errors.append("Question text 1 is required.")
    if not q.scoring_type:
        errors.append("Scoring type is required.")

    # --- MCQ types (1a-1h) ---
    if qtype.startswith("MCQ_"):
        options = list(q.options.all())
        if len(options) < 2:
            errors.append(f"MCQ requires at least 2 options (has {len(options)}).")
        correct = [o for o in options if o.is_correct]
        if len(correct) < 1:
            errors.append("MCQ requires at least 1 correct option.")
        # Image options type needs images on options
        if qtype == "MCQ_TEXT_IMAGE_IMG_OPTIONS":
            for o in options:
                if not o.image_file:
                    errors.append(
                        f"Option '{o.text_value or 'untitled'}' is missing an image "
                        "(required for MCQ with Image Options)."
                    )
                    break
        # Audio/Video types need media files
        if qtype == "MCQ_AUDIO_MULTI":
            if not q.media_files.filter(media_type="audio").exists():
                errors.append("MCQ Audio requires at least 1 audio file.")
        if qtype == "MCQ_VIDEO_MULTI":
            if not q.media_files.filter(media_type="video").exists():
                errors.append("MCQ Video requires at least 1 video file.")
        # Flash types need flash items
        if qtype in ("MCQ_WORD_FLASH_MULTI", "MCQ_IMAGE_FLASH_MULTI"):
            if not q.flash_items.exists():
                errors.append("Flash MCQ requires at least 1 flash item.")
            if not q.flash_interval_ms or q.flash_interval_ms < 100:
                errors.append("Flash interval must be at least 100ms.")
        # Passage type needs passage
        if qtype == "MCQ_PASSAGE_DISPLAY_MULTI":
            if not q.passage_title or not q.passage_title.strip():
                errors.append("Passage MCQ requires a passage title.")
            if not q.passage_body or not q.passage_body.strip():
                errors.append("Passage MCQ requires passage body text.")
        # Image display type needs image
        if qtype == "MCQ_IMAGE_DISPLAY_MULTI":
            if not q.image:
                errors.append("Image Display MCQ requires a question image.")

    # --- FITB types (2a-2d) ---
    elif qtype.startswith("FITB_"):
        options = list(q.options.all())
        if len(options) < 1:
            errors.append("FITB requires at least 1 field (option).")
        for o in options:
            if not o.correct_answers.exists():
                errors.append(
                    f"Field '{o.text_value or f'Field {o.order}'}' has no correct answers defined."
                )
                break
        # Flash types need flash items
        if qtype in ("FITB_WORD_FLASH_MULTI", "FITB_IMAGE_FLASH_MULTI"):
            if not q.flash_items.exists():
                errors.append("Flash FITB requires at least 1 flash item.")
            if not q.flash_interval_ms or q.flash_interval_ms < 100:
                errors.append("Flash interval must be at least 100ms.")

    # --- Match (3) ---
    elif qtype == "MATCH_FOLLOWING":
        match_a = q.options.filter(option_type="MATCH_A").count()
        match_b = q.options.filter(option_type="MATCH_B").count()
        if match_a < 2:
            errors.append(f"Match requires at least 2 Group A items (has {match_a}).")
        if match_b < 2:
            errors.append(f"Match requires at least 2 Group B items (has {match_b}).")
        if match_a != match_b:
            errors.append(f"Match requires equal Group A and B items (A={match_a}, B={match_b}).")
        # Check all have match_pair_id
        for o in q.options.filter(option_type__in=["MATCH_A", "MATCH_B"]):
            if not o.match_pair_id:
                errors.append(f"Option '{o.text_value}' is missing a match_pair_id.")
                break

    # --- Grid (4) ---
    elif qtype == "GRID_LIST_SELECTION":
        if not q.grid_rows or q.grid_rows < 1:
            errors.append("Grid requires grid_rows ≥ 1.")
        if not q.grid_cols or q.grid_cols < 1:
            errors.append("Grid requires grid_cols ≥ 1.")
        drag_pool = q.options.filter(option_type="DRAG_POOL").count()
        if drag_pool < 1:
            errors.append("Grid requires at least 1 cell content (DRAG_POOL option).")

    # --- Hotspot (5a/5b) ---
    elif qtype in ("HOTSPOT_SINGLE", "HOTSPOT_MULTI"):
        if not q.image:
            errors.append("Hotspot requires a question image.")
        if not q.image_width or not q.image_height:
            errors.append("Hotspot requires image_width and image_height to be set.")
        areas = list(q.hotspot_areas.all())
        if len(areas) < 1:
            errors.append("Hotspot requires at least 1 hotspot area to be defined.")
        correct_areas = [a for a in areas if a.is_correct]
        if qtype == "HOTSPOT_SINGLE":
            if len(correct_areas) < 1:
                errors.append("Hotspot Single requires at least 1 correct hotspot area.")
        else:  # HOTSPOT_MULTI
            if len(correct_areas) < 2:
                errors.append(
                    f"Hotspot Multi requires at least 2 correct hotspot areas (has {len(correct_areas)})."
                )

    # --- Rank (6a/6b) ---
    elif qtype in ("RANK_SIMPLE", "RANK_THEN_RATE"):
        rank_options = q.options.filter(option_type="RANK").count()
        if rank_options < 2:
            errors.append(f"Rank requires at least 2 options (has {rank_options}).")
        if qtype == "RANK_THEN_RATE":
            if not q.rating_scale_points or q.rating_scale_points < 2:
                errors.append("Rank-then-Rate requires rating_scale_points ≥ 2.")

    # --- Rating (7) ---
    elif qtype == "STANDARD_RATING_SCALE":
        if not q.rating_scale_points or q.rating_scale_points < 2:
            errors.append("Rating scale requires rating_scale_points ≥ 2.")
        if not q.rating_direction:
            errors.append("Rating scale requires a rating_direction (FORWARD/REVERSE).")

    # --- Forced Choice (8a/8b) ---
    elif qtype in ("FORCED_CHOICE_SINGLE_LEVEL", "FORCED_CHOICE_TWO_LEVEL"):
        fc_options = q.options.filter(option_type="FORCED_CHOICE").count()
        if fc_options < 2:
            errors.append(f"Forced-Choice requires at least 2 options (has {fc_options}).")
        # Check predefined_score is set
        for o in q.options.filter(option_type="FORCED_CHOICE"):
            if o.predefined_score is None or o.predefined_score == 0:
                errors.append(f"Option '{o.text_value}' is missing a predefined_score.")
                break
        # Two-level needs rating_scale_points
        if qtype == "FORCED_CHOICE_TWO_LEVEL":
            if not q.rating_scale_points or q.rating_scale_points < 2:
                errors.append("Forced-Choice Two-Level requires rating_scale_points ≥ 2.")

    return errors


def question_is_ready_for_review(question: Question) -> bool:
    """Check if a question has all required configuration for review submission."""
    return len(validate_question_config(question)) == 0
