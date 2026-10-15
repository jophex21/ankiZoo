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
    "reviewerShowPomodoro": True,
    "reviewerStylePresets": {},
    "reviewerShowHeader": True,
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

REVIEWER_TOGGLE_KEYS = {
    "pomodoro": "reviewerShowPomodoro",
    "header": "reviewerShowHeader",
}

POMODORO_MINUTES_RANGE = (1, 180)

# Reviewer appearance (Pomodoro circle + level chip). One entry drives the
# default, validation, the Settings-tab row, and the CSS variable
# `--az-<key>` injected into the reviewer (see reviewer_widget._style_vars_css).
# Colors accept #RRGGBB or #RRGGBBAA; "" means "follow Anki's theme".
_DIM_CHOICES = [("never", "Never"), ("running", "While running"),
                ("idle", "When not running"), ("always", "Always")]
REVIEWER_STYLE = [
    # key,                group,  kind,     default,     label,                   extra
    ("pomodoroTimeFormat", "pomo", "choice", "mmss", "Time display",
     [("mmss", "Minutes and seconds (24:59)"), ("mm", "Minutes only (25m)")]),
    ("pomodoroDim",        "pomo", "choice", "idle",      "Dim timer",            _DIM_CHOICES),
    ("pomodoroDimOpacity", "pomo", "int",    35,          "Dimmed opacity",       (5, 100, "%")),
    ("pomodoroSizePx",     "pomo", "int",    40,          "Circle size",          (24, 96, "px")),
    ("pomodoroFontPx",     "pomo", "int",    11,          "Text size",            (7, 32, "px")),
    ("pomodoroRingPx",     "pomo", "int",    3,           "Ring thickness",       (1, 12, "px")),
    ("pomodoroOffsetPx",   "pomo", "int",    14,          "Distance from corner", (0, 80, "px")),
    ("pomodoroRingColor",  "pomo", "color",  "#6fbf73",   "Ring color",           None),
    ("pomodoroTrackColor", "pomo", "color",  "",          "Ring track color",     None),
    ("pomodoroBgColor",    "pomo", "color",  "",          "Background color",     None),
    ("pomodoroTextColor",  "pomo", "color",  "",          "Text color",           None),
    ("pomodoroStartColor", "pomo", "color",  "#3f9142",   "Start button color",   None),
    ("pomodoroCancelColor", "pomo", "color", "#8a3f3f",   "Cancel button color",  None),
    # Popup menu: blank = match the timer circle's colors.
    ("pomodoroMenuBgColor", "pomo", "color", "",          "Menu background color", None),
    ("pomodoroMenuBorderColor", "pomo", "color", "",      "Menu border color",    None),
    ("pomodoroMenuTextColor", "pomo", "color", "",        "Menu text color",      None),
    ("pomodoroButtonTextColor", "pomo", "color", "#ffffff", "Menu button text color", None),
    ("chipWidthPx",        "chip", "int",    230,         "Width",                (120, 480, "px")),
    ("chipHeightPx",       "chip", "int",    28,          "Height",               (18, 60, "px")),
    ("chipFontPx",         "chip", "int",    12,          "Text size",            (8, 24, "px")),
    ("chipPaddingPx",      "chip", "int",    10,          "Inner padding",        (0, 30, "px")),
    ("chipRadiusPx",       "chip", "int",    12,          "Corner radius",        (0, 30, "px")),
    ("chipOffsetPx",       "chip", "int",    20,          "Distance from corner", (0, 80, "px")),
    ("chipOpacity",        "chip", "int",    100,         "Opacity",              (10, 100, "%")),
    ("chipBgColor",        "chip", "color",  "#00000033", "Background color",     None),
    ("chipBorderColor",    "chip", "color",  "#ffffff1a", "Border color",         None),
    ("chipBarStartColor",  "chip", "color",  "#6fbf73",   "XP bar start color",   None),
    ("chipBarEndColor",    "chip", "color",  "#3f9142",   "XP bar end color",     None),
    ("chipTextColor",      "chip", "color",  "#ffffff",   "Text color",           None),
    ("chipCoinsColor",     "chip", "color",  "#f2c96a",   "Coins color",          None),
    # Zoo window (zoo_dialog). Blank = follow Anki's theme.
    ("zooBgColor",         "zoo",  "color",  "",          "Window background",    None),
    ("zooPanelColor",      "zoo",  "color",  "",          "Cards & popups",       None),
    ("zooTextColor",       "zoo",  "color",  "",          "Text color",           None),
    ("zooBorderColor",     "zoo",  "color",  "",          "Border color",         None),
    ("zooHeaderColor",     "zoo",  "color",  "#3f5240",   "Header color",         None),
    ("zooHeaderDarkColor", "zoo",  "color",  "#2f4029",   "Header shade & tab bar", None),
    ("zooHeaderTextColor", "zoo",  "color",  "#fdf6ed",   "Header text & active tab", None),
    ("zooAccentColor",     "zoo",  "color",  "#778873",   "Accent color",         None),
    ("zooAccentLightColor", "zoo", "color",  "#a1bc98",   "Highlight & XP bar",   None),
    ("zooSkillColor",      "zoo",  "color",  "#ffe08a",   "Skill points color",   None),
    ("zooMapPaperColor",   "zoo",  "color",  "#dcc7a0",   "Map paper color",      None),
    ("zooMapGrassColor",   "zoo",  "color",  "#a9d178",   "Map grass color",      None),
    ("zooExhibitBlurPx",   "zoo",  "int",    0,           "Exhibit background blur", (0, 10, "px")),
]
REVIEWER_STYLE_BY_KEY = {f[0]: f for f in REVIEWER_STYLE}
DEFAULTS.update({f[0]: f[3] for f in REVIEWER_STYLE})

_STYLE_COLOR_RE = re.compile(r"^(#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?)?$")


def validate_style_value(key: str, raw: Any) -> Any:
    """Coerce a Settings-tab value for a REVIEWER_STYLE key; None if invalid."""
    field = REVIEWER_STYLE_BY_KEY.get(key)
    if not field:
        return None
    _, _, kind, _, _, extra = field
    if kind == "int":
        lo, hi, _unit = extra
        try:
            return max(lo, min(hi, int(raw)))
        except (TypeError, ValueError):
            return None
    if kind == "choice":
        return raw if raw in {v for v, _ in extra} else None
    return raw.lower() if isinstance(raw, str) and _STYLE_COLOR_RE.fullmatch(raw) else None


def style_vars_css(conf: Dict[str, Any], groups: tuple) -> str:
    """`:root { --az-<key>: ... }` for REVIEWER_STYLE keys in `groups`.
    Choice keys and empty colors are skipped so CSS fallbacks apply."""
    values = style_values(conf)
    decls = []
    for key, group, kind, _, _, extra in REVIEWER_STYLE:
        value = values[key]
        if group not in groups or kind == "choice" or value == "":
            continue
        if kind == "int":
            value = f"{value / 100:g}" if extra[2] == "%" else f"{value}{extra[2]}"
        decls.append(f"--az-{key}: {value};")
    return ":root { " + " ".join(decls) + " }"


def style_values(conf: Dict[str, Any]) -> Dict[str, Any]:
    """Current reviewer style, with bad/missing entries falling back to defaults."""
    out = {}
    for key, _, _, default, _, _ in REVIEWER_STYLE:
        value = validate_style_value(key, conf.get(key, default))
        out[key] = default if value is None else value
    return out

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
