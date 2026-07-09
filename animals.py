from __future__ import annotations

import functools
import os
from typing import Any, Dict, List, Optional, Tuple

from . import sprite_render, sprite_templates

# Hand-authored sprites live here, named "<animal_id>_idle.<ext>" and
# "<animal_id>_blink.<ext>" (png/jpg/jpeg/gif/webp/svg). Any animal without a
# matching idle file keeps using the procedural placeholder art, so files can
# be dropped in incrementally without touching code.
SPRITES_DIR = os.path.join(os.path.dirname(__file__), "sprites")
_SPRITE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")


def _find_sprite_file(animal_id: str, suffix: str) -> Optional[str]:
    for ext in _SPRITE_EXTS:
        path = os.path.join(SPRITES_DIR, f"{animal_id}_{suffix}{ext}")
        if os.path.isfile(path):
            return path
    return None


# Per-biome terrain source images live here, named "<biome_lowercased>.<ext>".
# Each is expected to be larger than the 32x32 crop taken from it when an
# animal is placed on a tile (see zoo_dialog.py's placeAnimal handler).
TERRAIN_DIR = os.path.join(os.path.dirname(__file__), "terrain")


def _find_terrain_file(biome: str) -> Optional[str]:
    for ext in _SPRITE_EXTS:
        path = os.path.join(TERRAIN_DIR, f"{biome.lower()}{ext}")
        if os.path.isfile(path):
            return path
    return None


@functools.lru_cache(maxsize=None)
def get_terrain_size(biome: str) -> Tuple[int, int]:
    path = _find_terrain_file(biome)
    if not path:
        return (32, 32)
    from aqt.qt import QImage
    image = QImage(path)
    return (image.width(), image.height())


@functools.lru_cache(maxsize=None)
def get_terrain_data_uri(biome: str) -> Optional[str]:
    path = _find_terrain_file(biome)
    if not path:
        return None
    return sprite_render.file_data_uri(path)

# Each biome is a colored branch of the skill tree. Animals within a branch are
# ordered common -> endangered (see _CONSERVATION_RANK); the color is used for the
# branch's connectors and node rings in the Skill Tree UI.
BIOME_COLORS: Dict[str, str] = {
    "Savanna": "#e0a92e",  # gold
    "Arctic": "#7cc9e0",   # ice blue
    "Ocean": "#3f78c9",    # deep blue
    "Jungle": "#37b24d",   # vivid green
    "Forest": "#2f7d4f",   # pine green
    "Desert": "#e07a2e",   # burnt orange
    "Outback": "#c0492e",  # red clay
}

# The order biome branches fan out in the tree (root at the bottom-center).
BIOME_ORDER: List[str] = [
    "Savanna", "Arctic", "Ocean", "Jungle", "Forest", "Desert", "Outback",
]

# IUCN Red List tiers, ordered least -> most at risk. Each biome tree is a spine of
# the tiers it contains; unlocking an animal earns that biome "stars" (rarer = more),
# and accumulated stars gate access to the biome's higher tiers.
TIER_ORDER: List[str] = ["LC", "NT", "VU", "EN", "CR"]
_CONSERVATION_RANK: Dict[str, int] = {t: i for i, t in enumerate(TIER_ORDER)}
TIER_NAME: Dict[str, str] = {
    "LC": "Least Concern", "NT": "Near Threatened", "VU": "Vulnerable",
    "EN": "Endangered", "CR": "Critically Endangered",
}
_RARITY_FOR_TIER: Dict[str, str] = {
    "LC": "common", "NT": "uncommon", "VU": "rare", "EN": "epic", "CR": "legendary",
}
# Stars an unlocked animal contributes to its biome (rarer tiers are worth more and
# count more toward reaching the next tier). Skill-point/coin unlock prices also
# scale with tier. All three tables are tunable balance knobs.
STAR_VALUE: Dict[str, int] = {"LC": 1, "NT": 3, "VU": 5, "EN": 8, "CR": 12}
SKILL_COST: Dict[str, int] = {"LC": 1, "NT": 2, "VU": 3, "EN": 4, "CR": 5}
COIN_COST: Dict[str, int] = {"LC": 30, "NT": 70, "VU": 120, "EN": 180, "CR": 260}
# A tier unlocks once you hold ~GATE_FRACTION of all stars available in the tiers
# below it within that biome. <1 means you never need to unlock everything below.
GATE_FRACTION = 0.6

