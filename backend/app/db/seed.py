"""Idempotent seed script. Run with: python -m app.db.seed

Ports MEASUREMENT_DATA from frontend/src/pages/MeasurementGuide.jsx
verbatim for the 5 garments it already covers (dress, tshirt, shirt,
skirt, trousers) and adds the 3 garments whose tabs existed in that file
with no data (kurta, saree blouse, salwar kameez) plus blouse.

Also seeds ~15 historical orders spread over 90 days with varied
statuses, so admin analytics has real shape from the first run rather
than an empty-chart demo.
"""

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.catalog import (
    ClothType,
    DesignOption,
    DesignOptionGroup,
    Material,
    MaterialColor,
    MeasurementField,
)
from app.models.order import Order, OrderStatusHistory
from app.models.settings import AppSetting
from app.models.user import User

CLOTH_TYPES = [
    dict(
        slug="tshirt",
        name="T-shirt",
        ai_prompt_noun="t-shirt",
        base_price=Decimal("2200"),
        base_stitching_cost=Decimal("300"),
        base_fabric_metres=Decimal("1.4"),
        reference_body_cm=Decimal("96"),
        sort_order=1,
    ),
    dict(
        slug="shirt",
        name="Shirt",
        ai_prompt_noun="button-up shirt",
        base_price=Decimal("2800"),
        base_stitching_cost=Decimal("450"),
        base_fabric_metres=Decimal("1.8"),
        reference_body_cm=Decimal("100"),
        sort_order=2,
    ),
    dict(
        slug="dress",
        name="Dress",
        ai_prompt_noun="dress",
        base_price=Decimal("3500"),
        base_stitching_cost=Decimal("600"),
        base_fabric_metres=Decimal("2.6"),
        reference_body_cm=Decimal("88"),
        sort_order=3,
    ),
    dict(
        slug="trousers",
        name="Trousers",
        ai_prompt_noun="tailored trousers",
        base_price=Decimal("3000"),
        base_stitching_cost=Decimal("500"),
        base_fabric_metres=Decimal("1.6"),
        reference_body_cm=Decimal("76"),
        sort_order=4,
    ),
    dict(
        slug="kurta",
        name="Kurta",
        ai_prompt_noun="kurta",
        base_price=Decimal("2600"),
        base_stitching_cost=Decimal("400"),
        base_fabric_metres=Decimal("2.2"),
        reference_body_cm=Decimal("98"),
        sort_order=5,
    ),
    dict(
        slug="saree-blouse",
        name="Saree Blouse",
        ai_prompt_noun="saree blouse",
        base_price=Decimal("1800"),
        base_stitching_cost=Decimal("400"),
        base_fabric_metres=Decimal("1.0"),
        reference_body_cm=Decimal("86"),
        sort_order=6,
    ),
    dict(
        slug="salwar-kameez",
        name="Salwar Kameez",
        ai_prompt_noun="salwar kameez suit",
        base_price=Decimal("4200"),
        base_stitching_cost=Decimal("700"),
        base_fabric_metres=Decimal("3.4"),
        reference_body_cm=Decimal("90"),
        sort_order=7,
    ),
    dict(
        slug="skirt",
        name="Skirt",
        ai_prompt_noun="skirt",
        base_price=Decimal("2100"),
        base_stitching_cost=Decimal("350"),
        base_fabric_metres=Decimal("1.5"),
        reference_body_cm=Decimal("74"),
        sort_order=8,
    ),
]

