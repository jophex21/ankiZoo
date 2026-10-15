from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from aqt import mw

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class ZooState:
    total_xp: int = 0
    coins: int = 0
    owned_tiles: List[List[int]] = field(default_factory=lambda: [[5, 5]])  # legacy 11x11 grid (pre-map redesign)
    placed_animals: Dict[str, str] = field(default_factory=dict)  # legacy "x,y" -> animal_id
    tile_terrain: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # legacy "x,y" -> {"biome", "ox", "oy"}
    # Zoo-map model: the park is a set of square plots grouped into biome districts.
    # A plot id is "<Biome>-<index>" (e.g. "Savanna-0"). Plots unlock left-to-right
    # within a district (construction state); an owned animal is then placed into one.
    unlocked_plots: List[str] = field(default_factory=list)   # plot ids the player has unlocked
    plot_animals: Dict[str, str] = field(default_factory=dict)  # plot id -> animal_id
    plots_init: bool = False  # one-time migration of legacy placements into plots
    # Two-step ownership: an animal is first *unlocked* in the skill tree (costs
    # skill points), then *bought* with coins to become placeable in the zoo.
    unlocked_animals: List[str] = field(default_factory=list)  # skill-tree unlocks
    owned_animals: List[str] = field(default_factory=list)     # coin-bought / placeable
    # Animals unlocked before the skill-tree system existed. They're "grandfathered"
    # so they don't retroactively drain the skill-point budget (see animals.points_spent).
    # pretree_init marks that the one-time snapshot has been taken for this save.
    pretree_animals: List[str] = field(default_factory=list)
    pretree_init: bool = False
    # Bonus skill points awarded outside the level curve (e.g. from loot boxes).
    # Added on top of the level*POINTS_PER_LEVEL budget in animals.available_points.
    bonus_skill_points: int = 0
    streak_current: int = 0
    streak_best: int = 0
    quests_date: str = ""
    quests: List[Dict[str, Any]] = field(default_factory=list)
    last_undo_xp: List[int] = field(default_factory=list)
    last_undo_coins: List[int] = field(default_factory=list)


class ZooData:
    """Per-profile persistence for ankiZoo, mirroring Onigiri's JSON-file approach."""

    def __init__(self, addon_path: str) -> None:
        self.addon_path = addon_path
        self.state = ZooState()
        self._load()
        self._migrate()

    def _migrate(self) -> None:
        """One-time save migrations for the skill-tree system."""
        st = self.state
        changed = False
        # Snapshot animals present before the skill tree existed so they stay free
        # (don't drain the skill-point budget; see animals.points_spent).
        if not st.pretree_init:
            st.pretree_animals = list(st.owned_animals)
            st.pretree_init = True
            changed = True
        # Invariant: anything owned (coin-bought) must also be unlocked.
        missing = [a for a in st.owned_animals if a not in st.unlocked_animals]
        if missing:
            st.unlocked_animals.extend(missing)
            changed = True
        # One-time: carry legacy grid placements into the biome-district plot model
        # so an existing zoo isn't emptied by the map redesign.
        if not st.plots_init:
            from . import animals as animals_module
            per_biome = {}
            for animal_id in st.placed_animals.values():
                try:
                    biome = animals_module.get_animal(animal_id)["biome"]
                except KeyError:
                    continue
                idx = per_biome.get(biome, 0)
                per_biome[biome] = idx + 1
                plot_id = f"{biome}-{idx}"
                if plot_id not in st.unlocked_plots:
                    st.unlocked_plots.append(plot_id)
                st.plot_animals[plot_id] = animal_id
            st.plots_init = True
            changed = True
        # Drop ids that no longer exist in the catalog (e.g. after a sprite/animal
        # replacement) so they don't sit dead in these lists forever.
        from . import animals as animals_module
        valid_ids = {a["id"] for a in animals_module.get_catalog()}
        for attr in ("unlocked_animals", "owned_animals", "pretree_animals"):
            lst = getattr(st, attr)
            filtered = [a for a in lst if a in valid_ids]
            if filtered != lst:
                setattr(st, attr, filtered)
                changed = True
        stale_plots = [p for p, a in st.plot_animals.items() if a not in valid_ids]
        for plot_id in stale_plots:
            st.plot_animals.pop(plot_id)
            changed = True
        if changed:
            self.save()

    def _get_data_path(self) -> str:
        user_files = os.path.join(self.addon_path, "user_files")
        os.makedirs(user_files, exist_ok=True)
        try:
            profile_name = mw.pm.name
        except Exception:
            profile_name = "default"
        return os.path.join(user_files, f"zoo_{profile_name}.json")

    def _load(self) -> None:
        path = self._get_data_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            known_fields = {f.name for f in self.state.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in known_fields}
            self.state = ZooState(**filtered)
        except Exception as e:
            print(f"ankiZoo: Error loading zoo data: {e}")

    def save(self) -> None:
        path = self._get_data_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self.state), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"ankiZoo: Error saving zoo data: {e}")

    def reset(self) -> None:
        self.state = ZooState()
        self.save()


_zoo_data: Optional[ZooData] = None


def _reset_zoo_data(*args: Any) -> None:
    global _zoo_data
    _zoo_data = None


from aqt import gui_hooks

gui_hooks.profile_did_open.append(_reset_zoo_data)


def get_zoo_data() -> ZooData:
    global _zoo_data
    if _zoo_data is None:
        _zoo_data = ZooData(ADDON_DIR)
    return _zoo_data
