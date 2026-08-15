"""AI prompt-engineering pipeline.

Converts structured customer inputs (cloth type, design tags, material,
colour, free-text description) into the actual string sent to the
text-to-image model. Pure and deterministic — no I/O, no randomness — so
it's exact-string testable.

This is the project's primary technical contribution per the proposal:
structured tags (with an explicit ai_prompt_term per option, stored in the
database — see app/models/catalog.py) produce a materially better prompt
than raw free text, because the vocabulary is curated per design dimension
rather than left to whatever a customer happens to type.
"""

from dataclasses import dataclass

DEFAULT_POSITIVE_TEMPLATE = (
    "professional fashion product photograph of a {cloth_type}, {option_terms}, "
    "{colour_term} {material_term} fabric{description_clause}, "
    "full-length front view on a plain studio background, soft diffused lighting, "
    "high detail, photorealistic, 8k"
)

DEFAULT_NEGATIVE_PROMPT = (
    "human face, watermark, text, logo, deformed, extra limbs, extra sleeves, "
    "blurry, low quality, cropped, distorted proportions"
)

MAX_DESCRIPTION_CHARS = 200


@dataclass(frozen=True)
class PromptSpec:
    cloth_type_term: str
    option_terms: tuple[str, ...]
    material_term: str
    colour_term: str
    custom_description: str = ""
    positive_template: str = DEFAULT_POSITIVE_TEMPLATE
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT


@dataclass(frozen=True)
class BuiltPrompt:
    positive: str
    negative: str


def _sanitize_description(text: str) -> str:
    """Strips newlines/control chars and truncates. Free text goes straight
    into a prompt string sent to a third-party API, so it must never be able
    to break out of the intended sentence structure or balloon the request."""
    cleaned = " ".join(text.split())
    cleaned = "".join(ch for ch in cleaned if ch.isprintable())
    return cleaned[:MAX_DESCRIPTION_CHARS].strip()


def build_prompt(spec: PromptSpec) -> BuiltPrompt:
    option_terms = ", ".join(t for t in spec.option_terms if t) or "classic silhouette"

    description = _sanitize_description(spec.custom_description)
    description_clause = f", {description}" if description else ""

    positive = spec.positive_template.format(
        cloth_type=spec.cloth_type_term,
        option_terms=option_terms,
        colour_term=spec.colour_term,
        material_term=spec.material_term,
        description_clause=description_clause,
    )
    # Collapse incidental double spaces from empty template slots.
    positive = " ".join(positive.split())

    return BuiltPrompt(positive=positive, negative=spec.negative_prompt)
