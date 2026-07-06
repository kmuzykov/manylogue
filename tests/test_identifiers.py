from manylogue.util import pick_unique_name


def test_pick_unique_name_returns_base_when_free() -> None:
    assert pick_unique_name("Claude", {"Human"}) == "Claude"


def test_pick_unique_name_numbers_collisions() -> None:
    assert pick_unique_name("Claude", {"Human", "Claude"}) == "Claude_2"
    assert pick_unique_name(
        "Claude", {"Human", "Claude", "Claude_2"}) == "Claude_3"


def test_pick_unique_name_human_is_reserved() -> None:
    assert pick_unique_name("Human", {"Human"}) == "Human_2"
