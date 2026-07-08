from __future__ import annotations

import copy
import re
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
    "widgetBgColor": "#1f232b",
    "widgetBorderColor": "#3f9142",
    "widgetXpBarColor": "#6fbf73",
    "widgetDividerColor": "#3f9142",
    "widgetQuestDoneColor": "#6fbf73",
    "lootBox": {
        "common": {"min": 20, "max": 40, "weight": 60},
        "uncommon": {"min": 41, "max": 70, "weight": 30},
        "rare": {"min": 71, "max": 100, "weight": 10},
    },
}

WIDGET_COLOR_KEYS = {
    "bg": "widgetBgColor",
    "border": "widgetBorderColor",
    "xpBar": "widgetXpBarColor",
    "divider": "widgetDividerColor",
    "questDone": "widgetQuestDoneColor",
}

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def valid_hex_color(value: Any, default: str) -> str:
    return value if isinstance(value, str) and _HEX_COLOR_RE.fullmatch(value) else default


def get_config() -> Dict[str, Any]:
    conf = mw.addonManager.getConfig(__name__) or {}
    merged = copy.deepcopy(DEFAULTS)
    merged.update(conf)
    return merged


def write_config(conf: Dict[str, Any]) -> None:
    mw.addonManager.writeConfig(__name__, conf)
