from __future__ import annotations

import json
import os
import random
from typing import Any, Dict, Optional

from aqt import mw
from aqt.qt import QColor, QColorDialog, QDialog, QVBoxLayout
from aqt.webview import AnkiWebView

from . import animals as animals_module
from . import config as config_module
from . import leveling, lootbox, quests as quests_module, sprite_render, zoo_logic
from .zoo_data import ADDON_DIR, get_zoo_data

GRID_SIZE = 11  # odd so the starting tile can sit dead-center

# The rank badge art is one sprite sheet: a 10x5 grid of 50 shield badges read
# left-to-right, top-to-bottom, so cell index N corresponds to level N+1. The
# header shows the current level's cell via CSS background-position (see zoo.js).
RANK_BADGE_PATH = os.path.join(ADDON_DIR, "sprites", "rank_upgrade_sprite_sheet.png")
RANK_BADGE_COLS = 10
RANK_BADGE_ROWS = 5


def _build_payload() -> Dict[str, Any]:
    data = get_zoo_data()
    state = data.state
    progress = leveling.get_progress(state.total_xp)
    level = progress.level
    # Ensure quests exist even if the dialog is opened before any card has
    # been answered today (economy.py otherwise only generates them lazily
    # on the first answered card).
    quests_module.ensure_daily_quests_and_save(data, level)

    biomes_in_use = {t["biome"] for t in state.tile_terrain.values()}
    terrain_images = {}
    for biome in biomes_in_use:
        uri = animals_module.get_terrain_data_uri(biome)
        if uri:
            w, h = animals_module.get_terrain_size(biome)
            terrain_images[biome] = {"uri": uri, "w": w, "h": h}

    rank_badge_uri = (
        sprite_render.file_data_uri(RANK_BADGE_PATH)
        if os.path.isfile(RANK_BADGE_PATH)
        else None
    )

    conf = config_module.get_config()
    widget_colors = {
        short_key: config_module.valid_hex_color(conf.get(conf_key), config_module.DEFAULTS[conf_key])
        for short_key, conf_key in config_module.WIDGET_COLOR_KEYS.items()
    }

    return {
        "gridSize": GRID_SIZE,
        "ownedTiles": state.owned_tiles,
        "placedAnimals": state.placed_animals,
        "tileTerrain": state.tile_terrain,
        "terrainImages": terrain_images,
        "fenceUri": sprite_render.FENCE_DATA_URI,
        "unlockedAnimals": state.unlocked_animals,
        "ownedAnimals": state.owned_animals,
        "coins": state.coins,
        "skillPoints": animals_module.available_points(level, state.unlocked_animals, state.pretree_animals, state.bonus_skill_points),
        "biomeStars": animals_module.biome_stars(state.unlocked_animals),
        "pointsPerLevel": animals_module.POINTS_PER_LEVEL,
        "biomeColors": animals_module.BIOME_COLORS,
        "biomeOrder": animals_module.BIOME_ORDER,
        "level": level,
        "xpIntoLevel": progress.xp_into,
        "xpToNextLevel": progress.xp_next,
        "rank": progress.rank,
        "nextTileCost": zoo_logic.tile_cost(len(state.owned_tiles)),
        "catalog": animals_module.get_catalog(),
        "quests": state.quests,
        "rarityColors": lootbox.RARITY_COLORS,
        "rarityLabels": lootbox.RARITY_LABEL,
        "widgetColors": widget_colors,
        "rankBadgeUri": rank_badge_uri,
        "rankBadgeCols": RANK_BADGE_COLS,
        "rankBadgeRows": RANK_BADGE_ROWS,
    }