# field_key, label, letter, min, max, affects_fabric, instructions
MEASUREMENT_FIELDS = {
    "dress": [
        (
            "bust",
            "Bust",
            "A",
            76,
            150,
            True,
            "Wrap the tape around the fullest part of your chest, under your arms and across your shoulder blades. Keep the tape horizontal all the way around.",
        ),
        (
            "waist",
            "Waist",
            "B",
            58,
            135,
            False,
            "Measure around your natural waist, approximately 2-4 cm above your belly button.",
        ),
        (
            "hip",
            "Hip",
            "C",
            82,
            160,
            False,
            "Measure around the fullest part of your hips and seat, approximately 18-23 cm below your natural waist.",
        ),
        (
            "shoulder",
            "Shoulder width",
            "D",
            32,
            56,
            False,
            "Measure straight across the back from the tip of your right shoulder bone to the tip of your left shoulder bone.",
        ),
        (
            "total_length",
            "Total dress length",
            "E",
            80,
            165,
            False,
            "Measure from the highest point of your shoulder straight down to where you want the hem to fall.",
        ),
        (
            "sleeve",
            "Sleeve length",
            "F",
            0,
            72,
            False,
            "Measure from the shoulder seam point along the outside of your arm to where you want the sleeve to end.",
        ),
        (
            "neckline_depth",
            "Neckline depth",
            "G",
            2,
            25,
            False,
            "Measure from the highest shoulder point straight down to the lowest point of the neckline opening.",
        ),
    ],
    "tshirt": [
        (
            "chest",
            "Chest circumference",
            "A",
            76,
            150,
            True,
            "Wrap tape around the fullest part of your chest, under your arms.",
        ),
        (
            "shoulder",
            "Shoulder width",
            "B",
            32,
            56,
            False,
            "Measure from shoulder bone tip to tip across the back.",
        ),
        (
            "total_length",
            "Body length",
            "C",
            55,
            90,
            False,
            "From the highest shoulder point straight down to where you want the hem.",
        ),
        (
            "sleeve",
            "Sleeve length",
            "D",
            0,
            70,
            False,
            "From the shoulder seam point along the outside of your arm to where the sleeve ends.",
        ),
    ],
    "shirt": [
        (
            "chest",
            "Chest circumference",
            "A",
            76,
            150,
            True,
            "Around the fullest part of your chest, tape horizontal under the arms and across the shoulder blades.",
        ),
        (
            "shoulder",
            "Shoulder width",
            "B",
            32,
            56,
            False,
            "Across the back from shoulder bone tip to tip.",
        ),
        (
            "total_length",
            "Shirt length",
            "C",
            60,
            95,
            False,
            "High point of shoulder at back of neck to where the hem falls.",
        ),
        (
            "sleeve",
            "Sleeve length",
            "D",
            15,
            72,
            False,
            "Shoulder seam to wrist bone with your arm slightly bent at 90 degrees.",
        ),
        (
            "collar",
            "Collar circumference",
            "E",
            32,
            52,
            False,
            "Around the base of your neck where the collar sits.",
        ),
        ("cuff", "Cuff circumference", "F", 18, 32, False, "Around your wrist bone."),
    ],
    "skirt": [
        (
            "waist",
            "Waist circumference",
            "A",
            58,
            135,
            True,
            "Measure around your body at the exact point where the waistband will sit.",
        ),
        (
            "hip",
            "Hip circumference",
            "B",
            82,
            160,
            False,
            "Around the fullest part of your hips and seat, approximately 18-23 cm below your natural waist.",
        ),
        (
            "total_length",
            "Skirt length",
            "C",
            30,
            120,
            False,
            "From the top of the waistband straight down to where you want the hem.",
        ),
        (
            "hem",
            "Hem circumference",
            "D",
            50,
            300,
            False,
            "For pencil and straight-cut skirts only, measure around your hips at the level where the hem will sit.",
        ),
    ],
    "trousers": [
        (
            "waist",
            "Waist circumference",
            "A",
            58,
            135,
            True,
            "Measure where the waistband will sit.",
        ),
        (
            "hip",
            "Hip circumference",
            "B",
            82,
            160,
            False,
            "Around the fullest part of your hips and seat.",
        ),
        (
            "inseam",
            "Inseam length",
            "C",
            60,
            95,
            False,
            "From the crotch seam along the inside of the leg to your ankle bone.",
        ),
        (
            "outseam",
            "Outseam length",
            "D",
            85,
            125,
            False,
            "From the top of the waistband down the outside of the leg to the hem.",
        ),
        (
            "thigh",
            "Thigh circumference",
            "E",
            42,
            90,
            False,
            "Around the fullest part of your upper thigh, approximately 3 cm below the crotch.",
        ),
        (
            "knee",
            "Knee circumference",
            "F",
            30,
            55,
            False,
            "Around the knee cap, taken with the leg slightly bent.",
        ),
        ("leg_opening", "Leg opening", "G", 28, 70, False, "Around the hem."),
    ],
    "kurta": [
        (
            "chest",
            "Chest circumference",
            "A",
            76,
            150,
            True,
            "Around the fullest part of your chest, under your arms.",
        ),
        (
            "shoulder",
            "Shoulder width",
            "B",
            32,
            56,
            False,
            "Across the back from shoulder bone tip to tip.",
        ),
        (
            "total_length",
            "Kurta length",
            "C",
            70,
            130,
            False,
            "From the shoulder down to where you want the hem — typically knee-length or below.",
        ),
        ("sleeve", "Sleeve length", "D", 15, 72, False, "Shoulder seam to wrist."),
    ],
    "saree-blouse": [
        ("bust", "Bust", "A", 76, 150, True, "Around the fullest part of your chest."),
        (
            "waist",
            "Waist",
            "B",
            58,
            135,
            False,
            "Around your natural waist, at the blouse hem line.",
        ),
        ("shoulder", "Shoulder width", "C", 32, 56, False, "Shoulder bone tip to tip."),
        (
            "sleeve",
            "Sleeve length",
            "D",
            0,
            40,
            False,
            "Shoulder seam to where the sleeve ends — many blouses use a short sleeve.",
        ),
    ],
    "salwar-kameez": [
        ("bust", "Bust", "A", 76, 150, True, "Around the fullest part of your chest."),
        ("waist", "Waist", "B", 58, 135, False, "Around your natural waist."),
        ("hip", "Hip", "C", 82, 160, False, "Around the fullest part of your hips."),
        (
            "kameez_length",
            "Kameez length",
            "D",
            80,
            135,
            False,
            "Shoulder to where the kameez hem falls.",
        ),
        (
            "shalwar_length",
            "Shalwar length",
            "E",
            85,
            115,
            False,
            "Waist to ankle for the trouser portion.",
        ),
    ],
}