# (id, name, biome, conservation, template, pattern, palette[body, shade, accent, eye])
_RAW_ANIMALS: List[Dict[str, Any]] = [
    # Savanna
    {"id": "lion", "name": "Lion", "biome": "Savanna", "conservation": "VU", "template": "mammal", "pattern": "none",
     "palette": {"B": "#d9a441", "S": "#b8822c", "A": "#7a4a1e", "E": "#2b1a0e"}},
    {"id": "elephant", "name": "Elephant", "biome": "Savanna", "conservation": "EN", "template": "mammal", "pattern": "none",
     "palette": {"B": "#9ea6ab", "S": "#7c8388", "A": "#5f6569", "E": "#1c1c1c"}},
    {"id": "giraffe", "name": "Giraffe", "biome": "Savanna", "conservation": "LC", "template": "mammal", "pattern": "spots",
     "palette": {"B": "#eecb7a", "S": "#d9b25f", "A": "#8a5a2b", "E": "#2b1a0e"}},
    {"id": "zebra", "name": "Zebra", "biome": "Savanna", "conservation": "LC", "template": "mammal", "pattern": "stripes",
     "palette": {"B": "#f2f2f2", "S": "#d8d8d8", "A": "#232323", "E": "#111111"}},
    {"id": "rhino", "name": "Rhino", "biome": "Savanna", "conservation": "CR", "template": "mammal", "pattern": "none",
     "palette": {"B": "#8f9a8a", "S": "#727d6e", "A": "#565f53", "E": "#161616"}},
    # Arctic
    {"id": "polar_bear", "name": "Polar Bear", "biome": "Arctic", "conservation": "EN", "template": "mammal", "pattern": "none",
     "palette": {"B": "#f2f6f8", "S": "#d6e2e6", "A": "#aebcc0", "E": "#1a1a1a"}},
    {"id": "penguin", "name": "Penguin", "biome": "Arctic", "conservation": "NT", "template": "bird", "pattern": "mask",
     "palette": {"B": "#f5f5f5", "S": "#dedede", "A": "#1c1c1c", "E": "#111111"}},
    {"id": "arctic_fox", "name": "Arctic Fox", "biome": "Arctic", "conservation": "LC", "template": "mammal", "pattern": "none",
     "palette": {"B": "#eef2f4", "S": "#cfd9dc", "A": "#a9b6ba", "E": "#1a1a1a"}},
    {"id": "seal", "name": "Seal", "biome": "Arctic", "conservation": "LC", "template": "marine", "pattern": "spots",
     "palette": {"B": "#8e9aa3", "S": "#6f7a82", "A": "#4c545a", "E": "#111111"}},
    {"id": "walrus", "name": "Walrus", "biome": "Arctic", "conservation": "VU", "template": "marine", "pattern": "none",
     "palette": {"B": "#c9a267", "S": "#a9824c", "A": "#7a5a30", "E": "#1a1a1a"}},
    # Ocean
    {"id": "dolphin", "name": "Dolphin", "biome": "Ocean", "conservation": "LC", "template": "marine", "pattern": "none",
     "palette": {"B": "#7fa8c9", "S": "#5f88ab", "A": "#3f688b", "E": "#0f1f2b"}},
    {"id": "sea_turtle", "name": "Sea Turtle", "biome": "Ocean", "conservation": "EN", "template": "marine", "pattern": "mask",
     "palette": {"B": "#6fa66a", "S": "#528049", "A": "#345c2d", "E": "#111111"}},
    {"id": "orca", "name": "Orca", "biome": "Ocean", "conservation": "CR", "template": "marine", "pattern": "mask",
     "palette": {"B": "#2b2f36", "S": "#1c1f24", "A": "#f2f2f2", "E": "#f2f2f2"}},
    {"id": "shark", "name": "Shark", "biome": "Ocean", "conservation": "VU", "template": "marine", "pattern": "none",
     "palette": {"B": "#8b98a3", "S": "#6c7982", "A": "#4c565d", "E": "#111111"}},
    {"id": "octopus", "name": "Octopus", "biome": "Ocean", "conservation": "LC", "template": "marine", "pattern": "spots",
     "palette": {"B": "#b56aa8", "S": "#914f86", "A": "#6b3564", "E": "#1a0a18"}},
    # Jungle
    {"id": "tiger", "name": "Tiger", "biome": "Jungle", "conservation": "EN", "template": "mammal", "pattern": "stripes",
     "palette": {"B": "#e08a2e", "S": "#c06f1c", "A": "#221510", "E": "#111111"}},
    {"id": "gorilla", "name": "Gorilla", "biome": "Jungle", "conservation": "CR", "template": "biped", "pattern": "none",
     "palette": {"B": "#3c3630", "S": "#2a2521", "A": "#1c1815", "E": "#0c0c0c"}},
    {"id": "chimpanzee", "name": "Chimpanzee", "biome": "Jungle", "conservation": "EN", "template": "biped", "pattern": "mask",
     "palette": {"B": "#7a5335", "S": "#5e3f27", "A": "#e7c9a3", "E": "#1a1006"}},
    {"id": "toucan", "name": "Toucan", "biome": "Jungle", "conservation": "LC", "template": "bird", "pattern": "mask",
     "palette": {"B": "#22201f", "S": "#141312", "A": "#f0a13a", "E": "#f2f2f2"}},
    {"id": "red_panda", "name": "Red Panda", "biome": "Jungle", "conservation": "NT", "template": "mammal", "pattern": "mask",
     "palette": {"B": "#b8562f", "S": "#943f1f", "A": "#f2ede0", "E": "#1a0e08"}},
    # Forest
    {"id": "brown_bear", "name": "Brown Bear", "biome": "Forest", "conservation": "VU", "template": "mammal", "pattern": "none",
     "palette": {"B": "#7a5738", "S": "#5e4128", "A": "#432e1b", "E": "#161010"}},
    {"id": "wolf", "name": "Wolf", "biome": "Forest", "conservation": "NT", "template": "mammal", "pattern": "none",
     "palette": {"B": "#8d8f94", "S": "#6d6f74", "A": "#4c4e52", "E": "#e8b93a"}},
    {"id": "fox", "name": "Fox", "biome": "Forest", "conservation": "LC", "template": "mammal", "pattern": "mask",
     "palette": {"B": "#d9702e", "S": "#b8571e", "A": "#f2ede0", "E": "#1a0e08"}},
    {"id": "owl", "name": "Owl", "biome": "Forest", "conservation": "LC", "template": "bird", "pattern": "spots",
     "palette": {"B": "#8a6d4c", "S": "#6d5439", "A": "#3f3122", "E": "#f2c94c"}},
    {"id": "deer", "name": "Deer", "biome": "Forest", "conservation": "LC", "template": "mammal", "pattern": "spots",
     "palette": {"B": "#c08a55", "S": "#9c6d3f", "A": "#f2ede0", "E": "#1a1008"}},
    # Desert / Outback
    {"id": "camel", "name": "Camel", "biome": "Desert", "conservation": "EN", "template": "mammal", "pattern": "none",
     "palette": {"B": "#d9b877", "S": "#bd9a5a", "A": "#8f6f3f", "E": "#1a1208"}},
    {"id": "kangaroo", "name": "Kangaroo", "biome": "Outback", "conservation": "LC", "template": "biped", "pattern": "none",
     "palette": {"B": "#a9825c", "S": "#8a6746", "A": "#5f4530", "E": "#111111"}},
    {"id": "meerkat", "name": "Meerkat", "biome": "Desert", "conservation": "LC", "template": "biped", "pattern": "mask",
     "palette": {"B": "#c9a877", "S": "#a98a5e", "A": "#4c3b28", "E": "#111111"}},
    {"id": "koala", "name": "Koala", "biome": "Outback", "conservation": "EN", "template": "mammal", "pattern": "none",
     "palette": {"B": "#a8a9a3", "S": "#87887f", "A": "#5f6058", "E": "#111111"}},
    {"id": "ostrich", "name": "Ostrich", "biome": "Desert", "conservation": "LC", "template": "bird", "pattern": "none",
     "palette": {"B": "#2b2825", "S": "#1a1816", "A": "#e8b93a", "E": "#111111"}},
]

