from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from aqt import mw
from aqt.qt import QDialog, QVBoxLayout
from aqt.webview import AnkiWebView

from . import animals as animals_module
from . import leveling, quests as quests_module, zoo_logic
from .zoo_data import get_zoo_data

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
GRID_SIZE = 11  # odd so the starting tile can sit dead-center


def _build_payload() -> Dict[str, Any]:
    data = get_zoo_data()
    state = data.state
    base = leveling.get_level_base()
    level, xp_into, xp_next = leveling.collapse_xp(state.total_xp, base)
    # Ensure quests exist even if the dialog is opened before any card has
    # been answered today (economy.py otherwise only generates them lazily
    # on the first answered card). Save immediately so a freshly-generated
    # set isn't lost if the user closes Anki without answering any cards.
    quests_before = state.quests
    quests_module.ensure_daily_quests(state, level)
    if state.quests is not quests_before:
        data.save()
    return {
        "gridSize": GRID_SIZE,
        "ownedTiles": state.owned_tiles,
        "placedAnimals": state.placed_animals,
        "ownedAnimals": state.owned_animals,
        "coins": state.coins,
        "level": level,
        "xpIntoLevel": xp_into,
        "xpToNextLevel": xp_next,
        "rank": leveling.rank_for_level(level),
        "nextTileCost": zoo_logic.tile_cost(len(state.owned_tiles)),
        "catalog": animals_module.get_catalog(),
        "quests": state.quests,
    }


class ZooDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Your Zoo")
        self.resize(1000, 750)
        self.setMinimumSize(700, 500)

        self.web = AnkiWebView(self)
        self.web.set_bridge_command(self._on_bridge_cmd, self)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self.setLayout(layout)

        self.render()

    def render(self) -> None:
        payload = _build_payload()
        data_script = f"<script>window.ANKIZOO_DATA = {json.dumps(payload, ensure_ascii=False)};</script>"

        # Inlined rather than referenced via css=/js= file paths: this sidesteps any
        # MIME-type/path quirk in Anki's /_addons/ static file handler for stylesheets,
        # and matches the inline pattern already proven to work in the deck browser
        # and reviewer widgets.
        css_content = self._read_web_asset("zoo.css")
        js_content = self._read_web_asset("zoo.js")
        head_html = data_script + f"<style>{css_content}</style>"

        body_html = self._read_web_asset("zoo.html") + f"<script>{js_content}</script>"

        self.web.stdHtml(body_html, head=head_html, context=self)

    @staticmethod
    def _read_web_asset(filename: str) -> str:
        path = os.path.join(ADDON_DIR, "web", filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _push_update(self, success: bool, message: str = "") -> None:
        result = {"success": success, "message": message, "payload": _build_payload()}
        script = f"if (window.ankiZooApplyUpdate) window.ankiZooApplyUpdate({json.dumps(result, ensure_ascii=False)});"
        try:
            self.web.eval(script)
        except Exception:
            pass
        if success:
            self._refresh_home_widget()

    def _on_bridge_cmd(self, cmd: str) -> Optional[Any]:
        data = get_zoo_data()
        state = data.state

        if cmd.startswith("buyTile:"):
            try:
                x_str, y_str = cmd.split(":", 1)[1].split(",")
                tile = (int(x_str), int(y_str))
            except Exception:
                self._push_update(False, "Invalid tile.")
                return None

            ok, msg = zoo_logic.can_buy_tile(tile, state.owned_tiles, GRID_SIZE)
            if not ok:
                self._push_update(False, msg)
                return None

            cost = zoo_logic.tile_cost(len(state.owned_tiles))
            if state.coins < cost:
                self._push_update(False, "Not enough coins.")
                return None

            state.coins -= cost
            state.owned_tiles.append([tile[0], tile[1]])
            data.save()
            self._push_update(True, "Tile purchased!")
            return None

        if cmd.startswith("buyAnimal:"):
            animal_id = cmd.split(":", 1)[1]
            try:
                animal = animals_module.get_animal(animal_id)
            except KeyError:
                self._push_update(False, "Unknown animal.")
                return None

            if animal_id in state.owned_animals:
                self._push_update(False, "Already owned.")
                return None

            base = leveling.get_level_base()
            level, _, _ = leveling.collapse_xp(state.total_xp, base)
            if level < animal["unlock_level"]:
                self._push_update(False, f"Requires level {animal['unlock_level']}.")
                return None
            if state.coins < animal["cost_coins"]:
                self._push_update(False, "Not enough coins.")
                return None

            state.coins -= animal["cost_coins"]
            state.owned_animals.append(animal_id)
            data.save()
            self._push_update(True, f"{animal['name']} joined your zoo!")
            return None

        if cmd.startswith("placeAnimal:"):
            try:
                rest = cmd.split(":", 1)[1]
                coords, animal_id = rest.split("|")
                x_str, y_str = coords.split(",")
                tile_key = f"{int(x_str)},{int(y_str)}"
            except Exception:
                self._push_update(False, "Invalid placement.")
                return None

            owned_set = {(t[0], t[1]) for t in state.owned_tiles}
            if (int(x_str), int(y_str)) not in owned_set:
                self._push_update(False, "Tile not owned.")
                return None
            if animal_id not in state.owned_animals:
                self._push_update(False, "Animal not owned.")
                return None
            if tile_key in state.placed_animals:
                self._push_update(False, "Tile already occupied.")
                return None
            if animal_id in state.placed_animals.values():
                self._push_update(False, "Animal already placed elsewhere.")
                return None

            state.placed_animals[tile_key] = animal_id
            data.save()
            self._push_update(True)
            return None

        if cmd.startswith("removeAnimal:"):
            coords = cmd.split(":", 1)[1]
            try:
                x_str, y_str = coords.split(",")
                tile_key = f"{int(x_str)},{int(y_str)}"
            except Exception:
                self._push_update(False, "Invalid tile.")
                return None
            state.placed_animals.pop(tile_key, None)
            data.save()
            self._push_update(True)
            return None

        if cmd == "resetZoo":
            data.reset()
            from . import reviewer_widget
            reviewer_widget.refresh_active_widget()
            self._push_update(True, "All progress has been reset.")
            return None

        return None

    def _refresh_home_widget(self) -> None:
        from . import deck_browser_widget
        deck_browser_widget.refresh_active_widget()


_zoo_dialog: Optional[ZooDialog] = None


def open_zoo_dialog() -> None:
    global _zoo_dialog
    if _zoo_dialog is not None:
        _zoo_dialog.close()
    _zoo_dialog = ZooDialog(mw)
    _zoo_dialog.show()
