"""The 100 Senate seats: every state holds two of the three classes.

A seat is (state, class). Class I seats are up in years where year % 6 == 2 (2018, 2024), class II where year % 6 == 4
(2020, 2026) and class III where year % 6 == 0 (2016, 2022). A special election fills the remainder of a term in a
seat whose class is not regularly up that year.
"""

from __future__ import annotations

from dataclasses import dataclass

STATES: dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}

CLASS_I = frozenset(
    [
        "AZ",
        "CA",
        "CT",
        "DE",
        "FL",
        "HI",
        "IN",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NJ",
        "NM",
        "NY",
        "ND",
        "OH",
        "PA",
        "RI",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
    ]
)
CLASS_II = frozenset(
    [
        "AL",
        "AK",
        "AR",
        "CO",
        "DE",
        "GA",
        "ID",
        "IL",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MA",
        "MI",
        "MN",
        "MS",
        "MT",
        "NE",
        "NH",
        "NJ",
        "NM",
        "NC",
        "OK",
        "OR",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "VA",
        "WV",
        "WY",
    ]
)
# Every state has exactly two classes, so class III is every state that lacks class I or class II.
CLASS_III = frozenset(s for s in STATES if not (s in CLASS_I and s in CLASS_II))
MEMBERS: dict[int, frozenset[str]] = {1: CLASS_I, 2: CLASS_II, 3: CLASS_III}


@dataclass(frozen=True, slots=True)
class Seat:
    state: str
    senate_class: int

    @property
    def seat_id(self) -> str:
        return f"{self.state}-{self.senate_class}"


def seats() -> list[Seat]:
    return [Seat(s, c) for s in STATES for c in (1, 2, 3) if s in MEMBERS[c]]


def classes_of(state: str) -> tuple[int, int]:
    a, b = (c for c in (1, 2, 3) if state in MEMBERS[c])
    return a, b


def regular_class(year: int) -> int | None:
    """Class regularly up in an even year; None in odd years."""
    if year % 2:
        return None
    return {2: 1, 4: 2, 0: 3}[year % 6]


def class_for_contest(state: str, year: int, special: bool) -> int | None:
    """Seat class a contest filled, when the calendar alone decides it; None when it is ambiguous.

    Regular elections always resolve. A special resolves when the state's other seat is the one regularly up that
    year (e.g. Nebraska 2024: class I regular, so the special was class II). Otherwise the state holds neither or
    the special could be either seat (e.g. Arizona 2020, odd-year specials) and needs an explicit assignment.
    """
    reg = regular_class(year)
    mine = classes_of(state)
    if not special:
        if reg is None or reg not in mine:
            raise ValueError(f"{state} has no class {reg} seat for a regular {year} election")
        return reg
    if reg is not None and reg in mine:
        return next(c for c in mine if c != reg)
    return None


def seat_for(state: str, cycle: int, special: bool, overrides: dict[tuple[str, int, str], int]) -> tuple[str, str]:
    """(seat_id, method) for a Senate contest, using the calendar first and data/special_seats.json second."""
    cls = class_for_contest(state, cycle, special)
    if cls is not None:
        return f"{state}-{cls}", "calendar"
    if (state, cycle, "special") in overrides:
        return f"{state}-{overrides[(state, cycle, 'special')]}", "override"
    raise LookupError(f"{state} {cycle} special: add its seat class to data/special_seats.json")


def seats_up(cycle: int, overrides: dict[tuple[str, int, str], int]) -> list[tuple[str, bool]]:
    """(seat_id, special) for every seat with a scheduled election in a cycle, regular and known specials."""
    reg = regular_class(cycle)
    out = [(f"{s}-{reg}", False) for s in STATES if reg is not None and s in MEMBERS[reg]]
    out += [(f"{s}-{c}", True) for (s, y, _), c in overrides.items() if y == cycle]
    return sorted(out)


assert len(CLASS_I) == 33 and len(CLASS_II) == 33 and len(CLASS_III) == 34, "class membership is wrong"
assert all(sum(s in MEMBERS[c] for c in (1, 2, 3)) == 2 for s in STATES), "each state must hold exactly two classes"
