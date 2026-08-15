"""Pricing engine verification — the graded artefact.

tests/fixtures/pricing_cases.csv contains 20 combinations, each with hand-
computed expected values (see docs/testing/pricing-verification.md for the
long-hand arithmetic behind 3 representative cases). This file only turns
that CSV into pytest parameters and asserts calculate_price() matches
exactly, case by case, plus a handful of additional boundary/edge tests
not captured in the CSV.
"""

import csv
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.pricing import OptionInput, PricingInput, calculate_price

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _parse_semicolon_decimals(value: str) -> list[Decimal]:
    if not value:
        return []
    return [Decimal(v) for v in value.split(";")]


def load_pricing_cases() -> list[dict]:
    with open(FIXTURES_DIR / "pricing_cases.csv", newline="") as f:
        return list(csv.DictReader(f))


CASES = load_pricing_cases()


def _build_input(row: dict) -> PricingInput:
    premiums = _parse_semicolon_decimals(row["option_premiums"])
    multipliers = _parse_semicolon_decimals(row["option_multipliers"])
    options = tuple(
        OptionInput(code=f"opt{i}", label=f"Option {i}", stitching_premium=p, fabric_multiplier=m)
        for i, (p, m) in enumerate(zip(premiums, multipliers, strict=True))
    )
    primary_body_cm = Decimal(row["primary_body_cm"]) if row["primary_body_cm"] else None

    return PricingInput(
        cloth_type_name="Test Garment",
        base_price=Decimal(row["base_price"]),
        base_stitching_cost=Decimal(row["base_stitching"]),
        base_fabric_metres=Decimal(row["base_fabric_metres"]),
        reference_body_cm=Decimal(row["reference_body_cm"]),
        material_name="Test Material",
        material_cost_per_metre=Decimal(row["material_cost_per_metre"]),
        colour_surcharge=Decimal(row["colour_surcharge"]),
        options=options,
        primary_body_cm=primary_body_cm,
        delivery_fee=Decimal(row["delivery_fee"]),
        free_delivery_threshold=Decimal(row["free_delivery_threshold"]),
        size_factor_k=Decimal(row["size_factor_k"]),
        size_factor_min=Decimal(row["size_factor_min"]),
        size_factor_max=Decimal(row["size_factor_max"]),
    )


@pytest.mark.parametrize("row", CASES, ids=[f"{r['case_id']}_{r['description'][:30]}" for r in CASES])
def test_pricing_case(row: dict):
    inp = _build_input(row)
    result = calculate_price(inp)

    assert result.fabric_metres == Decimal(row["expected_fabric_metres"]), "fabric_metres mismatch"
    assert result.base == Decimal(row["expected_base"]), "base mismatch"
    assert result.stitching == Decimal(row["expected_stitching"]), "stitching mismatch"
    assert result.material == Decimal(row["expected_material"]), "material mismatch"
    assert result.delivery == Decimal(row["expected_delivery"]), "delivery mismatch"
    assert result.total == Decimal(row["expected_total"]), "total mismatch"


def test_exactly_20_cases_present():
    assert len(CASES) == 20


def test_total_always_equals_subtotal_plus_delivery():
    for row in CASES:
        inp = _build_input(row)
        result = calculate_price(inp)
        assert result.total == result.base + result.stitching + result.material + result.delivery


def test_line_items_sum_to_reported_totals():
    """Every displayed line item must sum to exactly the category subtotal —
    otherwise an itemised breakdown that doesn't add up would be shown to a
    paying customer."""
    for row in CASES:
        inp = _build_input(row)
        result = calculate_price(inp)
        stitching_lines = sum((li.amount for li in result.lines if li.category == "stitching"), Decimal("0"))
        material_lines = sum((li.amount for li in result.lines if li.category == "material"), Decimal("0"))
        delivery_lines = sum((li.amount for li in result.lines if li.category == "delivery"), Decimal("0"))
        assert stitching_lines == result.stitching
        assert material_lines == result.material
        assert delivery_lines == result.delivery


def test_no_options_is_pure_function_of_inputs():
    """Calling twice with identical inputs must give identical output —
    no hidden state, no wall-clock dependency."""
    inp = _build_input(CASES[0])
    assert calculate_price(inp) == calculate_price(inp)


def test_negative_measurement_deviation_never_produces_negative_fabric():
    inp = PricingInput(
        cloth_type_name="Edge case",
        base_price=Decimal("1000"),
        base_stitching_cost=Decimal("0"),
        base_fabric_metres=Decimal("1"),
        reference_body_cm=Decimal("100"),
        material_name="M",
        material_cost_per_metre=Decimal("100"),
        primary_body_cm=Decimal("0"),  # extreme deviation
    )
    result = calculate_price(inp)
    assert result.fabric_metres > 0
    assert result.size_factor == inp.size_factor_min
