"""Step 2's design tags: which ones each garment offers.

Previously all four groups — Fit, Neckline, Sleeve, Pattern — were seeded with
`cloth_type_id = None`, so every garment showed all of them. A customer
designing trousers was asked to pick a neckline and a sleeve length, which the
prompt builder then dutifully fed to the image model.

Two kinds of group, and the split is the point:

  - **Global** (`GLOBAL_GROUPS`) — genuinely applies to anything with fabric in
    it. Fit and pattern qualify; a neckline does not.
  - **Per garment** (`CLOTH_TYPE_GROUPS`, keyed by cloth-type slug) — the
    decisions a tailor actually has to make for *that* garment. Trousers get a
    leg cut and a rise; a saree blouse gets a back style; a skirt gets neither
    a neckline nor a sleeve.

The vocabulary is deliberately garment-specific even where the group name
repeats: a t-shirt neckline offers a crew and a henley, a dress neckline offers
a sweetheart and a halter. Sharing one neckline list across both was how the
irrelevant options got there in the first place.

Each option is `(code, label, ai_prompt_term, stitching_premium, fabric_multiplier)`.
`ai_prompt_term` is what reaches the diffusion prompt, kept separate from the
label so the UI can be reworded without changing what gets generated.
"""

# Applied to every cloth type. These two lists are unchanged from the original
# seed on purpose: the migration that scopes the other groups leaves them
# alone, so editing them here would make a freshly seeded database disagree
# with a migrated one.
GLOBAL_GROUPS = {
    "fit": (
        "Fit",
        [
            ("slim_fit", "Slim fit", "close-fitting silhouette", 0, 1.00),
            ("regular_fit", "Regular fit", "regular fit", 0, 1.05),
            ("oversized", "Oversized", "oversized loose fit", 0, 1.15),
            ("fitted", "Fitted", "fitted silhouette", 100, 1.02),
            ("flowy", "Flowy", "flowing loose drape", 150, 1.20),
        ],
    ),
    "pattern": (
        "Pattern",
        [
            ("plain", "Plain / solid", "plain solid colour", 0, 1.00),
            ("floral", "Floral", "floral print", 200, 1.00),
            ("striped", "Striped", "striped pattern", 150, 1.00),
            ("embroidered", "Embroidered", "detailed embroidery", 600, 1.05),
            ("lace_trim", "Lace trim", "delicate lace trim", 400, 1.03),
            ("pockets", "Pockets", "functional pockets", 150, 1.05),
            ("front_buttons", "Front buttons", "front button placket", 100, 1.02),
            ("side_zip", "Side zip", "concealed side zip", 100, 1.00),
        ],
    ),
}

