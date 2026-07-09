from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Dict, List

from aqt import mw

from . import config
from .zoo_data import ZooData, ZooState

QUEST_TEMPLATES = [
    {"kind": "cards", "min": 15, "max": 40, "label": "Answer {target} cards"},
    {"kind": "new_cards", "min": 5, "max": 15, "label": "Study {target} new cards"},
    # More than 10 correct in a row is difficult, so the range is capped there.
    {"kind": "streak", "min": 6, "max": 10, "label": "Get {target} correct in a row"},
    # Binary quest (target is always 1): completed by clearing every card
    # currently matching Anki's "is:due" search, not by a counted amount.
    {"kind": "due_clear", "min": 1, "max": 1, "label": "Clear all of today's due cards"},
]


def _today_key() -> str:
    try:
        day_cutoff = mw.col.sched.day_cutoff
        return datetime.fromtimestamp(day_cutoff - 1).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def _generate_quests(level: int) -> List[Dict[str, Any]]:
    # Rewards are no longer decided up front: completing a quest grants a loot
    # box the player opens later (see lootbox.py), so its contents stay hidden.
    count = int(config.get_config().get("dailyQuestCount", 3))
    templates = random.sample(QUEST_TEMPLATES, k=min(count, len(QUEST_TEMPLATES)))
    quests = []
    for i, template in enumerate(templates):
        target = random.randint(template["min"], template["max"])
        quests.append({
            "id": f"{template['kind']}_{i}",
            "kind": template["kind"],
            "target": target,
            "progress": 0,
            "completed": False,
            "claimed": False,       # set once the loot box is opened
            "claimed_reward": None,  # the rolled reward, for display after opening
            "label": template["label"].format(target=target),
        })
    return quests


def ensure_daily_quests(state: ZooState, level: int) -> List[Dict[str, Any]]:
    today = _today_key()
    if state.quests_date != today or not state.quests:
        state.quests_date = today
        state.quests = _generate_quests(level)
    return state.quests


def ensure_daily_quests_and_save(data: ZooData, level: int) -> List[Dict[str, Any]]:
    """Like ensure_daily_quests, but persists immediately if quests were freshly
    generated, so a freshly-rolled set isn't lost if Anki closes before anything
    else triggers a save."""
    state = data.state
    quests_before = state.quests
    ensure_daily_quests(state, level)
    if state.quests is not quests_before:
        data.save()
    return state.quests


def update_quest_progress(state: ZooState, kind: str, amount: int = 1) -> List[Dict[str, Any]]:
    """Increment progress for quests of the given kind. Returns list of newly-completed quests."""
    newly_completed = []
    for quest in state.quests:
        if quest["kind"] != kind or quest["completed"]:
            continue
        quest["progress"] = min(quest["target"], quest["progress"] + amount)
        if quest["progress"] >= quest["target"]:
            quest["completed"] = True
            newly_completed.append(quest)
    return newly_completed


def set_streak_progress(state: ZooState, streak_current: int) -> List[Dict[str, Any]]:
    newly_completed = []
    for quest in state.quests:
        if quest["kind"] != "streak" or quest["completed"]:
            continue
        quest["progress"] = min(quest["target"], streak_current)
        if quest["progress"] >= quest["target"]:
            quest["completed"] = True
            newly_completed.append(quest)
    return newly_completed


def check_due_clear_quest(state: ZooState) -> List[Dict[str, Any]]:
    """Binary quest: completed once no cards match Anki's own "is:due" search.

    Only queries the collection if a due_clear quest exists today and isn't
    already completed, so this is a no-op on the ~1/4 of days it doesn't roll.
    """
    newly_completed = []
    for quest in state.quests:
        if quest["kind"] != "due_clear" or quest["completed"]:
            continue
        try:
            due_count = len(mw.col.find_cards("is:due"))
        except Exception:
            continue
        if due_count == 0:
            quest["progress"] = quest["target"]
            quest["completed"] = True
            newly_completed.append(quest)
    return newly_completed
