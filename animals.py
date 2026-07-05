from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

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

# (id, name, biome, template, pattern, palette[body, shade, accent, eye])
_RAW_ANIMALS: List[Dict[str, Any]] = [
    # Savanna
    {"id": "lion", "name": "Lion", "biome": "Savanna", "template": "mammal", "pattern": "none",
     "palette": {"B": "#d9a441", "S": "#b8822c", "A": "#7a4a1e", "E": "#2b1a0e"}},
    {"id": "elephant", "name": "Elephant", "biome": "Savanna", "template": "mammal", "pattern": "none",
     "palette": {"B": "#9ea6ab", "S": "#7c8388", "A": "#5f6569", "E": "#1c1c1c"}},
    {"id": "giraffe", "name": "Giraffe", "biome": "Savanna", "template": "mammal", "pattern": "spots",
     "palette": {"B": "#eecb7a", "S": "#d9b25f", "A": "#8a5a2b", "E": "#2b1a0e"}},
    {"id": "zebra", "name": "Zebra", "biome": "Savanna", "template": "mammal", "pattern": "stripes",
     "palette": {"B": "#f2f2f2", "S": "#d8d8d8", "A": "#232323", "E": "#111111"}},
    {"id": "rhino", "name": "Rhino", "biome": "Savanna", "template": "mammal", "pattern": "none",
     "palette": {"B": "#8f9a8a", "S": "#727d6e", "A": "#565f53", "E": "#161616"}},
    # Arctic
    {"id": "polar_bear", "name": "Polar Bear", "biome": "Arctic", "template": "mammal", "pattern": "none",
     "palette": {"B": "#f2f6f8", "S": "#d6e2e6", "A": "#aebcc0", "E": "#1a1a1a"}},
    {"id": "penguin", "name": "Penguin", "biome": "Arctic", "template": "bird", "pattern": "mask",
     "palette": {"B": "#f5f5f5", "S": "#dedede", "A": "#1c1c1c", "E": "#111111"}},
    {"id": "arctic_fox", "name": "Arctic Fox", "biome": "Arctic", "template": "mammal", "pattern": "none",
     "palette": {"B": "#eef2f4", "S": "#cfd9dc", "A": "#a9b6ba", "E": "#1a1a1a"}},
    {"id": "seal", "name": "Seal", "biome": "Arctic", "template": "marine", "pattern": "spots",
     "palette": {"B": "#8e9aa3", "S": "#6f7a82", "A": "#4c545a", "E": "#111111"}},
    {"id": "walrus", "name": "Walrus", "biome": "Arctic", "template": "marine", "pattern": "none",
     "palette": {"B": "#c9a267", "S": "#a9824c", "A": "#7a5a30", "E": "#1a1a1a"}},
    # Ocean
    {"id": "dolphin", "name": "Dolphin", "biome": "Ocean", "template": "marine", "pattern": "none",
     "palette": {"B": "#7fa8c9", "S": "#5f88ab", "A": "#3f688b", "E": "#0f1f2b"}},
    {"id": "sea_turtle", "name": "Sea Turtle", "biome": "Ocean", "template": "marine", "pattern": "mask",
     "palette": {"B": "#6fa66a", "S": "#528049", "A": "#345c2d", "E": "#111111"}},
    {"id": "orca", "name": "Orca", "biome": "Ocean", "template": "marine", "pattern": "mask",
     "palette": {"B": "#2b2f36", "S": "#1c1f24", "A": "#f2f2f2", "E": "#f2f2f2"}},
    {"id": "shark", "name": "Shark", "biome": "Ocean", "template": "marine", "pattern": "none",
     "palette": {"B": "#8b98a3", "S": "#6c7982", "A": "#4c565d", "E": "#111111"}},
    {"id": "octopus", "name": "Octopus", "biome": "Ocean", "template": "marine", "pattern": "spots",
     "palette": {"B": "#b56aa8", "S": "#914f86", "A": "#6b3564", "E": "#1a0a18"}},
    # Jungle
    {"id": "tiger", "name": "Tiger", "biome": "Jungle", "template": "mammal", "pattern": "stripes",
     "palette": {"B": "#e08a2e", "S": "#c06f1c", "A": "#221510", "E": "#111111"}},
    {"id": "gorilla", "name": "Gorilla", "biome": "Jungle", "template": "biped", "pattern": "none",
     "palette": {"B": "#3c3630", "S": "#2a2521", "A": "#1c1815", "E": "#0c0c0c"}},
    {"id": "chimpanzee", "name": "Chimpanzee", "biome": "Jungle", "template": "biped", "pattern": "mask",
     "palette": {"B": "#7a5335", "S": "#5e3f27", "A": "#e7c9a3", "E": "#1a1006"}},
    {"id": "toucan", "name": "Toucan", "biome": "Jungle", "template": "bird", "pattern": "mask",
     "palette": {"B": "#22201f", "S": "#141312", "A": "#f0a13a", "E": "#f2f2f2"}},
    {"id": "red_panda", "name": "Red Panda", "biome": "Jungle", "template": "mammal", "pattern": "mask",
     "palette": {"B": "#b8562f", "S": "#943f1f", "A": "#f2ede0", "E": "#1a0e08"}},
    # Forest
    {"id": "brown_bear", "name": "Brown Bear", "biome": "Forest", "template": "mammal", "pattern": "none",
     "palette": {"B": "#7a5738", "S": "#5e4128", "A": "#432e1b", "E": "#161010"}},
    {"id": "wolf", "name": "Wolf", "biome": "Forest", "template": "mammal", "pattern": "none",
     "palette": {"B": "#8d8f94", "S": "#6d6f74", "A": "#4c4e52", "E": "#e8b93a"}},
    {"id": "fox", "name": "Fox", "biome": "Forest", "template": "mammal", "pattern": "mask",
     "palette": {"B": "#d9702e", "S": "#b8571e", "A": "#f2ede0", "E": "#1a0e08"}},
    {"id": "owl", "name": "Owl", "biome": "Forest", "template": "bird", "pattern": "spots",
     "palette": {"B": "#8a6d4c", "S": "#6d5439", "A": "#3f3122", "E": "#f2c94c"}},
    {"id": "deer", "name": "Deer", "biome": "Forest", "template": "mammal", "pattern": "spots",
     "palette": {"B": "#c08a55", "S": "#9c6d3f", "A": "#f2ede0", "E": "#1a1008"}},
    # Desert / Outback
    {"id": "camel", "name": "Camel", "biome": "Desert", "template": "mammal", "pattern": "none",
     "palette": {"B": "#d9b877", "S": "#bd9a5a", "A": "#8f6f3f", "E": "#1a1208"}},
    {"id": "kangaroo", "name": "Kangaroo", "biome": "Outback", "template": "biped", "pattern": "none",
     "palette": {"B": "#a9825c", "S": "#8a6746", "A": "#5f4530", "E": "#111111"}},
    {"id": "meerkat", "name": "Meerkat", "biome": "Desert", "template": "biped", "pattern": "mask",
     "palette": {"B": "#c9a877", "S": "#a98a5e", "A": "#4c3b28", "E": "#111111"}},
    {"id": "koala", "name": "Koala", "biome": "Outback", "template": "mammal", "pattern": "none",
     "palette": {"B": "#a8a9a3", "S": "#87887f", "A": "#5f6058", "E": "#111111"}},
    {"id": "ostrich", "name": "Ostrich", "biome": "Desert", "template": "bird", "pattern": "none",
     "palette": {"B": "#2b2825", "S": "#1a1816", "A": "#e8b93a", "E": "#111111"}},
]