class ZooDialog(QDialog):
    def __init__(self, parent, initial_tab: str = "zoo"):
        super().__init__(parent)
        self.setWindowTitle("Your Zoo")
        self.resize(1000, 750)
        self.setMinimumSize(700, 500)
        self.initial_tab = initial_tab

        self.web = AnkiWebView(self)
        self.web.set_bridge_command(self._on_bridge_cmd, self)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self.setLayout(layout)

        self.render()

    def render(self) -> None:
        payload = _build_payload()
        payload["initialTab"] = self.initial_tab
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

    def _push_update(self, success: bool, message: str = "", loot: Optional[Dict[str, Any]] = None) -> None:
        result = {"success": success, "message": message, "payload": _build_payload(), "loot": loot}
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

        if cmd.startswith("unlockAnimal:"):
            animal_id = cmd.split(":", 1)[1]
            try:
                animal = animals_module.get_animal(animal_id)
            except KeyError:
                self._push_update(False, "Unknown animal.")
                return None

            if animal_id in state.unlocked_animals:
                self._push_update(False, "Already unlocked.")
                return None

            if not animals_module.tier_accessible(animal, state.unlocked_animals):
                self._push_update(
                    False,
                    f"Earn {animal['tier_threshold']}★ in {animal['biome']} to unlock {animal['tier_name']} animals.",
                )
                return None

            level = leveling.get_progress(state.total_xp).level
            available = animals_module.available_points(level, state.unlocked_animals, state.pretree_animals, state.bonus_skill_points)
            if available < animal["skill_cost"]:
                self._push_update(False, "Not enough skill points.")
                return None

            # Skill points are derived from level minus spent, so appending the
            # animal (which raises points_spent) is what "spends" the points.
            state.unlocked_animals.append(animal_id)
            data.save()
            self._push_update(True, f"{animal['name']} unlocked! Buy it with coins to add it to your zoo.")
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
            if animal_id not in state.unlocked_animals:
                self._push_update(False, "Unlock it in the skill tree first.")
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
            biome = animals_module.get_animal(animal_id)["biome"]
            w, h = animals_module.get_terrain_size(biome)
            state.tile_terrain[tile_key] = {
                "biome": biome,
                "ox": random.randint(0, max(0, w - 32)),
                "oy": random.randint(0, max(0, h - 32)),
            }
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

        if cmd.startswith("claimQuest:"):
            quest_id = cmd.split(":", 1)[1]
            quest = next((q for q in state.quests if q.get("id") == quest_id), None)
            if quest is None:
                self._push_update(False, "Quest not found.")
                return None
            if not quest.get("completed"):
                self._push_update(False, "Finish the quest first.")
                return None
            if quest.get("claimed"):
                self._push_update(False, "Loot box already opened.")
                return None

            reward = lootbox.roll_reward(state)
            lootbox.apply_reward(state, reward)
            quest["claimed"] = True
            quest["claimed_reward"] = reward
            data.save()
            self._refresh_home_widget()
            from . import reviewer_widget
            reviewer_widget.refresh_active_widget()
            # The reward is applied immediately; JS plays the reveal animation from
            # the `loot` field so nothing is lost if the window closes mid-spin.
            self._push_update(True, loot={"questId": quest_id, "reward": reward})
            return None

        if cmd == "resetZoo":
            data.reset()
            from . import reviewer_widget
            reviewer_widget.refresh_active_widget()
            self._push_update(True, "All progress has been reset.")
            return None

        if cmd.startswith("setWidgetColor:"):
            try:
                _, short_key, value = cmd.split(":", 2)
            except ValueError:
                return None
            conf_key = config_module.WIDGET_COLOR_KEYS.get(short_key)
            if conf_key and config_module.valid_hex_color(value, "") == value:
                conf = config_module.get_config()
                conf[conf_key] = value
                config_module.write_config(conf)
                self._push_update(True)
            return None

        if cmd.startswith("pickWidgetColor:"):
            short_key = cmd.split(":", 1)[1]
            conf_key = config_module.WIDGET_COLOR_KEYS.get(short_key)
            if not conf_key:
                return None
            conf = config_module.get_config()
            current = config_module.valid_hex_color(conf.get(conf_key), config_module.DEFAULTS[conf_key])
            # QColorDialog is Qt's own native dialog (same as Interactive Heatmap's
            # color pickers) -- unlike an HTML <input type="color">, it doesn't route
            # through Chromium's separate color-management stack, which was producing
            # inaccurate colors compared to what the user actually picked.
            color = QColorDialog.getColor(QColor(current), self, "Choose a color")
            if color.isValid():
                conf[conf_key] = color.name()
                config_module.write_config(conf)
                self._push_update(True)
            return None

        return None

    def _refresh_home_widget(self) -> None:
        from . import deck_browser_widget
        deck_browser_widget.refresh_active_widget()


_zoo_dialog: Optional[ZooDialog] = None


def open_zoo_dialog(initial_tab: str = "zoo") -> None:
    global _zoo_dialog
    if _zoo_dialog is not None:
        _zoo_dialog.close()
    _zoo_dialog = ZooDialog(mw, initial_tab=initial_tab)
    _zoo_dialog.show()