# Keyed by ClothType.slug. Order here is the order shown in step 2.
CLOTH_TYPE_GROUPS = {
    "blouse": [
        (
            "neckline",
            "Neckline",
            [
                ("v_neck", "V-neck", "V-neck", 0, 1.00),
                ("round_neck", "Round neck", "round neckline", 0, 1.00),
                ("square_neck", "Square neck", "square neckline", 50, 1.00),
                ("boat_neck", "Boat neck", "boat neckline", 50, 1.00),
                ("sweetheart", "Sweetheart", "sweetheart neckline", 150, 1.00),
                ("collar", "Collar", "collared neckline", 150, 1.05),
            ],
        ),
        (
            "sleeve",
            "Sleeve",
            [
                ("sleeveless", "Sleeveless", "sleeveless", 0, 0.90),
                ("cap_sleeve", "Cap sleeve", "cap sleeves", 50, 0.95),
                ("short_sleeve", "Short sleeve", "short sleeves", 0, 1.00),
                ("three_quarter_sleeve", "3/4 sleeve", "three-quarter length sleeves", 100, 1.08),
                ("long_sleeve", "Long sleeve", "long sleeves", 150, 1.15),
                ("puffed_sleeve", "Puffed sleeve", "puffed sleeves", 300, 1.20),
            ],
        ),
    ],
    "tshirt": [
        (
            "neckline",
            "Neckline",
            [
                ("crew_neck", "Crew neck", "crew neckline", 0, 1.00),
                ("v_neck", "V-neck", "V-neck", 0, 1.00),
                ("scoop_neck", "Scoop neck", "scoop neckline", 50, 1.00),
                ("henley", "Henley", "henley placket neckline", 150, 1.02),
                ("polo_collar", "Polo collar", "polo collar", 200, 1.03),
            ],
        ),
        (
            "sleeve",
            "Sleeve",
            [
                ("sleeveless", "Sleeveless", "sleeveless", 0, 0.90),
                ("short_sleeve", "Short sleeve", "short sleeves", 0, 1.00),
                ("three_quarter_sleeve", "3/4 sleeve", "three-quarter length sleeves", 100, 1.08),
                ("long_sleeve", "Long sleeve", "long sleeves", 150, 1.15),
            ],
        ),
    ],
    "shirt": [
        (
            "collar",
            "Collar",
            [
                ("classic_collar", "Classic collar", "classic point collar", 0, 1.00),
                ("button_down", "Button-down", "button-down collar", 100, 1.01),
                ("mandarin_collar", "Mandarin collar", "mandarin band collar", 150, 1.00),
                ("spread_collar", "Spread collar", "cutaway spread collar", 150, 1.02),
                ("no_collar", "Collarless", "collarless round neckline", 0, 0.98),
            ],
        ),
        (
            "sleeve",
            "Sleeve",
            [
                ("short_sleeve", "Short sleeve", "short sleeves", 0, 1.00),
                ("long_sleeve", "Long sleeve", "long sleeves", 150, 1.15),
                ("roll_up_sleeve", "Roll-up sleeve", "long sleeves with roll-up tabs", 200, 1.16),
            ],
        ),
        (
            "cuff",
            "Cuff",
            [
                ("barrel_cuff", "Barrel cuff", "single barrel cuffs", 0, 1.00),
                ("french_cuff", "French cuff", "double french cuffs", 250, 1.05),
                ("no_cuff", "No cuff", "plain hemmed sleeve ends", 0, 1.00),
            ],
        ),
    ],
    "dress": [
        (
            "neckline",
            "Neckline",
            [
                ("v_neck", "V-neck", "V-neck", 0, 1.00),
                ("round_neck", "Round neck", "round neckline", 0, 1.00),
                ("square_neck", "Square neck", "square neckline", 50, 1.00),
                ("sweetheart", "Sweetheart", "sweetheart neckline", 150, 1.00),
                ("off_shoulder", "Off-shoulder", "off-shoulder neckline", 200, 1.05),
                ("halter", "Halter", "halter neckline", 200, 1.03),
            ],
        ),
        (
            "sleeve",
            "Sleeve",
            [
                ("sleeveless", "Sleeveless", "sleeveless", 0, 0.90),
                ("cap_sleeve", "Cap sleeve", "cap sleeves", 50, 0.95),
                ("short_sleeve", "Short sleeve", "short sleeves", 0, 1.00),
                ("three_quarter_sleeve", "3/4 sleeve", "three-quarter length sleeves", 100, 1.08),
                ("long_sleeve", "Long sleeve", "long sleeves", 150, 1.15),
                ("puffed_sleeve", "Puffed sleeve", "puffed sleeves", 300, 1.20),
                ("bell_sleeve", "Bell sleeve", "flowing bell sleeves", 350, 1.22),
            ],
        ),
        (
            "length",
            "Length",
            [
                ("mini", "Mini", "mini length above the knee", 0, 0.85),
                ("knee_length", "Knee length", "knee-length", 0, 1.00),
                ("midi", "Midi", "midi length below the knee", 100, 1.15),
                ("maxi", "Maxi", "full-length maxi", 200, 1.35),
            ],
        ),
    ],
    "trousers": [
        (
            "leg",
            "Leg cut",
            [
                ("straight_leg", "Straight leg", "straight leg", 0, 1.00),
                ("tapered", "Tapered", "tapered leg narrowing to the ankle", 100, 0.97),
                ("wide_leg", "Wide leg", "wide leg", 150, 1.20),
                ("bootcut", "Bootcut", "bootcut flaring below the knee", 150, 1.10),
                ("palazzo", "Palazzo", "flowing palazzo leg", 200, 1.30),
            ],
        ),
        (
            "rise",
            "Rise",
            [
                ("low_rise", "Low rise", "low rise waist", 0, 0.98),
                ("mid_rise", "Mid rise", "mid rise waist", 0, 1.00),
                ("high_rise", "High rise", "high rise waist", 50, 1.03),
            ],
        ),
        (
            "waistband",
            "Waistband",
            [
                ("flat_waistband", "Flat front", "flat front waistband", 0, 1.00),
                ("pleated_waist", "Pleated", "pleated front waistband", 150, 1.08),
                ("elasticated", "Elasticated", "elasticated waistband", 50, 1.00),
                ("drawstring", "Drawstring", "drawstring waist", 100, 1.01),
            ],
        ),
    ],
    "kurta": [
        (
            "neckline",
            "Neckline",
            [
                ("round_neck", "Round neck", "round neckline", 0, 1.00),
                ("mandarin_collar", "Mandarin collar", "mandarin band collar", 150, 1.00),
                ("v_neck", "V-neck", "V-neck", 0, 1.00),
                ("keyhole_neck", "Keyhole", "keyhole neckline", 150, 1.00),
                ("boat_neck", "Boat neck", "boat neckline", 50, 1.00),
            ],
        ),
        (
            "sleeve",
            "Sleeve",
            [
                ("sleeveless", "Sleeveless", "sleeveless", 0, 0.90),
                ("short_sleeve", "Short sleeve", "short sleeves", 0, 1.00),
                ("three_quarter_sleeve", "3/4 sleeve", "three-quarter length sleeves", 100, 1.08),
                ("long_sleeve", "Long sleeve", "long sleeves", 150, 1.15),
            ],
        ),
        (
            "length",
            "Length",
            [
                ("hip_length", "Hip length", "hip-length kurta", 0, 0.90),
                ("knee_length", "Knee length", "knee-length kurta", 0, 1.00),
                ("calf_length", "Calf length", "calf-length kurta", 150, 1.18),
                ("ankle_length", "Ankle length", "ankle-length kurta", 250, 1.32),
            ],
        ),
    ],
    "saree-blouse": [
        (
            "neckline",
            "Neckline",
            [
                ("round_neck", "Round neck", "round neckline", 0, 1.00),
                ("v_neck", "V-neck", "V-neck", 0, 1.00),
                ("sweetheart", "Sweetheart", "sweetheart neckline", 150, 1.00),
                ("boat_neck", "Boat neck", "boat neckline", 50, 1.00),
                ("high_neck", "High neck", "high closed neckline", 150, 1.02),
            ],
        ),
        (
            "sleeve",
            "Sleeve",
            [
                ("sleeveless", "Sleeveless", "sleeveless", 0, 0.90),
                ("cap_sleeve", "Cap sleeve", "cap sleeves", 50, 0.95),
                ("short_sleeve", "Short sleeve", "short sleeves", 0, 1.00),
                ("elbow_sleeve", "Elbow sleeve", "elbow-length sleeves", 100, 1.06),
                ("three_quarter_sleeve", "3/4 sleeve", "three-quarter length sleeves", 100, 1.08),
            ],
        ),
        (
            "back",
            "Back style",
            [
                ("round_back", "Round back", "plain round back", 0, 1.00),
                ("deep_back", "Deep back", "deep scooped back", 100, 0.98),
                ("keyhole_back", "Keyhole back", "keyhole cut-out back", 200, 1.00),
                ("tie_back", "Tie back", "tie-back fastening", 200, 1.02),
                ("dori_back", "Dori back", "dori tasselled back", 300, 1.03),
            ],
        ),
    ],
    "salwar-kameez": [
        (
            "neckline",
            "Neckline",
            [
                ("round_neck", "Round neck", "round neckline", 0, 1.00),
                ("v_neck", "V-neck", "V-neck", 0, 1.00),
                ("mandarin_collar", "Mandarin collar", "mandarin band collar", 150, 1.00),
                ("boat_neck", "Boat neck", "boat neckline", 50, 1.00),
                ("keyhole_neck", "Keyhole", "keyhole neckline", 150, 1.00),
            ],
        ),
        (
            "sleeve",
            "Sleeve",
            [
                ("sleeveless", "Sleeveless", "sleeveless", 0, 0.90),
                ("short_sleeve", "Short sleeve", "short sleeves", 0, 1.00),
                ("three_quarter_sleeve", "3/4 sleeve", "three-quarter length sleeves", 100, 1.08),
                ("long_sleeve", "Long sleeve", "long sleeves", 150, 1.15),
            ],
        ),
        (
            "kameez_length",
            "Kameez length",
            [
                ("short_kameez", "Short", "short kameez to the hip", 0, 0.90),
                ("knee_length", "Knee length", "knee-length kameez", 0, 1.00),
                ("calf_length", "Calf length", "calf-length kameez", 150, 1.18),
                ("ankle_length", "Ankle length", "ankle-length kameez", 250, 1.30),
            ],
        ),
        (
            "salwar_style",
            "Salwar style",
            [
                ("churidar", "Churidar", "fitted churidar bottoms", 200, 1.10),
                ("patiala", "Patiala", "pleated patiala bottoms", 250, 1.35),
                ("straight_salwar", "Straight salwar", "straight salwar bottoms", 0, 1.00),
                ("palazzo", "Palazzo", "flowing palazzo bottoms", 200, 1.28),
            ],
        ),
    ],
    "skirt": [
        (
            "shape",
            "Shape",
            [
                ("a_line", "A-line", "A-line skirt", 0, 1.00),
                ("pencil", "Pencil", "fitted pencil skirt", 100, 0.92),
                ("pleated", "Pleated", "knife-pleated skirt", 250, 1.40),
                ("wrap", "Wrap", "wrap skirt", 150, 1.12),
                ("flared", "Flared", "flared circle skirt", 200, 1.45),
            ],
        ),
        (
            "length",
            "Length",
            [
                ("mini", "Mini", "mini length above the knee", 0, 0.80),
                ("knee_length", "Knee length", "knee-length", 0, 1.00),
                ("midi", "Midi", "midi length below the knee", 100, 1.20),
                ("maxi", "Maxi", "full-length maxi", 200, 1.45),
            ],
        ),
        (
            "waistband",
            "Waistband",
            [
                ("flat_waistband", "Flat waistband", "flat fitted waistband", 0, 1.00),
                ("elasticated", "Elasticated", "elasticated waistband", 50, 1.00),
                ("paperbag", "Paperbag", "gathered paperbag waist", 200, 1.10),
                ("drawstring", "Drawstring", "drawstring waist", 100, 1.01),
            ],
        ),
    ],
}