assert len(_RAW_ANIMALS) == 30

POINTS_PER_LEVEL = 2  # skill points granted per level (see leveling.get_progress)


def _tier_thresholds(tiers_present: List[str], tier_star_pool: Dict[str, int]) -> Dict[str, int]:
    """Star cost to access each tier: GATE_FRACTION of all stars available in the
    tiers below it. The first present tier is always free (threshold 0)."""
    import math
    thresholds: Dict[str, int] = {}
    pool_below = 0
    for tier in tiers_present:
        thresholds[tier] = math.ceil(GATE_FRACTION * pool_below)
        pool_below += tier_star_pool[tier]
    return thresholds


def _build_catalog() -> List[Dict[str, Any]]:
    # Group by biome (first-seen order), then by IUCN tier. Each biome tree is a
    # spine of the tiers it actually contains; animals share a tier as siblings.
    by_biome: Dict[str, List[Dict[str, Any]]] = {}
    for raw in _RAW_ANIMALS:
        by_biome.setdefault(raw["biome"], []).append(raw)

    catalog: List[Dict[str, Any]] = []
    for biome, group in by_biome.items():
        tiers_present = [t for t in TIER_ORDER if any(r["conservation"] == t for r in group)]
        tier_star_pool = {
            t: sum(STAR_VALUE[r["conservation"]] for r in group if r["conservation"] == t)
            for t in tiers_present
        }
        thresholds = _tier_thresholds(tiers_present, tier_star_pool)

        per_tier_index: Dict[str, int] = {t: 0 for t in tiers_present}
        tier_size = {t: sum(1 for r in group if r["conservation"] == t) for t in tiers_present}
        # Emit ordered by tier then original list order, so layout is deterministic.
        ordered = sorted(group, key=lambda r: _CONSERVATION_RANK[r["conservation"]])
        for raw in ordered:
            tier = raw["conservation"]
            idle, blink = sprite_templates.build_sprite_frames(raw["template"], raw["pattern"], raw["id"])
            idle_frame = sprite_templates.grid_to_strings(idle)
            blink_frame = sprite_templates.grid_to_strings(blink)

            idle_file = _find_sprite_file(raw["id"], "idle")
            blink_file = _find_sprite_file(raw["id"], "blink")
            if idle_file:
                idle_uri = sprite_render.file_data_uri(idle_file)
                # Blink frame is optional -- reuse idle art (no blink animation) if absent.
                blink_uri = sprite_render.file_data_uri(blink_file) if blink_file else idle_uri
            else:
                idle_uri = sprite_render.sprite_data_uri(idle_frame, raw["palette"])
                blink_uri = sprite_render.sprite_data_uri(blink_frame, raw["palette"])

            catalog.append({
                "id": raw["id"],
                "name": raw["name"],
                "biome": biome,
                "biome_color": BIOME_COLORS.get(biome, "#888888"),
                "conservation": tier,
                "tier_name": TIER_NAME.get(tier, tier),
                "tier_rank": tiers_present.index(tier),
                "star_value": STAR_VALUE[tier],
                "tier_threshold": thresholds[tier],
                "within_tier_index": per_tier_index[tier],
                "tier_size": tier_size[tier],
                "skill_cost": SKILL_COST[tier],
                "cost_coins": COIN_COST[tier],
                "rarity": _RARITY_FOR_TIER.get(tier, "common"),
                "palette": raw["palette"],
                "sprite_idle": idle_frame,
                "sprite_blink": blink_frame,
                "sprite_idle_uri": idle_uri,
                "sprite_blink_uri": blink_uri,
                "sprite_file": idle_file,
            })
            per_tier_index[tier] += 1
    return catalog


