# ADR 0003: Configuration-driven catalogue instead of hardcoded garment types

## Status
Accepted

## Context
The proposal requires that an administrator can add new garment categories (and their measurement fields, design tags, and pricing rules) without modifying application code. The original prototype hardcoded all of this: 8 cloth types and their prices in `DesignWizard.jsx`, 5 of 9 garments' measurement fields in `MeasurementGuide.jsx`'s `MEASUREMENT_DATA` object, and design tag arrays inline in the wizard component.

## Decision
Every garment-specific fact lives in the database, editable via the admin API:
- `cloth_types` — name, base price, base fabric requirement, reference body measurement
- `measurement_fields` — per-cloth-type ordered list of required measurements with validation ranges (seeded from the original `MEASUREMENT_DATA`, extended to cover the 4 garments that previously had none)
- `design_option_groups` / `design_options` — the Fit/Neckline/Sleeve/Pattern tags, each carrying an `ai_prompt_term` (decoupling the UI label from the diffusion-model prompt vocabulary) and a `stitching_premium`/`fabric_multiplier` (making pricing configuration-driven)
- `materials` / `material_colors` — fabric catalogue with live stock levels

The pricing engine (`app/services/pricing.py`) and prompt builder (`app/services/prompt.py`) are pure functions that take these values as plain inputs — they contain no per-garment logic themselves.

## Consequences
- Adding a new garment category is an admin API call (`POST /api/admin/catalog/cloth-types` + a few `POST .../measurement-fields`), not a code change and deploy. This is demonstrated directly by `tests/test_api_admin.py::test_admin_can_add_cloth_type_without_code_changes`.
- The frontend wizard must read this catalogue from the API rather than hold its own copy of cloth types/tags — this is addressed in a later PR (the frontend still has some hardcoded catalogue data as of this PR, tracked as a known gap until the wizard is wired to `/api/catalog/*`).
