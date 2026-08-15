# Pricing engine verification

`app/services/pricing.py::calculate_price` is a pure function tested against 20 hand-computed combinations in `backend/tests/fixtures/pricing_cases.csv`, run by `backend/tests/test_pricing.py`. As of the last run: **25/25 tests pass, 100% line coverage on `pricing.py`**.

## Algorithm (fixed order — this is the spec)

1. `size_factor = clamp(1 + (primary_body_cm − reference_body_cm) / 100 × k, min, max)` — `1.0000` if no primary measurement is supplied
2. `fabric_metres = round(base_fabric_metres × Π(option.fabric_multiplier) × size_factor, 2)`
3. `material = round(fabric_metres × (cost_per_metre + colour_surcharge), 2)`
4. `stitching = round(base_stitching_cost + Σ(option.stitching_premium), 2)`
5. `subtotal = base_price + stitching + material`
6. `delivery = 0 if subtotal ≥ free_delivery_threshold else round(delivery_fee, 2)`
7. `total = round(subtotal + delivery, 2)`

All arithmetic is `Decimal`, rounded `ROUND_HALF_UP` at each labelled step — never `float`, and never rounded only once at the end (so the itemised line items always sum exactly to the displayed subtotals — see `test_line_items_sum_to_reported_totals`).

## Long-hand verification of 3 representative cases

### Case 3 — measurement above reference (tests the size factor)

Dress, base price 3500, base stitching 600, base fabric 2.6 m, reference body 90 cm, silk at 1800/m, no colour surcharge, no design options, customer's primary measurement = 110 cm.

```
size_factor = 1 + (110 − 90) / 100 × 0.60 = 1 + 0.20 × 0.60 = 1 + 0.12 = 1.1200
fabric_metres = 2.6 × 1 × 1.1200 = 2.912 → round → 2.91 m
material = 2.91 × 1800 = 5238.00
stitching = 600.00 (no options)
subtotal = 3500.00 + 600.00 + 5238.00 = 9338.00
subtotal (9338.00) < free_delivery_threshold (15000.00) → delivery = 350.00
total = 9338.00 + 350.00 = 9688.00
```
Matches `expected_total = 9688.00` in the fixture (case 3).

### Case 9 — two stacked design options (tests premium sum + multiplier product)

T-shirt, base price 2200, base stitching 300, base fabric 1.4 m, reference 96 cm, cotton at 650/m, customer's chest = 96 cm (= reference, so size_factor = 1). Two options: one with premium 300 / multiplier 1.20, one with premium 100 / multiplier 1.02.

```
size_factor = 1.0000 (measurement equals reference)
fabric_multiplier_product = 1.20 × 1.02 = 1.224
fabric_metres = 1.4 × 1.224 × 1.0000 = 1.7136 → round → 1.71 m
material = 1.71 × 650 = 1111.50
stitching = 300 (base) + 300 + 100 = 700.00
subtotal = 2200.00 + 700.00 + 1111.50 = 4011.50
subtotal < threshold → delivery = 350.00
total = 4011.50 + 350.00 = 4361.50
```
Matches `expected_total = 4361.50` in the fixture (case 9).

### Case 15 — Decimal rounding at the exact .xx5 boundary

Minimal garment, base price 1000, base stitching 0, base fabric **1.005** m, reference 100 cm, cost/metre 100, no measurement supplied, delivery fee 0 (isolates the rounding question from delivery logic).

```
size_factor = 1.0000 (no primary_body_cm supplied)
fabric_metres = round(1.005 × 1 × 1.0000, 2)
```
`Decimal("1.005")` is exact (unlike the equivalent `float`, which would actually store `1.00499999...`). `ROUND_HALF_UP` on an exact `.xx5` rounds away from zero:
```
fabric_metres = 1.01 m
material = 1.01 × 100 = 101.00
stitching = 0.00
subtotal = 1000.00 + 0.00 + 101.00 = 1101.00
delivery = 0 (threshold set to 0 for this case — always "free")
total = 1101.00
```
Matches `expected_total = 1101.00` in the fixture (case 15). This specifically guards against a naive `float` rounding implementation, which would have produced `1.00` here due to binary floating-point representation error — the reason the entire engine uses `Decimal` throughout rather than rounding once at the end with floats.

## Full case list

See `backend/tests/fixtures/pricing_cases.csv` for all 20 cases (baseline, size-factor clamping at both ends, single/multiple stacked options, colour surcharge, free-delivery-threshold boundary ± 1 cent, zero delivery fee, and a high-value order). Every case's expected values were computed by hand using the algorithm above before `pytest` was run against them — the test run at the top of this document is the record of that verification passing, not the source of the expected values.