OPTION_GROUPS = {
    "fit": [
        ("slim_fit", "Slim fit", "close-fitting silhouette", 0, 1.00),
        ("regular_fit", "Regular fit", "regular fit", 0, 1.05),
        ("oversized", "Oversized", "oversized loose fit", 0, 1.15),
        ("fitted", "Fitted", "fitted silhouette", 100, 1.02),
        ("flowy", "Flowy", "flowing loose drape", 150, 1.20),
    ],
    "neckline": [
        ("v_neck", "V-neck", "V-neck", 0, 1.00),
        ("round_neck", "Round neck", "round neckline", 0, 1.00),
        ("square_neck", "Square neck", "square neckline", 50, 1.00),
        ("off_shoulder", "Off-shoulder", "off-shoulder neckline", 200, 1.05),
        ("collar", "Collar", "collared neckline", 150, 1.05),
        ("halter", "Halter", "halter neckline", 200, 1.03),
    ],
    "sleeve": [
        ("sleeveless", "Sleeveless", "sleeveless", 0, 0.90),
        ("short_sleeve", "Short sleeve", "short sleeves", 0, 1.00),
        ("three_quarter_sleeve", "3/4 sleeve", "three-quarter length sleeves", 100, 1.08),
        ("long_sleeve", "Long sleeve", "long sleeves", 150, 1.15),
        ("puffed_sleeve", "Puffed sleeve", "puffed sleeves", 300, 1.20),
        ("bell_sleeve", "Bell sleeve", "flowing bell sleeves", 350, 1.22),
    ],
    "pattern": [
        ("plain", "Plain / solid", "plain solid colour", 0, 1.00),
        ("floral", "Floral", "floral print", 200, 1.00),
        ("striped", "Striped", "striped pattern", 150, 1.00),
        ("embroidered", "Embroidered", "detailed embroidery", 600, 1.05),
        ("lace_trim", "Lace trim", "delicate lace trim", 400, 1.03),
        ("pockets", "Pockets", "functional pockets", 150, 1.05),
        ("front_buttons", "Front buttons", "front button placket", 100, 1.02),
        ("side_zip", "Side zip", "concealed side zip", 100, 1.00),
    ],
}