assert len(_RAW_ANIMALS) == 30


def _unlock_level_for_index(i: int, count: int) -> int:
    """Spread unlocks across levels 1..50, denser early, sparser late."""
    frac = (i + 1) / count
    level = round(50 * (frac ** 1.6))
    return max(1, level)


def _rarity_for_level(level: int) -> str:
    if level < 10:
        return "common"
    if level < 20:
        return "uncommon"
    if level < 30:
        return "rare"
    if level < 40:
        return "epic"
    return "legendary"


def _cost_for_level(level: int) -> int:
    return 40 + level * 12


def _build_catalog() -> List[Dict[str, Any]]:
    catalog: List[Dict[str, Any]] = []
    for i, raw in enumerate(_RAW_ANIMALS):
        level = _unlock_level_for_index(i, len(_RAW_ANIMALS))
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
            "biome": raw["biome"],
            "unlock_level": level,
            "rarity": _rarity_for_level(level),
            "cost_coins": _cost_for_level(level),
            "palette": raw["palette"],
            "sprite_idle": idle_frame,
            "sprite_blink": blink_frame,
            "sprite_idle_uri": idle_uri,
            "sprite_blink_uri": blink_uri,
            "sprite_file": idle_file,
        })
    catalog.sort(key=lambda a: a["unlock_level"])
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
