import pytest

from midterms.seats import class_for_contest, regular_class, seat_for, seats, seats_up


def test_hundred_seats_two_per_state():
    all_seats = seats()
    assert len(all_seats) == 100
    assert len({s.state for s in all_seats}) == 50


@pytest.mark.parametrize(
    ("year", "cls"), [(2018, 1), (2024, 1), (2020, 2), (2026, 2), (2016, 3), (2022, 3), (2021, None)]
)
def test_regular_cycle(year, cls):
    assert regular_class(year) == cls


def test_calendar_resolves_specials_when_the_other_seat_is_up():
    assert class_for_contest("NE", 2024, special=True) == 2  # class I regular that year, so the special was class II
    assert class_for_contest("GA", 2020, special=True) == 3


def test_ambiguous_specials_need_an_override(overrides):
    assert class_for_contest("AZ", 2020, special=True) is None
    assert seat_for("AZ", 2020, True, overrides) == ("AZ-3", "override")
    assert seat_for("OH", 2026, True, overrides) == ("OH-3", "override")


def test_regular_election_for_a_seat_the_state_lacks_is_an_error():
    with pytest.raises(ValueError):
        class_for_contest("AZ", 2020, special=False)


def test_2026_has_35_seats(overrides):
    up = seats_up(2026, overrides)
    assert len(up) == 35
    assert ("FL-3", True) in up and ("OH-3", True) in up