_CATALOG: List[Dict[str, Any]] = []


def get_catalog() -> List[Dict[str, Any]]:
    global _CATALOG
    if not _CATALOG:
        _CATALOG = _build_catalog()
    return _CATALOG


def get_animal(animal_id: str) -> Dict[str, Any]:
    for animal in get_catalog():
        if animal["id"] == animal_id:
            return animal
    raise KeyError(animal_id)


def points_spent(unlocked: List[str], pretree: List[str]) -> int:
    """Skill points spent on tree unlocks: sum of skill_cost over unlocked animals,
    excluding grandfathered ones (unlocked before the skill tree existed)."""
    grandfathered = set(pretree)
    by_id = {a["id"]: a for a in get_catalog()}
    total = 0
    for animal_id in unlocked:
        if animal_id in grandfathered:
            continue
        animal = by_id.get(animal_id)
        if animal:
            total += animal["skill_cost"]
    return total


def available_points(level: int, unlocked: List[str], pretree: List[str], bonus: int = 0) -> int:
    """Skill points a player currently has to spend (never negative). `bonus` is
    extra points earned off the level curve (e.g. loot-box rewards)."""
    return max(0, level * POINTS_PER_LEVEL + bonus - points_spent(unlocked, pretree))


def biome_stars(unlocked: List[str]) -> Dict[str, int]:
    """Stars earned per biome from unlocked animals (rarer = worth more)."""
    by_id = {a["id"]: a for a in get_catalog()}
    totals: Dict[str, int] = {}
    for animal_id in unlocked:
        animal = by_id.get(animal_id)
        if animal:
            totals[animal["biome"]] = totals.get(animal["biome"], 0) + animal["star_value"]
    return totals


def tier_accessible(animal: Dict[str, Any], unlocked: List[str]) -> bool:
    """A tier is reachable once the biome holds enough stars for its threshold."""
    return biome_stars(unlocked).get(animal["biome"], 0) >= animal["tier_threshold"]
