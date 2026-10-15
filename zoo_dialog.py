from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from aqt import mw
from aqt.qt import QColor, QColorDialog, QDialog, QVBoxLayout
from aqt.webview import AnkiWebView

from . import animals as animals_module
from . import config as config_module
from . import leveling, lootbox, quests as quests_module, sprite_render, zoo_logic
from .zoo_data import ADDON_DIR, get_zoo_data

GRID_SIZE = 11  # legacy; kept for the retired buyTile/grid path
BUILDING_SLOTS = 20  # square building plots reserved in the central Plaza (art pending)

# The rank badge art is one sprite sheet: a 10x5 grid of 50 shield badges read
# left-to-right, top-to-bottom, so cell index N corresponds to level N+1. The
# header shows the current level's cell via CSS background-position (see zoo.js).
RANK_BADGE_PATH = os.path.join(ADDON_DIR, "sprites", "rank_upgrade_sprite_sheet.png")
RANK_BADGE_COLS = 10
RANK_BADGE_ROWS = 5

COIN_ICON_PATH = os.path.join(ADDON_DIR, "sprites", "assets", "coin.png")
_coin_uri_cache: Optional[str] = None


def _coin_data_uri() -> Optional[str]:
    """The coin sprite, downscaled once and cached (the source is multi-MB)."""
    global _coin_uri_cache
    if _coin_uri_cache is None and os.path.isfile(COIN_ICON_PATH):
        _coin_uri_cache = sprite_render.scaled_png_data_uri(COIN_ICON_PATH, 64)
    return _coin_uri_cache


def _build_payload() -> Dict[str, Any]:
    data = get_zoo_data()
    state = data.state
    progress = leveling.get_progress(state.total_xp)
    level = progress.level
    # Ensure quests exist even if the dialog is opened before any card has
    # been answered today (economy.py otherwise only generates them lazily
    # on the first answered card).
    quests_module.ensure_daily_quests_and_save(data, level)

    # Terrain is only shipped for districts that actually have a filled plot
    # (some terrain PNGs are large); the district biome is the plot-id prefix.
    biomes_in_use = {plot_id.rsplit("-", 1)[0] for plot_id in state.plot_animals}
    terrain_images = {}
    for biome in biomes_in_use:
        uri = animals_module.get_terrain_data_uri(biome)
        if uri:
            terrain_images[biome] = {"uri": uri}

    rank_badge_uri = (
        sprite_render.file_data_uri(RANK_BADGE_PATH)
        if os.path.isfile(RANK_BADGE_PATH)
        else None
    )
    coin_uri = _coin_data_uri()

    conf = config_module.get_config()
    widget_colors = {
        short_key: config_module.valid_hex_color(conf.get(conf_key), config_module.DEFAULTS[conf_key])
        for short_key, conf_key in config_module.WIDGET_COLOR_KEYS.items()
    }

    return {
        "unlockedPlots": state.unlocked_plots,
        "plotAnimals": state.plot_animals,
        "nextPlotCost": zoo_logic.tile_cost(len(state.unlocked_plots)),
        "buildingSlots": BUILDING_SLOTS,
        "terrainImages": terrain_images,
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
        "catalog": animals_module.get_catalog(),
        "quests": state.quests,
        "rarityColors": lootbox.RARITY_COLORS,
        "rarityLabels": lootbox.RARITY_LABEL,
        "widgetColors": widget_colors,
        "pomodoroMinutes": conf.get("pomodoroMinutes", config_module.DEFAULTS["pomodoroMinutes"]),
        "reviewerStyle": {
            "schema": [
                {"key": k, "group": g, "kind": kind, "label": label, "extra": extra}
                for k, g, kind, _, label, extra in config_module.REVIEWER_STYLE
            ],
            "values": config_module.style_values(conf),
            "presets": sorted((conf.get("reviewerStylePresets") or {}).keys(), key=str.lower),
        },
        "reviewerToggles": {k: bool(conf.get(v, True)) for k, v in config_module.REVIEWER_TOGGLE_KEYS.items()},
        "rankBadgeUri": rank_badge_uri,
        "rankBadgeCols": RANK_BADGE_COLS,
        "rankBadgeRows": RANK_BADGE_ROWS,
        "coinUri": coin_uri,
    }


def _qcolor_from_hex(value: str) -> QColor:
    """#RRGGBB[AA] -> QColor (Qt reads 8-digit hex as #AARRGGBB, so reorder)."""
    if len(value) == 9:
        value = "#" + value[7:9] + value[1:7]
    return QColor(value) if value else QColor("#ffffff")