MATERIALS = [
    dict(
        slug="cotton",
        name="Cotton",
        cost_per_metre=Decimal("650"),
        stock_metres=Decimal("120"),
        low_stock_threshold=Decimal("20"),
        swatch_css="#f5ede0",
        ai_prompt_term="cotton",
    ),
    dict(
        slug="linen",
        name="Linen",
        cost_per_metre=Decimal("850"),
        stock_metres=Decimal("80"),
        low_stock_threshold=Decimal("20"),
        swatch_css="#e8ddd0",
        ai_prompt_term="matte slubby linen",
    ),
    dict(
        slug="silk",
        name="Silk",
        cost_per_metre=Decimal("1800"),
        stock_metres=Decimal("2"),
        low_stock_threshold=Decimal("10"),
        swatch_css="linear-gradient(135deg,#e8ddf0,#d4c8e8)",
        ai_prompt_term="lustrous draping silk",
    ),
    dict(
        slug="chiffon",
        name="Chiffon",
        cost_per_metre=Decimal("950"),
        stock_metres=Decimal("45"),
        low_stock_threshold=Decimal("15"),
        swatch_css="linear-gradient(135deg,#f0ece8,#e4dcd4)",
        ai_prompt_term="sheer flowing chiffon",
    ),
    dict(
        slug="satin",
        name="Satin",
        cost_per_metre=Decimal("1100"),
        stock_metres=Decimal("60"),
        low_stock_threshold=Decimal("15"),
        swatch_css="linear-gradient(135deg,#dce8f0,#c8d8e8)",
        ai_prompt_term="glossy satin",
    ),
    dict(
        slug="denim",
        name="Denim",
        cost_per_metre=Decimal("900"),
        stock_metres=Decimal("70"),
        low_stock_threshold=Decimal("20"),
        swatch_css="linear-gradient(135deg,#d8e0d8,#c4d0c4)",
        ai_prompt_term="sturdy denim twill",
    ),
    dict(
        slug="velvet",
        name="Velvet",
        cost_per_metre=Decimal("1600"),
        stock_metres=Decimal("30"),
        low_stock_threshold=Decimal("15"),
        swatch_css="linear-gradient(135deg,#f0e4e8,#e4d0d4)",
        ai_prompt_term="plush velvet",
    ),
]

COLORS = [
    ("Ivory", "#F5F0E8", "ivory"),
    ("Burgundy", "#6E2C3E", "deep burgundy"),
    ("Deep Blue", "#1F3A5F", "deep navy blue"),
    ("Blush", "#E8C4C4", "soft blush pink"),
    ("Charcoal", "#36373A", "charcoal grey"),
    ("Sage", "#8A9A7B", "muted sage green"),
]

APP_SETTINGS = [
    (
        "delivery_fee",
        "350",
        "Delivery fee",
        "Flat delivery fee applied when the order subtotal is below the free-delivery threshold.",
    ),
    (
        "free_delivery_threshold",
        "15000",
        "Free delivery threshold",
        "Order subtotal (LKR) above which delivery is free.",
    ),
    (
        "size_factor_k",
        "0.60",
        "Size factor sensitivity",
        "How strongly fabric requirement scales with body measurement deviation from the reference size.",
    ),
    (
        "size_factor_min",
        "0.85",
        "Size factor minimum",
        "Lower clamp on the fabric size multiplier.",
    ),
    (
        "size_factor_max",
        "1.40",
        "Size factor maximum",
        "Upper clamp on the fabric size multiplier.",
    ),
]

