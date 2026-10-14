"""Per-state UI program rules for the 10 demo states.

Values sourced from DOL's annual Comparison of State Unemployment Insurance Laws
and individual state agency websites.  Simplified for the demo.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StateProfile:
    code: str
    name: str
    eta_region: int
    wba_max: int            # maximum weekly benefit amount ($)
    base_period_quarters: int
    work_search_contacts: int  # required employer contacts per week
    waiting_week: bool
    has_pfml: bool
    pfml_max_weekly: int    # 0 if no PFML program


PROFILES: dict[str, StateProfile] = {
    "CA": StateProfile("CA", "California",    6, 450, 4, 3, True,  True,  1620),
    "WA": StateProfile("WA", "Washington",    6, 999, 4, 3, True,  True,  1456),
    "TX": StateProfile("TX", "Texas",         4, 577, 4, 3, False, False, 0),
    "IL": StateProfile("IL", "Illinois",      5, 742, 4, 2, True,  False, 0),
    "OH": StateProfile("OH", "Ohio",          5, 598, 4, 2, True,  False, 0),
    "FL": StateProfile("FL", "Florida",       3, 275, 4, 5, True,  False, 0),
    "GA": StateProfile("GA", "Georgia",       3, 365, 4, 3, False, False, 0),
    "NY": StateProfile("NY", "New York",      1, 504, 4, 3, True,  True,  1151),
    "NJ": StateProfile("NJ", "New Jersey",    1, 830, 4, 3, True,  True,  1025),
    "PA": StateProfile("PA", "Pennsylvania",  2, 612, 4, 2, True,  False, 0),
}

STATE_CODES = list(PROFILES.keys())