def _hex_from_qcolor(color: QColor) -> str:
    """QColor -> CSS #RRGGBB, or #RRGGBBAA when not fully opaque."""
    rgb = color.name()
    return rgb if color.alpha() == 255 else f"{rgb}{color.alpha():02x}"


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
        zoo_vars = config_module.style_vars_css(config_module.get_config(), ("zoo",))
        head_html = data_script + f"<style>{css_content}</style><style>{zoo_vars}</style>"

        body_html = self._read_web_asset("zoo.html") + f"<script>{js_content}</script>"

        self.web.stdHtml(body_html, head=head_html, context=self)

    @staticmethod
    def _read_web_asset(filename: str) -> str:
        path = os.path.join(ADDON_DIR, "web", filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _biome_animal_count(biome: str) -> int:
        return sum(1 for a in animals_module.get_catalog() if a["biome"] == biome)

    def _validate_frontier_plot(self, plot_id: str, state) -> tuple:
        """A plot is unlockable only if it's the next unopened plot in its district
        (districts fill left-to-right, so index N needs the N plots before it open)."""
        try:
            biome, idx_str = plot_id.rsplit("-", 1)
            idx = int(idx_str)
        except Exception:
            return False, "Invalid plot."
        if biome not in animals_module.BIOME_ORDER:
            return False, "Invalid plot."
        if idx < 0 or idx >= self._biome_animal_count(biome):
            return False, "Invalid plot."
        if plot_id in state.unlocked_plots:
            return False, "Plot already cleared."
        unlocked_in_biome = sum(1 for p in state.unlocked_plots if p.rsplit("-", 1)[0] == biome)
        if idx != unlocked_in_biome:
            return False, "Clear the earlier plots in this area first."
        return True, ""

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

        if cmd.startswith("unlockPlot:"):
            plot_id = cmd.split(":", 1)[1]
            ok, msg = self._validate_frontier_plot(plot_id, state)
            if not ok:
                self._push_update(False, msg)
                return None
            cost = zoo_logic.tile_cost(len(state.unlocked_plots))
            if state.coins < cost:
                self._push_update(False, "Not enough coins.")
                return None
            state.coins -= cost
            state.unlocked_plots.append(plot_id)
            data.save()
            self._push_update(True, "Plot cleared -- place an animal here.")
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

            level = leveling.get_progress(state.total_xp).level
            if not animals_module.tier_accessible(animal, state.unlocked_animals, level):
                if animal["conservation"] == "EX" and level < animal["min_level"]:
                    self._push_update(
                        False,
                        f"Reach level {animal['min_level']} to unlock Extinct animals in {animal['biome']}.",
                    )
                else:
                    self._push_update(
                        False,
                        f"Earn {animal['tier_threshold']}★ in {animal['biome']} to unlock {animal['tier_name']} animals.",
                    )
                return None

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
                plot_id, animal_id = cmd.split(":", 1)[1].split("|")
            except Exception:
                self._push_update(False, "Invalid placement.")
                return None

            if plot_id not in state.unlocked_plots:
                self._push_update(False, "Clear this plot first.")
                return None
            if animal_id not in state.owned_animals:
                self._push_update(False, "Animal not owned.")
                return None
            if plot_id in state.plot_animals:
                self._push_update(False, "Plot already occupied.")
                return None
            if animal_id in state.plot_animals.values():
                self._push_update(False, "Animal already placed elsewhere.")
                return None

            state.plot_animals[plot_id] = animal_id
            data.save()
            self._push_update(True)
            return None

        if cmd.startswith("removeAnimal:"):
            plot_id = cmd.split(":", 1)[1]
            state.plot_animals.pop(plot_id, None)
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

        if cmd.startswith("setReviewerToggle:"):
            try:
                _, short_key, value = cmd.split(":", 2)
            except ValueError:
                return None
            conf_key = config_module.REVIEWER_TOGGLE_KEYS.get(short_key)
            if conf_key:
                conf = config_module.get_config()
                conf[conf_key] = value == "1"
                config_module.write_config(conf)
                from . import reviewer_widget
                reviewer_widget.apply_visibility()
                self._push_update(True)
            return None

        if cmd.startswith("setPomodoroMinutes:"):
            lo, hi = config_module.POMODORO_MINUTES_RANGE
            try:
                minutes = max(lo, min(hi, int(cmd.split(":", 1)[1])))
            except ValueError:
                return None
            conf = config_module.get_config()
            conf["pomodoroMinutes"] = minutes
            config_module.write_config(conf)
            from . import reviewer_widget
            reviewer_widget._reload_reviewer_widget()
            self._push_update(True)
            return None

        if cmd.startswith("reviewerStyle:"):
            self._on_reviewer_style(cmd.split(":", 1)[1])
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

    def _on_reviewer_style(self, raw: str) -> None:
        """Settings-tab appearance actions: set / pick / reset / presets."""
        try:
            req = json.loads(raw)
            action = req["action"]
        except (ValueError, KeyError, TypeError):
            return
        conf = config_module.get_config()
        presets = dict(conf.get("reviewerStylePresets") or {})
        message = ""

        if action == "set":
            value = config_module.validate_style_value(req.get("key"), req.get("value"))
            if value is None:
                self._push_update(False, "Invalid value.")
                return
            conf[req["key"]] = value
        elif action == "pick":
            key = req.get("key")
            if config_module.REVIEWER_STYLE_BY_KEY.get(key, (None, None, None))[2] != "color":
                return
            current = config_module.style_values(conf)[key]
            color = QColorDialog.getColor(
                _qcolor_from_hex(current), self, "Choose a color",
                QColorDialog.ColorDialogOption.ShowAlphaChannel,
            )
            if not color.isValid():
                return
            conf[key] = _hex_from_qcolor(color)
        elif action == "reset":
            for key, _, _, default, _, _ in config_module.REVIEWER_STYLE:
                conf[key] = default
            message = "Appearance reset to defaults."
        elif action == "savePreset":
            name = str(req.get("name", "")).strip()[:40]
            if not name:
                self._push_update(False, "Give the preset a name first.")
                return
            presets[name] = config_module.style_values(conf)
            conf["reviewerStylePresets"] = presets
            message = f"Saved preset \u201c{name}\u201d."
        elif action == "loadPreset":
            preset = presets.get(req.get("name"))
            if not isinstance(preset, dict):
                return
            for key, value in preset.items():
                value = config_module.validate_style_value(key, value)
                if value is not None:
                    conf[key] = value
            message = f"Loaded preset \u201c{req['name']}\u201d."
        elif action == "deletePreset":
            if presets.pop(req.get("name"), None) is None:
                return
            conf["reviewerStylePresets"] = presets
            message = f"Deleted preset \u201c{req['name']}\u201d."
        else:
            return

        config_module.write_config(conf)
        from . import reviewer_widget
        reviewer_widget.apply_style()
        self._push_update(True, message)

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
