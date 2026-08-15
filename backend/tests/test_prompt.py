from app.services.prompt import DEFAULT_NEGATIVE_PROMPT, PromptSpec, build_prompt


def test_basic_prompt_construction():
    spec = PromptSpec(
        cloth_type_term="dress",
        option_terms=("V-neck", "puffed sleeves"),
        material_term="silk",
        colour_term="burgundy",
        custom_description="",
    )
    result = build_prompt(spec)
    assert "dress" in result.positive
    assert "V-neck, puffed sleeves" in result.positive
    assert "burgundy silk fabric" in result.positive
    assert result.negative == DEFAULT_NEGATIVE_PROMPT


def test_prompt_is_deterministic():
    spec = PromptSpec(
        cloth_type_term="shirt",
        option_terms=("collar",),
        material_term="cotton",
        colour_term="ivory",
    )
    assert build_prompt(spec) == build_prompt(spec)


def test_empty_option_terms_falls_back_to_classic_silhouette():
    spec = PromptSpec(cloth_type_term="skirt", option_terms=(), material_term="denim", colour_term="blue")
    result = build_prompt(spec)
    assert "classic silhouette" in result.positive


def test_custom_description_is_appended():
    spec = PromptSpec(
        cloth_type_term="kurta",
        option_terms=("collar",),
        material_term="linen",
        colour_term="sage",
        custom_description="with a mandarin collar and side slits",
    )
    result = build_prompt(spec)
    assert "with a mandarin collar and side slits" in result.positive


def test_custom_description_is_truncated_to_200_chars():
    long_text = "x" * 500
    spec = PromptSpec(
        cloth_type_term="dress",
        option_terms=(),
        material_term="silk",
        colour_term="red",
        custom_description=long_text,
    )
    result = build_prompt(spec)
    # 200 chars of 'x' plus the leading ", " separator
    assert result.positive.count("x") == 200


def test_custom_description_strips_newlines_and_control_chars():
    spec = PromptSpec(
        cloth_type_term="dress",
        option_terms=(),
        material_term="silk",
        colour_term="red",
        custom_description="line one\nline two\twith a tab",
    )
    result = build_prompt(spec)
    assert "\n" not in result.positive
    assert "\t" not in result.positive
    assert "line one line two with a tab" in result.positive


def test_missing_description_produces_no_dangling_comma():
    spec = PromptSpec(cloth_type_term="dress", option_terms=(), material_term="silk", colour_term="red")
    result = build_prompt(spec)
    assert ",," not in result.positive
    assert not result.positive.rstrip().endswith(",")
