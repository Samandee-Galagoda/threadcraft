"""Design tags are scoped to the garment they belong on.

The bug this guards: every group was seeded with `cloth_type_id = NULL`, so the
catalogue offered a neckline and a sleeve length to someone designing trousers,
and the prompt builder passed both to the image model.
"""

import pytest

from app.db.design_tags import CLOTH_TYPE_GROUPS, GLOBAL_GROUPS
from app.models.catalog import ClothType, DesignOption, DesignOptionGroup


@pytest.fixture()
def tagged_catalogue(db_session):
    """Two garments, the global groups, and each garment's own."""
    cloth_types = {}
    for slug, name, noun in [
        ("tshirt", "T-shirt", "t-shirt"),
        ("trousers", "Trousers", "trousers"),
    ]:
        cloth_type = ClothType(
            slug=slug,
            name=name,
            base_price=2200,
            base_stitching_cost=300,
            base_fabric_metres=1.4,
            reference_body_cm=96,
            ai_prompt_noun=noun,
        )
        db_session.add(cloth_type)
        db_session.flush()
        cloth_types[slug] = cloth_type

    def add_group(cloth_type_id, code, label, options, sort_order):
        group = DesignOptionGroup(
            cloth_type_id=cloth_type_id,
            code=code,
            label=label,
            selection_type="single",
            sort_order=sort_order,
        )
        db_session.add(group)
        db_session.flush()
        for index, (opt_code, opt_label, term, premium, multiplier) in enumerate(options):
            db_session.add(
                DesignOption(
                    group_id=group.id,
                    code=opt_code,
                    label=opt_label,
                    ai_prompt_term=term,
                    stitching_premium=premium,
                    fabric_multiplier=multiplier,
                    sort_order=index,
                )
            )

    for order, (code, (label, options)) in enumerate(GLOBAL_GROUPS.items()):
        add_group(None, code, label, options, order)

    for slug, cloth_type in cloth_types.items():
        for order, (code, label, options) in enumerate(CLOTH_TYPE_GROUPS[slug]):
            add_group(cloth_type.id, code, label, options, len(GLOBAL_GROUPS) + order)

    db_session.commit()
    return cloth_types


def _groups(client, slug):
    (cloth_type,) = [c for c in client.get("/api/catalog/cloth-types").json() if c["slug"] == slug]
    return {g["code"]: g for g in cloth_type["option_groups"]}


def test_trousers_are_not_asked_for_a_neckline_or_a_sleeve(client, tagged_catalogue):
    codes = _groups(client, "trousers")
    assert "neckline" not in codes
    assert "sleeve" not in codes


def test_trousers_get_the_decisions_that_do_apply(client, tagged_catalogue):
    codes = _groups(client, "trousers")
    assert {"leg", "rise", "waistband"} <= set(codes)


def test_a_tshirt_still_gets_a_neckline_and_a_sleeve(client, tagged_catalogue):
    codes = _groups(client, "tshirt")
    assert "neckline" in codes
    assert "sleeve" in codes
    assert "leg" not in codes


def test_every_garment_keeps_the_universal_groups(client, tagged_catalogue):
    for slug in ("tshirt", "trousers"):
        assert {"fit", "pattern"} <= set(_groups(client, slug))


def test_the_shared_group_name_carries_garment_specific_options(client, tagged_catalogue):
    """A t-shirt neckline offers a henley; a dress neckline offers a halter.
    One shared list is how the irrelevant options arrived in the first place."""
    tshirt_necklines = {o["code"] for o in _groups(client, "tshirt")["neckline"]["options"]}
    assert "henley" in tshirt_necklines
    assert "halter" not in tshirt_necklines


def test_groups_come_back_in_a_defined_order(client, tagged_catalogue):
    """The relationship had no order_by, so this was previously incidental."""
    codes = list(_groups(client, "trousers"))
    assert codes == ["fit", "pattern", "leg", "rise", "waistband"]


def test_a_single_cloth_type_endpoint_scopes_the_same_way(client, tagged_catalogue):
    body = client.get("/api/catalog/cloth-types/trousers").json()
    assert "neckline" not in {g["code"] for g in body["option_groups"]}


# ── the data itself ──────────────────────────────────────────────────────────


def test_no_garment_redefines_a_global_group():
    """A duplicate code would render the group twice in step 2."""
    for slug, groups in CLOTH_TYPE_GROUPS.items():
        clashes = {code for code, _, _ in groups} & set(GLOBAL_GROUPS)
        assert not clashes, f"{slug} redefines {clashes}"


def test_option_codes_are_unique_within_a_group():
    for slug, groups in CLOTH_TYPE_GROUPS.items():
        for code, _, options in groups:
            codes = [option[0] for option in options]
            assert len(codes) == len(set(codes)), f"{slug}/{code} repeats an option"


def test_group_codes_are_unique_within_a_garment():
    """The table's unique constraint is (cloth_type_id, code)."""
    for slug, groups in CLOTH_TYPE_GROUPS.items():
        codes = [code for code, _, _ in groups]
        assert len(codes) == len(set(codes)), f"{slug} repeats a group"


def test_every_option_carries_a_prompt_term_and_sane_pricing():
    everything = [
        (slug, group_code, option)
        for slug, groups in CLOTH_TYPE_GROUPS.items()
        for group_code, _, options in groups
        for option in options
    ] + [
        ("global", group_code, option)
        for group_code, (_, options) in GLOBAL_GROUPS.items()
        for option in options
    ]
    assert everything

    for slug, group_code, (code, label, term, premium, multiplier) in everything:
        where = f"{slug}/{group_code}/{code}"
        assert label.strip(), where
        # Empty prompt terms would silently drop the choice from the image.
        assert term.strip(), where
        assert premium >= 0, where
        # A multiplier outside this range means a garment costing wildly more
        # or less in fabric than its base — always a typo, never intended.
        assert 0.5 <= multiplier <= 2.0, where
