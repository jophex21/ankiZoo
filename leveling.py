from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from . import config

# Cumulative XP grows quadratically: level L costs `base * L` additional XP
# over level L-1. With base=4 and 1 XP per correct card, ~5,000 correct
# cards lands you around level 50 (cumulative(50) = 4 * 50*51/2 = 5,100).
RANKS: List[Tuple[int, str]] = [
    (0, "Trainee"),
    (5, "Keeper"),
    (10, "Senior Keeper"),
    (20, "Curator"),
    (30, "Zoo Director"),
    (40, "Master Naturalist"),
]


def xp_for_level(level: int, base: int) -> int:
    """Additional XP required to go from `level - 1` to `level`."""
    return base * level


def collapse_xp(total_xp: int, base: int) -> Tuple[int, int, int]:
    """Return (level, xp_into_level, xp_to_next_level) for a given total XP."""
    level = 0
    xp_needed = 0
    while True:
        cost = xp_for_level(level + 1, base)
        if total_xp < xp_needed + cost:
            return level, total_xp - xp_needed, cost
        xp_needed += cost
        level += 1


def rank_for_level(level: int) -> str:
    current = RANKS[0][1]
    for min_level, name in RANKS:
        if level >= min_level:
            current = name
        else:
            break
    return current


def get_level_base() -> int:
    return int(config.get_config().get("levelCurveBase", 4))


@dataclass
class Progress:
    level: int
    xp_into: int
    xp_next: int
    percent: int
    rank: str


def get_progress(total_xp: int) -> Progress:
    """Level/XP/rank/percent bundle, computed once from total_xp."""
    level, xp_into, xp_next = collapse_xp(total_xp, get_level_base())
    percent = 0 if xp_next <= 0 else min(100, int(xp_into / xp_next * 100))
    return Progress(level, xp_into, xp_next, percent, rank_for_level(level))
