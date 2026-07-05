from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Dict, List

from aqt import mw

from . import animals as animals_module
from . import config
from .zoo_data import QuestData, ZooState

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


def _roll_reward(kind: str, target: int, level: int) -> Dict[str, Any]:
    if kind == "streak":
        return {"reward_type": "coins", "reward_amount": target * 10}
    if kind == "due_clear":
        return {"reward_type": "coins", "reward_amount": 100}

    # 70% coins, 30% a free eligible-but-locked animal (falls back to coins if none available)
    if random.random() < 0.3:
        eligible = [
            a for a in animals_module.get_catalog()
            if a["unlock_level"] <= level
        ]
        if eligible:
            animal = random.choice(eligible)
            return {"reward_type": "animal", "reward_amount": 0, "reward_animal_id": animal["id"]}
    return {"reward_type": "coins", "reward_amount": random.randint(30, 80)}


def _generate_quests(level: int) -> List[Dict[str, Any]]:
    count = int(config.get_config().get("dailyQuestCount", 3))
    templates = random.sample(QUEST_TEMPLATES, k=min(count, len(QUEST_TEMPLATES)))
    quests = []
    for i, template in enumerate(templates):
        target = random.randint(template["min"], template["max"])
        reward = _roll_reward(template["kind"], target, level)
        quests.append({
            "id": f"{template['kind']}_{i}",
            "kind": template["kind"],
            "target": target,
            "progress": 0,
            "completed": False,
            "label": template["label"].format(target=target),
            **reward,
        })
    return quests


def ensure_daily_quests(state: ZooState, level: int) -> List[Dict[str, Any]]:
    today = _today_key()
    if state.quests_date != today or not state.quests:
        state.quests_date = today
        state.quests = _generate_quests(level)
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
