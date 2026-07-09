from __future__ import annotations

import random
from typing import Any, Dict, List

from . import animals as animals_module

# ---------------------------------------------------------------------------
# Loot boxes replace visible quest rewards. Completing a quest grants a box the
# player opens from the Quests tab; opening rolls one reward whose *rarity band*
# drives its border color (grey -> orange) in the CS:GO-style reveal animation.
# ---------------------------------------------------------------------------

RARITY_ORDER: List[str] = ["common", "uncommon", "rare", "epic", "legendary"]
RARITY_COLORS: Dict[str, str] = {
    "common": "#9aa0a6",     # grey
    "uncommon": "#4caf50",   # green
    "rare": "#3f78c9",       # blue
    "epic": "#9b59b6",       # purple
    "legendary": "#e07a2e",  # orange
}
RARITY_LABEL: Dict[str, str] = {
    "common": "Common", "uncommon": "Uncommon", "rare": "Rare",
    "epic": "Epic", "legendary": "Legendary",
}

# Odds a claimed box lands in each band. Animals and high coin values live only
# in the upper bands, so both stay naturally scarce.
RARITY_WEIGHTS: Dict[str, int] = {
    "common": 48, "uncommon": 26, "rare": 15, "epic": 8, "legendary": 3,
}
# Coin payout range per band -- a bigger purse is a rarer drop.
COIN_RANGES: Dict[str, tuple] = {
    "common": (20, 45), "uncommon": (55, 95), "rare": (110, 165),
    "epic": (190, 250), "legendary": (300, 420),
}
# Each band maps 1:1 to the IUCN tier an animal reward may come from, so the
# animal's own conservation rarity always matches its box's band color. Since
# rarer bands are rarer rolls, more-endangered animals are correspondingly rare.
BAND_ANIMAL_TIER: Dict[str, str] = {
    "common": "LC", "uncommon": "NT", "rare": "VU", "epic": "EN", "legendary": "CR",
}
# Chance a band pays out in an animal (when an eligible one exists) rather than
# coins. Rises with rarity but stays a minority so coins remain the norm.
ANIMAL_CHANCE: Dict[str, float] = {
    "common": 0.08, "uncommon": 0.15, "rare": 0.25, "epic": 0.40, "legendary": 0.55,
}
# Epic boxes may instead award skill points (checked before the animal/coins roll).
EPIC_SKILL_CHANCE = 0.35
EPIC_SKILL_RANGE = (1, 2)


def _weighted_band() -> str:
    keys = list(RARITY_WEIGHTS)
    return random.choices(keys, weights=[RARITY_WEIGHTS[k] for k in keys], k=1)[0]


def _eligible_animals(state, tier: str) -> List[Dict[str, Any]]:
    """Animals the player has unlocked (skill tree) but not yet owned (bought),
    restricted to the given IUCN tier. A loot box can never hand out an animal
    the player hasn't unlocked -- it just skips the coin cost of buying it."""
    owned = set(state.owned_animals)
    unlocked = set(state.unlocked_animals)
    return [
        a for a in animals_module.get_catalog()
        if a["id"] in unlocked and a["id"] not in owned and a["conservation"] == tier
    ]


def roll_reward(state) -> Dict[str, Any]:
    """Roll (but do not apply) one loot-box reward. Returns a dict with a `kind`
    of coins/animal/skill, a `rarity` band, a display `label`, and payload."""
    band = _weighted_band()

    # Epic boxes can pay out in skill points.
    if band == "epic" and random.random() < EPIC_SKILL_CHANCE:
        pts = random.randint(*EPIC_SKILL_RANGE)
        return {
            "kind": "skill", "amount": pts, "rarity": "epic",
            "label": f"+{pts} skill point" + ("" if pts == 1 else "s"),
        }

    # Try an animal from this band's tier.
    if random.random() < ANIMAL_CHANCE.get(band, 0.0):
        pool = _eligible_animals(state, BAND_ANIMAL_TIER[band])
        if pool:
            animal = random.choice(pool)
            return {
                "kind": "animal", "animal_id": animal["id"], "rarity": band,
                "label": animal["name"],
            }

    # Default: coins, rounded to a tidy multiple of 5.
    lo, hi = COIN_RANGES[band]
    amount = int(round(random.randint(lo, hi) / 5.0)) * 5
    return {"kind": "coins", "amount": amount, "rarity": band, "label": f"{amount} coins"}


def apply_reward(state, reward: Dict[str, Any]) -> None:
    """Grant a rolled reward to the player's state (caller saves)."""
    kind = reward.get("kind")
    if kind == "coins":
        state.coins += int(reward.get("amount", 0))
    elif kind == "skill":
        state.bonus_skill_points += int(reward.get("amount", 0))
    elif kind == "animal":
        animal_id = reward.get("animal_id")
        if animal_id and animal_id not in state.owned_animals:
            if animal_id not in state.unlocked_animals:
                state.unlocked_animals.append(animal_id)
            state.owned_animals.append(animal_id)
