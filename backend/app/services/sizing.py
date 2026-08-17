"""UK size-band lookup — deterministic, no model.

This is the replacement for the withdrawn fit recommender, and the split of
responsibility is the point:

  * The **hard, genuinely ML part** — inferring chest, waist and hip from two
    numbers a customer actually knows (height and weight) — is done by the
    trained measurement predictor, which is validated and strictly monotonic in
    body size.
  * The **easy, standards part** — turning measurements into a size label — is a
    table lookup. Learning it from rental data was what produced a recommender
    that told a 45 kg customer to wear a size 27 (see
    docs/testing/ml-evaluation.md).

Because the chart is monotonic and the predictor is monotonic, the composition
cannot invert. That is a guarantee by construction, not a metric to be measured
and hoped for.

**On the chart itself.** Ranges follow common UK retail womenswear/menswear
conventions. Real charts differ by several centimetres between retailers, which
is precisely why ready-to-wear fit is unreliable and why a made-to-measure
service exists at all — so the number here is offered as a reference point, never
as the specification a garment is cut to.
"""

from dataclasses import dataclass

# (label, bust/chest cm, waist cm, hip cm) — inclusive lower bound, exclusive
# upper, so adjacent bands cannot both claim a measurement or leave a gap.
WOMENS_BANDS = (
    ("UK 6", (76, 82), (58, 64), (84, 90)),
    ("UK 8", (82, 86), (64, 68), (90, 94)),
    ("UK 10", (86, 90), (68, 72), (94, 98)),
    ("UK 12", (90, 95), (72, 77), (98, 103)),
    ("UK 14", (95, 100), (77, 82), (103, 108)),
    ("UK 16", (100, 105), (82, 87), (108, 113)),
    ("UK 18", (105, 110), (87, 92), (113, 118)),
    ("UK 20", (110, 115), (92, 97), (118, 123)),
    ("UK 22", (115, 120), (97, 102), (123, 128)),
    ("UK 24", (120, 999), (102, 999), (128, 999)),
)

MENS_BANDS = (
    ("XS", (81, 86), (66, 71), (84, 89)),
    ("S", (86, 91), (71, 76), (89, 94)),
    ("M", (91, 97), (76, 81), (94, 99)),
    ("L", (97, 102), (81, 87), (99, 104)),
    ("XL", (102, 107), (87, 92), (104, 109)),
    ("XXL", (107, 112), (92, 97), (109, 114)),
    ("3XL", (112, 999), (97, 999), (114, 999)),
)

MEASUREMENT_LABELS = {"chest": "chest", "waist": "waist", "hip": "hip"}

# Which slot of each band tuple a measurement is compared against.
_SLOT = {"chest": 1, "waist": 2, "hip": 3}


@dataclass(frozen=True)
class SizeEstimate:
    size: str
    # The band each individual measurement landed in. A body rarely sits in one
    # band across all three, and hiding that would misrepresent the certainty.
    per_measurement: dict[str, str]
    spans_multiple_bands: bool
    note: str


def _bands(sex: int | None):
    """sex: 1 = male, 0 = female. Defaults to the women's chart, which is what
    the wizard's 'Sizing basis' control defaults to."""
    return MENS_BANDS if sex == 1 else WOMENS_BANDS


def band_for(measurement: str, value: float, sex: int | None = None) -> str | None:
    """The size band a single measurement falls in, or None if unknown."""
    if value is None or measurement not in _SLOT:
        return None
    bands = _bands(sex)
    slot = _SLOT[measurement]
    for band in bands:
        low, high = band[slot]
        if low <= value < high:
            return band[0]
    # Below the smallest band: clamp rather than return nothing, so a very
    # slight customer still gets a reference point.
    return bands[0][0] if value < bands[0][slot][0] else bands[-1][0]


def estimate_size(measurements: dict[str, float], sex: int | None = None) -> SizeEstimate | None:
    """Map chest/waist/hip onto a UK size band.

    Where the measurements disagree, the **largest** band wins. That is standard
    tailoring practice — cloth can be taken in but not added — and it is the
    conservative direction for a customer using this as a reference.
    """
    bands = _bands(sex)
    order = [b[0] for b in bands]

    per_measurement = {}
    for name in _SLOT:
        value = measurements.get(name)
        if value is not None:
            label = band_for(name, float(value), sex)
            if label:
                per_measurement[name] = label

    if not per_measurement:
        return None

    chosen = max(per_measurement.values(), key=order.index)
    spans = len(set(per_measurement.values())) > 1

    if spans:
        smallest = min(per_measurement.values(), key=order.index)
        note = (
            f"Your measurements span {smallest} to {chosen}, which is normal — "
            "off-the-rack sizes assume one fixed set of proportions. We've shown the "
            "larger, since ready-to-wear can be taken in but not let out."
        )
    else:
        note = f"Your chest, waist and hip all fall in {chosen}."

    return SizeEstimate(
        size=chosen,
        per_measurement=per_measurement,
        spans_multiple_bands=spans,
        note=note,
    )
