from __future__ import annotations

import random
import time
from typing import Dict, Optional

from . import config

# Deliberately in-memory only (not persisted to zoo_data): closing Anki
# mid-Pomodoro should abandon the run and reset to the default duration,
# per spec, rather than resuming it on next launch.
_runtime: Dict[str, Optional[float]] = {"start": None, "minutes": 25}


def start(minutes: Optional[int] = None) -> None:
    if minutes is None:
        minutes = int(config.get_config().get("pomodoroMinutes", 25))
    _runtime["start"] = time.time()
    _runtime["minutes"] = minutes


def cancel() -> None:
    _runtime["start"] = None
    _runtime["minutes"] = int(config.get_config().get("pomodoroMinutes", 25))


def is_running() -> bool:
    return _runtime["start"] is not None


def target_end_epoch() -> Optional[float]:
    if _runtime["start"] is None:
        return None
    return _runtime["start"] + _runtime["minutes"] * 60


def default_minutes() -> int:
    return int(config.get_config().get("pomodoroMinutes", 25))


def is_complete() -> bool:
    end = target_end_epoch()
    return end is not None and time.time() >= end


def complete_and_roll() -> Dict[str, object]:
    """Confirm completion (called from the pycmd handler) and roll a loot box."""
    _runtime["start"] = None
    return roll_loot_box()


def roll_loot_box() -> Dict[str, object]:
    conf = config.get_config()
    tiers = conf["lootBox"]
    names = list(tiers.keys())
    weights = [tiers[name]["weight"] for name in names]
    tier = random.choices(names, weights=weights, k=1)[0]
    bounds = tiers[tier]
    amount = random.randint(int(bounds["min"]), int(bounds["max"]))
    return {"tier": tier, "amount": amount}
