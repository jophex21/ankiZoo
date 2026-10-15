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

# Biome names that aren't safe/available as a terrain filename stem map to the
# terrain file they should reuse instead (e.g. a merged biome reusing one of
# its former halves' art).
TERRAIN_SLUG: Dict[str, str] = {"Desert & Outback": "desert"}


def _find_terrain_file(biome: str) -> Optional[str]:
    stem = TERRAIN_SLUG.get(biome, biome.lower())
    for ext in _SPRITE_EXTS:
        path = os.path.join(TERRAIN_DIR, f"{stem}{ext}")
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
    "Desert & Outback": "#e07a2e",  # burnt orange
}

# The order biome branches fan out in the tree (root at the bottom-center).
BIOME_ORDER: List[str] = [
    "Savanna", "Arctic", "Ocean", "Jungle", "Forest", "Desert & Outback",
]

# IUCN Red List tiers, ordered least -> most at risk, plus a synthetic "EX"
# (Extinct) tier above CR for prehistoric/extinct animals. Each biome tree is a
# spine of the tiers it contains; unlocking an animal earns that biome "stars"
# (rarer = more), and accumulated stars gate access to the biome's higher tiers.
# EX additionally requires a minimum player level (see EX_MIN_LEVEL) on top of
# the usual star gate, since it's meant to be a deliberate late-game milestone.
TIER_ORDER: List[str] = ["LC", "NT", "VU", "EN", "CR", "EX"]
_CONSERVATION_RANK: Dict[str, int] = {t: i for i, t in enumerate(TIER_ORDER)}
TIER_NAME: Dict[str, str] = {
    "LC": "Least Concern", "NT": "Near Threatened", "VU": "Vulnerable",
    "EN": "Endangered", "CR": "Critically Endangered", "EX": "Extinct",
}
_RARITY_FOR_TIER: Dict[str, str] = {
    "LC": "common", "NT": "uncommon", "VU": "rare", "EN": "epic", "CR": "legendary",
    "EX": "mythic",
}
# Stars an unlocked animal contributes to its biome (rarer tiers are worth more and
# count more toward reaching the next tier). Skill-point/coin unlock prices also
# scale with tier. All three tables are tunable balance knobs.
STAR_VALUE: Dict[str, int] = {"LC": 1, "NT": 3, "VU": 5, "EN": 8, "CR": 12, "EX": 18}
SKILL_COST: Dict[str, int] = {"LC": 1, "NT": 2, "VU": 3, "EN": 4, "CR": 5, "EX": 7}
COIN_COST: Dict[str, int] = {"LC": 30, "NT": 70, "VU": 120, "EN": 180, "CR": 260, "EX": 360}
# A tier unlocks once you hold ~GATE_FRACTION of all stars available in the tiers
# below it within that biome. <1 means you never need to unlock everything below.
GATE_FRACTION = 0.6

# EX tier also requires the player to have reached this level in the biome,
# on top of the usual star threshold. Spread across the 40-50 late-game window.
EX_MIN_LEVEL: Dict[str, int] = {
    "Ocean": 40, "Arctic": 42, "Savanna": 44, "Forest": 46,
    "Desert & Outback": 48, "Jungle": 50,
}

