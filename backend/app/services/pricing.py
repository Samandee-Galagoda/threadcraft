"""Dynamic pricing engine.

Pure function: no database session, no I/O, no wall-clock reads. Every
number is a Decimal, rounded to 2 dp with ROUND_HALF_UP at each labelled
step below — never float, and never rounded only at the end, so the
itemised line items always sum exactly to the displayed subtotals.

Algorithm (this ordering is the spec — see docs/testing/pricing-verification.md
for hand-computed cases that must match this exactly):

  1. size_factor  = clamp(1 + (primary_body_cm - reference_body_cm) / 100 * k, min, max)
  2. fabric_metres = base_fabric_metres * product(option.fabric_multiplier) * size_factor
  3. material      = fabric_metres * (cost_per_metre + colour_surcharge)
  4. stitching     = base_stitching_cost + sum(option.stitching_premium)
  5. subtotal      = base_price + stitching + material
  6. delivery      = 0 if subtotal >= free_delivery_threshold else delivery_fee
  7. total         = subtotal + delivery
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


def _round(value: Decimal, places: Decimal = TWO_PLACES) -> Decimal:
    return value.quantize(places, rounding=ROUND_HALF_UP)


def _clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return max(low, min(high, value))


@dataclass(frozen=True)
class OptionInput:
    code: str
    label: str
    stitching_premium: Decimal = Decimal("0")
    fabric_multiplier: Decimal = Decimal("1")


@dataclass(frozen=True)
class PricingInput:
    cloth_type_name: str
    base_price: Decimal
    base_stitching_cost: Decimal
    base_fabric_metres: Decimal
    reference_body_cm: Decimal

    material_name: str
    material_cost_per_metre: Decimal
    colour_surcharge: Decimal = Decimal("0")

    options: tuple[OptionInput, ...] = field(default_factory=tuple)
    primary_body_cm: Decimal | None = None

    delivery_fee: Decimal = Decimal("350")
    free_delivery_threshold: Decimal = Decimal("15000")

    size_factor_k: Decimal = Decimal("0.60")
    size_factor_min: Decimal = Decimal("0.85")
    size_factor_max: Decimal = Decimal("1.40")


@dataclass(frozen=True)
class LineItem:
    label: str
    amount: Decimal
    category: str  # base | stitching | material | delivery


@dataclass(frozen=True)
class PriceBreakdown:
    lines: tuple[LineItem, ...]
    fabric_metres: Decimal
    size_factor: Decimal
    base: Decimal
    stitching: Decimal
    material: Decimal
    delivery: Decimal
    total: Decimal


def calculate_price(inp: PricingInput) -> PriceBreakdown:
    # 1. Size factor
    if inp.primary_body_cm is None:
        size_factor = Decimal("1")
    else:
        raw_factor = (
            Decimal("1") + (inp.primary_body_cm - inp.reference_body_cm) / Decimal("100") * inp.size_factor_k
        )
        size_factor = _clamp(raw_factor, inp.size_factor_min, inp.size_factor_max)
    size_factor = _round(size_factor, FOUR_PLACES)

    # 2. Fabric metres
    fabric_multiplier_product = Decimal("1")
    for opt in inp.options:
        fabric_multiplier_product *= opt.fabric_multiplier
    fabric_metres = _round(inp.base_fabric_metres * fabric_multiplier_product * size_factor)

    # 3. Material cost
    material = _round(fabric_metres * (inp.material_cost_per_metre + inp.colour_surcharge))

    # 4. Stitching cost (base + per-option premiums, each its own line item)
    stitching_lines = [
        LineItem(label=f"{opt.label}", amount=_round(opt.stitching_premium), category="stitching")
        for opt in inp.options
        if opt.stitching_premium != 0
    ]
    stitching = _round(inp.base_stitching_cost + sum((li.amount for li in stitching_lines), Decimal("0")))

    # 5. Subtotal
    subtotal = inp.base_price + stitching + material

    # 6. Delivery
    delivery = Decimal("0") if subtotal >= inp.free_delivery_threshold else _round(inp.delivery_fee)

    # 7. Total
    total = _round(subtotal + delivery)

    lines = (
        LineItem(f"Base price ({inp.cloth_type_name})", _round(inp.base_price), "base"),
        LineItem("Base stitching", _round(inp.base_stitching_cost), "stitching"),
        *stitching_lines,
        LineItem(f"Material ({inp.material_name}, {fabric_metres}m)", material, "material"),
        LineItem("Delivery" if delivery > 0 else "Delivery (free over threshold)", delivery, "delivery"),
    )

    return PriceBreakdown(
        lines=lines,
        fabric_metres=fabric_metres,
        size_factor=size_factor,
        base=_round(inp.base_price),
        stitching=stitching,
        material=material,
        delivery=delivery,
        total=total,
    )
