from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from aqt import mw


@dataclass
class QuestData:
    id: str
    kind: str  # "cards", "new_cards", "streak"
    target: int
    progress: int = 0
    completed: bool = False
    reward_type: str = "coins"  # "coins" or "animal"
    reward_amount: int = 0


@dataclass
class ZooState:
    total_xp: int = 0
    coins: int = 0
    owned_tiles: List[List[int]] = field(default_factory=lambda: [[5, 5]])  # center of the 11x11 grid
    placed_animals: Dict[str, str] = field(default_factory=dict)  # "x,y" -> animal_id
    owned_animals: List[str] = field(default_factory=list)
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

    def reload(self) -> None:
        self._load()

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


try:
    from aqt import gui_hooks

    gui_hooks.profile_did_open.append(_reset_zoo_data)
except Exception:
    pass


def get_zoo_data() -> ZooData:
    global _zoo_data
    if _zoo_data is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        _zoo_data = ZooData(current_dir)
    return _zoo_data