# (id, name, biome, conservation). Every animal here has hand-authored art in
# sprites/<id>_idle.png (see _find_sprite_file), so no template/pattern/palette
# is needed -- _build_catalog only falls back to procedural art when a hand
# file is missing.
_RAW_ANIMALS: List[Dict[str, Any]] = [
    # Savanna
    {"id": "hyena", "name": "Hyena", "biome": "Savanna", "conservation": "LC"},
    {"id": "bison", "name": "Bison", "biome": "Savanna", "conservation": "NT"},
    {"id": "zebra", "name": "Zebra", "biome": "Savanna", "conservation": "NT"},
    {"id": "cheetah", "name": "Cheetah", "biome": "Savanna", "conservation": "VU"},
    {"id": "giraffe", "name": "Giraffe", "biome": "Savanna", "conservation": "VU"},
    {"id": "lion", "name": "Lion", "biome": "Savanna", "conservation": "VU"},
    {"id": "elephant", "name": "Elephant", "biome": "Savanna", "conservation": "EN"},
    {"id": "eastern_bongo", "name": "Eastern Bongo", "biome": "Savanna", "conservation": "CR"},
    {"id": "rhino", "name": "Rhino", "biome": "Savanna", "conservation": "CR"},
    {"id": "brachiosaurus", "name": "Brachiosaurus", "biome": "Savanna", "conservation": "EX"},
    {"id": "triceratops", "name": "Triceratops", "biome": "Savanna", "conservation": "EX"},
    {"id": "trex", "name": "Tyrannosaurus Rex", "biome": "Savanna", "conservation": "EX"},
    # Arctic
    {"id": "arctic_fox", "name": "Arctic Fox", "biome": "Arctic", "conservation": "LC"},
    {"id": "seal", "name": "Seal", "biome": "Arctic", "conservation": "LC"},
    {"id": "beluga_whale", "name": "Beluga Whale", "biome": "Arctic", "conservation": "LC"},
    {"id": "magellanic_penguin", "name": "Magellanic Penguin", "biome": "Arctic", "conservation": "NT"},
    {"id": "emperor_penguin", "name": "Emperor Penguin", "biome": "Arctic", "conservation": "NT"},
    {"id": "narwhal", "name": "Narwhal", "biome": "Arctic", "conservation": "NT"},
    {"id": "walrus", "name": "Walrus", "biome": "Arctic", "conservation": "VU"},
    {"id": "polar_bear", "name": "Polar Bear", "biome": "Arctic", "conservation": "EN"},
    {"id": "mammoth", "name": "Woolly Mammoth", "biome": "Arctic", "conservation": "EX"},
    {"id": "smilodon", "name": "Smilodon", "biome": "Arctic", "conservation": "EX"},
    {"id": "direwolf", "name": "Dire Wolf", "biome": "Arctic", "conservation": "EX"},
    # Ocean
    {"id": "alligator", "name": "Alligator", "biome": "Ocean", "conservation": "LC"},
    {"id": "clownfish", "name": "Clownfish", "biome": "Ocean", "conservation": "LC"},
    {"id": "dolphin", "name": "Dolphin", "biome": "Ocean", "conservation": "LC"},
    {"id": "octopus", "name": "Octopus", "biome": "Ocean", "conservation": "LC"},
    {"id": "marlin", "name": "Marlin", "biome": "Ocean", "conservation": "NT"},
    {"id": "platypus", "name": "Platypus", "biome": "Ocean", "conservation": "NT"},
    {"id": "crocodile", "name": "Crocodile", "biome": "Ocean", "conservation": "VU"},
    {"id": "galapagos_tortoise", "name": "Galapagos Tortoise", "biome": "Ocean", "conservation": "VU"},
    {"id": "great_white_shark", "name": "Great White Shark", "biome": "Ocean", "conservation": "VU"},
    {"id": "manatee", "name": "Manatee", "biome": "Ocean", "conservation": "VU"},
    {"id": "marine_iguana", "name": "Marine Iguana", "biome": "Ocean", "conservation": "VU"},
    {"id": "mola_mola", "name": "Mola Mola", "biome": "Ocean", "conservation": "VU"},
    {"id": "giant_river_otter", "name": "Giant River Otter", "biome": "Ocean", "conservation": "EN"},
    {"id": "manta_ray", "name": "Manta Ray", "biome": "Ocean", "conservation": "EN"},
    {"id": "orca", "name": "Orca", "biome": "Ocean", "conservation": "EN"},
    {"id": "sea_turtle", "name": "Sea Turtle", "biome": "Ocean", "conservation": "EN"},
    {"id": "hammerhead_shark", "name": "Hammerhead Shark", "biome": "Ocean", "conservation": "CR"},
    {"id": "megalodon", "name": "Megalodon", "biome": "Ocean", "conservation": "EX"},
    {"id": "mosasaurus", "name": "Mosasaurus", "biome": "Ocean", "conservation": "EX"},
    {"id": "spinosaurus", "name": "Spinosaurus", "biome": "Ocean", "conservation": "EX"},
    # Jungle
    {"id": "macaw", "name": "Scarlet Macaw", "biome": "Jungle", "conservation": "LC"},
    {"id": "ocelot", "name": "Ocelot", "biome": "Jungle", "conservation": "LC"},
    {"id": "sloth", "name": "Sloth", "biome": "Jungle", "conservation": "LC"},
    {"id": "toucan", "name": "Toucan", "biome": "Jungle", "conservation": "LC"},
    {"id": "anteater", "name": "Anteater", "biome": "Jungle", "conservation": "VU"},
    {"id": "binturong", "name": "Binturong", "biome": "Jungle", "conservation": "VU"},
    {"id": "fossa", "name": "Fossa", "biome": "Jungle", "conservation": "VU"},
    {"id": "giant_panda", "name": "Giant Panda", "biome": "Jungle", "conservation": "VU"},
    {"id": "hyacinth_macaw", "name": "Hyacinth Macaw", "biome": "Jungle", "conservation": "VU"},
    {"id": "king_cobra", "name": "King Cobra", "biome": "Jungle", "conservation": "VU"},
    {"id": "mandrill", "name": "Mandrill", "biome": "Jungle", "conservation": "VU"},
    {"id": "chimpanzee", "name": "Chimpanzee", "biome": "Jungle", "conservation": "EN"},
    {"id": "komodo_dragon", "name": "Komodo Dragon", "biome": "Jungle", "conservation": "EN"},
    {"id": "okapi", "name": "Okapi", "biome": "Jungle", "conservation": "EN"},
    {"id": "red_panda", "name": "Red Panda", "biome": "Jungle", "conservation": "EN"},
    {"id": "ring_tailed_lemur", "name": "Ring-Tailed Lemur", "biome": "Jungle", "conservation": "EN"},
    {"id": "siberian_tiger", "name": "Siberian Tiger", "biome": "Jungle", "conservation": "EN"},
    {"id": "spider_monkey", "name": "Spider Monkey", "biome": "Jungle", "conservation": "EN"},
    {"id": "tapir", "name": "Tapir", "biome": "Jungle", "conservation": "EN"},
    {"id": "gorilla", "name": "Gorilla", "biome": "Jungle", "conservation": "CR"},
    {"id": "orangutan", "name": "Orangutan", "biome": "Jungle", "conservation": "CR"},
    {"id": "pangolin", "name": "Pangolin", "biome": "Jungle", "conservation": "CR"},
    {"id": "dodo", "name": "Dodo", "biome": "Jungle", "conservation": "EX"},
    {"id": "parasaurolophus", "name": "Parasaurolophus", "biome": "Jungle", "conservation": "EX"},
    # Forest
    {"id": "capybara", "name": "Capybara", "biome": "Forest", "conservation": "LC"},
    {"id": "bald_eagle", "name": "Bald Eagle", "biome": "Forest", "conservation": "LC"},
    {"id": "beaver", "name": "Beaver", "biome": "Forest", "conservation": "LC"},
    {"id": "black_bear", "name": "Black Bear", "biome": "Forest", "conservation": "LC"},
    {"id": "deer", "name": "Deer", "biome": "Forest", "conservation": "LC"},
    {"id": "fox", "name": "Fox", "biome": "Forest", "conservation": "LC"},
    {"id": "owl", "name": "Owl", "biome": "Forest", "conservation": "LC"},
    {"id": "porcupine", "name": "Porcupine", "biome": "Forest", "conservation": "LC"},
    {"id": "goliath_beetle", "name": "Goliath Beetle", "biome": "Forest", "conservation": "LC"},
    {"id": "forest_wolf", "name": "Wolf", "biome": "Forest", "conservation": "NT"},
    {"id": "vulture", "name": "Vulture", "biome": "Forest", "conservation": "NT"},
    {"id": "brown_bear", "name": "Brown Bear", "biome": "Forest", "conservation": "VU"},
    {"id": "shoebill", "name": "Shoebill", "biome": "Forest", "conservation": "VU"},
    {"id": "snow_leopard", "name": "Snow Leopard", "biome": "Forest", "conservation": "VU"},
    {"id": "urial", "name": "Urial", "biome": "Forest", "conservation": "VU"},
    {"id": "monarch_butterfly", "name": "Monarch Butterfly", "biome": "Forest", "conservation": "EN"},
    {"id": "black_footed_ferret", "name": "Black-Footed Ferret", "biome": "Forest", "conservation": "EN"},
    {"id": "stegosaurus", "name": "Stegosaurus", "biome": "Forest", "conservation": "EX"},
    {"id": "ankylosaurus", "name": "Ankylosaurus", "biome": "Forest", "conservation": "EX"},
    {"id": "pachycephalosaurus", "name": "Pachycephalosaurus", "biome": "Forest", "conservation": "EX"},
    # Desert & Outback
    {"id": "meerkat", "name": "Meerkat", "biome": "Desert & Outback", "conservation": "LC"},
    {"id": "ostrich", "name": "Ostrich", "biome": "Desert & Outback", "conservation": "LC"},
    {"id": "thorny_devil", "name": "Thorny Devil", "biome": "Desert & Outback", "conservation": "LC"},
    {"id": "kangaroo", "name": "Kangaroo", "biome": "Desert & Outback", "conservation": "LC"},
    {"id": "black_footed_rock_wallaby", "name": "Black-Footed Rock Wallaby", "biome": "Desert & Outback", "conservation": "VU"},
    {"id": "camel", "name": "Camel", "biome": "Desert & Outback", "conservation": "EN"},
    {"id": "koala", "name": "Koala", "biome": "Desert & Outback", "conservation": "EN"},
    {"id": "tree_kangaroo", "name": "Tree Kangaroo", "biome": "Desert & Outback", "conservation": "EN"},
    {"id": "dimetrodon", "name": "Dimetrodon", "biome": "Desert & Outback", "conservation": "EX"},
    {"id": "velociraptor", "name": "Velociraptor", "biome": "Desert & Outback", "conservation": "EX"},
]

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

            idle_file = _find_sprite_file(raw["id"], "idle")
            blink_file = _find_sprite_file(raw["id"], "blink")
            idle_frame = blink_frame = None
            if idle_file:
                idle_uri = sprite_render.file_data_uri(idle_file)
                # Blink frame is optional -- reuse idle art (no blink animation) if absent.
                blink_uri = sprite_render.file_data_uri(blink_file) if blink_file else idle_uri
            else:
                # No hand-authored art yet -- fall back to procedural placeholder art.
                idle, blink = sprite_templates.build_sprite_frames(
                    raw.get("template", "mammal"), raw.get("pattern", "none"), raw["id"]
                )
                idle_frame = sprite_templates.grid_to_strings(idle)
                blink_frame = sprite_templates.grid_to_strings(blink)
                palette = raw.get("palette", {})
                idle_uri = sprite_render.sprite_data_uri(idle_frame, palette)
                blink_uri = sprite_render.sprite_data_uri(blink_frame, palette)

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
                "min_level": EX_MIN_LEVEL.get(biome, 0) if tier == "EX" else 0,
                "palette": raw.get("palette"),
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


def tier_accessible(animal: Dict[str, Any], unlocked: List[str], level: int = 0) -> bool:
    """A tier is reachable once the biome holds enough stars for its threshold.
    The EX (Extinct) tier additionally requires the player to have reached its
    biome's minimum level, regardless of stars."""
    if animal["conservation"] == "EX" and level < EX_MIN_LEVEL.get(animal["biome"], 0):
        return False
    return biome_stars(unlocked).get(animal["biome"], 0) >= animal["tier_threshold"]
