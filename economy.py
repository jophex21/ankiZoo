from __future__ import annotations

from typing import Any, Dict, List

from . import config, leveling, notify, quests
from .zoo_data import get_zoo_data

GOOD_EASES = (3, 4)  # Good, Easy
AGAIN_HARD_EASES = (1, 2)  # Again, Hard

_UNDO_HISTORY_LIMIT = 200


def _apply_quest_rewards(state, newly_completed: List[Dict[str, Any]]) -> None:
    for quest in newly_completed:
        if quest.get("reward_type") == "animal":
            animal_id = quest.get("reward_animal_id")
            if animal_id and animal_id not in state.owned_animals:
                state.owned_animals.append(animal_id)
                notify.show_toast(
                    "Quest Complete!",
                    f"{quest['label']} — you earned a new animal!",
                    kind="quest",
                )
                continue
        amount = int(quest.get("reward_amount", 0))
        state.coins += amount
        notify.show_toast(
            "Quest Complete!",
            f"{quest['label']} — +{amount} coins!",
            kind="quest",
        )


def on_reviewer_did_answer(reviewer: Any, card: Any, ease: int) -> None:
    conf = config.get_config()
    data = get_zoo_data()
    state = data.state

    was_correct = ease in GOOD_EASES
    xp_delta = int(conf["xpPerCard"]) if was_correct else 0
    coin_delta = int(conf["coinsPerCard"]) if was_correct else 0

    prev_level, _, _ = leveling.collapse_xp(state.total_xp, leveling.get_level_base())
    prev_streak = state.streak_current

    state.total_xp += xp_delta
    state.coins += coin_delta
    state.streak_current = state.streak_current + 1 if was_correct else 0
    state.streak_best = max(state.streak_best, state.streak_current)

    new_level, _, _ = leveling.collapse_xp(state.total_xp, leveling.get_level_base())

    quests.ensure_daily_quests(state, new_level)
    newly_completed: List[Dict[str, Any]] = []
    newly_completed += quests.update_quest_progress(state, "cards", 1)
    if getattr(card, "reps", 0) == 1:
        newly_completed += quests.update_quest_progress(state, "new_cards", 1)
    newly_completed += quests.set_streak_progress(state, state.streak_current)
    newly_completed += quests.check_due_clear_quest(state)

    state.last_undo_xp.append(xp_delta)
    state.last_undo_coins.append(coin_delta)
    if len(state.last_undo_xp) > _UNDO_HISTORY_LIMIT:
        state.last_undo_xp.pop(0)
        state.last_undo_coins.pop(0)

    _apply_quest_rewards(state, newly_completed)

    if new_level > prev_level:
        notify.show_toast("Level Up!", f"You reached level {new_level}!", kind="level_up")

    data.save()
    _refresh_widgets()


def on_state_did_undo(*args: Any) -> None:
    from aqt import mw

    if mw.state != "review":
        return

    data = get_zoo_data()
    state = data.state
    if not state.last_undo_xp:
        return

    xp_delta = state.last_undo_xp.pop()
    coin_delta = state.last_undo_coins.pop()

    state.total_xp = max(0, state.total_xp - xp_delta)
    state.coins = max(0, state.coins - coin_delta)
    # Streak/quest progress is not perfectly rewound on undo -- acceptable
    # simplification; only the XP/coin economy needs to stay exact.

    data.save()
    _refresh_widgets()


def _refresh_widgets() -> None:
    from . import deck_browser_widget, reviewer_widget

    deck_browser_widget.refresh_active_widget()
    reviewer_widget.refresh_active_widget()


def register_hooks() -> None:
    from aqt import gui_hooks

    gui_hooks.reviewer_did_answer_card.append(on_reviewer_did_answer)
    if hasattr(gui_hooks, "state_did_undo"):
        gui_hooks.state_did_undo.append(on_state_did_undo)
