from __future__ import annotations

import copy
from typing import Any, Dict

from aqt import mw

DEFAULTS: Dict[str, Any] = {
    "xpPerCard": 1,
    "coinsPerCard": 1,
    "levelCurveBase": 4,
    "pomodoroMinutes": 25,
    "dailyQuestCount": 3,
    "tileExpandBaseCost": 25,
    "tileExpandCostPerOwned": 8,
    "notificationsEnabled": True,
    "lootBox": {
        "common": {"min": 20, "max": 40, "weight": 60},
        "uncommon": {"min": 41, "max": 70, "weight": 30},
        "rare": {"min": 71, "max": 100, "weight": 10},
    },
}


def get_config() -> Dict[str, Any]:
    conf = mw.addonManager.getConfig(__name__) or {}
    merged = copy.deepcopy(DEFAULTS)
    merged.update(conf)
    return merged


def write_config(conf: Dict[str, Any]) -> None:
    mw.addonManager.writeConfig(__name__, conf)