STATUS_FLOW = ["received", "fabric_cut", "stitching", "qc", "dispatched"]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(ClothType).count() > 0:
            print("Already seeded (ClothType rows exist) — skipping. Delete the DB to reseed.")
            return

        # --- Cloth types + measurement fields ---
        cloth_type_by_slug = {}
        for ct_data in CLOTH_TYPES:
            ct = ClothType(**ct_data)
            db.add(ct)
            db.flush()
            cloth_type_by_slug[ct.slug] = ct
            for i, (key, label, letter, lo, hi, affects_fabric, instructions) in enumerate(
                MEASUREMENT_FIELDS.get(ct.slug, [])
            ):
                db.add(
                    MeasurementField(
                        cloth_type_id=ct.id,
                        field_key=key,
                        label=label,
                        letter=letter,
                        min_value=Decimal(lo),
                        max_value=Decimal(hi),
                        affects_fabric=affects_fabric,
                        instructions=instructions,
                        sort_order=i,
                    )
                )
        db.flush()
        print(f"Seeded {len(CLOTH_TYPES)} cloth types with measurement fields.")

        # --- Design option groups + options (apply to every cloth type: cloth_type_id=None) ---
        for group_code, options in OPTION_GROUPS.items():
            group = DesignOptionGroup(
                cloth_type_id=None,
                code=group_code,
                label=group_code.replace("_", " ").title(),
                selection_type="single",
            )
            db.add(group)
            db.flush()
            for i, (code, label, prompt_term, stitch_premium, fabric_mult) in enumerate(options):
                db.add(
                    DesignOption(
                        group_id=group.id,
                        code=code,
                        label=label,
                        ai_prompt_term=prompt_term,
                        stitching_premium=Decimal(stitch_premium),
                        fabric_multiplier=Decimal(str(fabric_mult)),
                        sort_order=i,
                    )
                )
        db.flush()
        print(f"Seeded {len(OPTION_GROUPS)} design option groups.")

        # --- Materials + colors ---
        for mat_data in MATERIALS:
            mat = Material(**mat_data)
            db.add(mat)
            db.flush()
            # Stock is held per colourway. Split the material's total across its
            # colours so the seeded figures stay consistent with each other, and
            # vary it a little so the inventory screen shows a realistic spread
            # rather than six identical bars.
            per_colour = Decimal(str(mat.stock_metres)) / len(COLORS)
            for index, (name, hex_code, prompt_term) in enumerate(COLORS):
                skew = Decimal("1.4") if index == 0 else (Decimal("0.4") if index == 1 else Decimal("1"))
                db.add(
                    MaterialColor(
                        material_id=mat.id,
                        name=name,
                        hex_code=hex_code,
                        ai_prompt_term=prompt_term,
                        stock_metres=(per_colour * skew).quantize(Decimal("0.01")),
                        low_stock_threshold=Decimal(str(mat.low_stock_threshold)) / len(COLORS),
                    )
                )
        db.flush()
        print(f"Seeded {len(MATERIALS)} materials, deliberately including Silk at low stock (2m).")

        # --- App settings ---
        for key, value, label, description in APP_SETTINGS:
            db.add(AppSetting(key=key, value=value, label=label, description=description))

        # --- Admin + demo users ---
        from app.core.config import settings as app_settings

        admin = User(
            first_name="Admin",
            last_name="User",
            email=app_settings.admin_email,
            password_hash=get_password_hash(app_settings.admin_password),
            role="admin",
        )
        demo = User(
            first_name="Demo",
            last_name="Customer",
            email=app_settings.demo_email,
            password_hash=get_password_hash(app_settings.demo_password),
            role="customer",
        )
        db.add_all([admin, demo])
        db.flush()
        print(f"Seeded admin ({app_settings.admin_email}) and demo customer ({app_settings.demo_email}).")

        # --- Synthetic historical orders for non-empty analytics ---
        cloth_types = list(cloth_type_by_slug.values())
        rng = random.Random(42)
        now = datetime.now(UTC)
        # Real materials rather than the MATERIALS spec dicts, so the seeded
        # orders carry usable foreign keys. Without them the reorder resolver
        # cannot find the fabric and reports every historical order as
        # discontinued — which is exactly what a demo would run into.
        seeded_materials = db.query(Material).all()

        for i in range(15):
            ct = rng.choice(cloth_types)
            chosen_material = rng.choice(seeded_materials)
            chosen_colour = rng.choice(chosen_material.colors) if chosen_material.colors else None
            chosen_options = [
                option
                for group in db.query(DesignOptionGroup)
                .filter(DesignOptionGroup.cloth_type_id.is_(None))
                .all()
                for option in ([rng.choice(group.options)] if group.options else [])
            ][:2]
            days_ago = rng.randint(1, 90)
            created = now - timedelta(days=days_ago)
            n_stages = rng.randint(1, len(STATUS_FLOW))
            final_status = STATUS_FLOW[n_stages - 1]
            price = ct.base_price + Decimal(rng.randint(-300, 1500))

            order = Order(
                order_number=f"TC-{created.year}-{100000 + i}",
                user_id=demo.id if i % 3 == 0 else None,
                guest_email=None if i % 3 == 0 else "guest@example.com",
                cloth_type_id=ct.id,
                material_id=chosen_material.id,
                material_color_id=chosen_colour.id if chosen_colour else None,
                cloth_type_name=ct.name,
                material_name=chosen_material.name,
                color_name=chosen_colour.name if chosen_colour else None,
                color_hex=chosen_colour.hex_code if chosen_colour else None,
                fabric_metres_used=ct.base_fabric_metres,
                price_base=ct.base_price,
                price_stitching=ct.base_stitching_cost,
                price_material=price - ct.base_price - ct.base_stitching_cost,
                price_delivery=Decimal("0") if price > 15000 else Decimal("350"),
                price_total=price,
                price_breakdown=[],
                design_options_snapshot=[{"code": o.code, "label": o.label} for o in chosen_options],
                measurements_snapshot={f.field_key: 90 for f in ct.measurement_fields[:3]},
                status=final_status,
                payment_status="paid",
                created_at=created,
            )
            db.add(order)
            db.flush()
            for stage_idx in range(n_stages):
                db.add(
                    OrderStatusHistory(
                        order_id=order.id,
                        from_status=STATUS_FLOW[stage_idx - 1] if stage_idx > 0 else None,
                        to_status=STATUS_FLOW[stage_idx],
                        created_at=created + timedelta(days=stage_idx),
                    )
                )
        print("Seeded 15 synthetic historical orders across the last 90 days.")

        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
