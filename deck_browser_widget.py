from __future__ import annotations

import html
import json
import os
from typing import Any

from aqt import mw
from aqt.deckbrowser import DeckBrowser

from . import animals as animals_module
from . import config as config_module
from . import leveling
from . import quests as quests_module
from . import sprite_render
from .zoo_data import get_zoo_data

RANK_SPRITE_COLS = 10
RANK_SPRITE_ROWS = 5
RANK_SPRITE_MAX_LEVEL = RANK_SPRITE_COLS * RANK_SPRITE_ROWS
ASSETS_DIR = os.path.join(animals_module.SPRITES_DIR, "assets")

TOAST_ASSETS = """
<style>
.ankizoo-toast-container { position: fixed; top: 14px; right: 14px; z-index: 9999; display: flex; flex-direction: column; gap: 8px; }
.ankizoo-toast { background: #2b2f36; color: #f2f2f2; border-radius: 10px; padding: 10px 14px; min-width: 200px; max-width: 280px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.35); font-family: -apple-system, sans-serif; font-size: 13px; opacity: 0; transform: translateY(-8px);
    transition: opacity 0.2s ease, transform 0.2s ease; }
.ankizoo-toast.show { opacity: 1; transform: translateY(0); }
.ankizoo-toast .az-title { font-weight: 700; margin-bottom: 2px; }
.ankizoo-toast .az-desc { opacity: 0.85; }
</style>
<script>
window.AnkiZooToast = window.AnkiZooToast || {
    show: function(payload) {
        let container = document.getElementById('ankizoo-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'ankizoo-toast-container';
            container.className = 'ankizoo-toast-container';
            document.body.appendChild(container);
        }
        const el = document.createElement('div');
        el.className = 'ankizoo-toast';
        el.innerHTML = '<div class="az-title"></div><div class="az-desc"></div>';
        el.querySelector('.az-title').textContent = payload.title || '';
        el.querySelector('.az-desc').textContent = payload.description || '';
        container.appendChild(el);
        requestAnimationFrame(() => el.classList.add('show'));
        setTimeout(() => {
            el.classList.remove('show');
            setTimeout(() => el.remove(), 250);
        }, 3500);
    }
};
</script>
"""

WIDGET_CSS = """
<style>
.ankizoo-widget { position: relative; display: flex; background: var(--az-bg, #1f232b);
    border: 2px solid var(--az-border, #3f9142); border-radius: 14px; padding: 10px 14px; margin: 12px auto; width: 100%; max-width: 720px;
    box-sizing: border-box; overflow: hidden; cursor: pointer; font-family: -apple-system, sans-serif; user-select: none; }
.ankizoo-widget .az-settings-btn { position: absolute; top: 6px; right: 8px; font-size: 14px;
    opacity: 0.6; cursor: pointer; line-height: 1; }
.ankizoo-widget .az-settings-btn:hover { opacity: 1; }
.ankizoo-widget .az-gate-pane { display: flex; align-items: center; justify-content: center; width: 54px;
    flex-shrink: 0; border-right: 1px solid var(--az-divider, #3f9142); margin-right: 12px; padding-right: 12px; }
.ankizoo-widget .az-gate-pane img { width: 44px; height: 44px; object-fit: contain; }
.ankizoo-widget .az-info { flex: 1; min-width: 0; }
.ankizoo-widget .az-title-row { display: flex; align-items: center; gap: 10px; }
.ankizoo-widget .az-rank-icon { width: 52px; height: 52px; background-repeat: no-repeat;
    background-size: 1000% 500%; image-rendering: pixelated; flex-shrink: 0; }
.ankizoo-widget .az-title-stack { flex: 1; min-width: 0; }
.ankizoo-widget .az-rank-level-row { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.ankizoo-widget .az-rank { font-weight: 700; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ankizoo-widget .az-level { font-weight: 800; font-size: 15px; white-space: nowrap; flex-shrink: 0; }
.ankizoo-widget .az-bar-row { display: flex; align-items: center; gap: 6px; margin-top: 5px; }
.ankizoo-widget .az-bar { flex: 1; height: 7px; border-radius: 999px; background: rgba(120,120,120,0.25); overflow: hidden; }
.ankizoo-widget .az-bar-fill { height: 100%; background: var(--az-xpbar, #6fbf73); }
.ankizoo-widget .az-xp-label { font-size: 10px; opacity: 0.85; white-space: nowrap; }
.ankizoo-widget .az-bottom-row { display: flex; gap: 10px; margin-top: 8px; }
.ankizoo-widget .az-stats-col { display: flex; flex-direction: column; gap: 4px; font-size: 10px; flex-shrink: 0; }
.ankizoo-widget .az-stats-col .az-quest-count { font-weight: 700; }
.ankizoo-widget .az-coin-icon { width: 11px; height: 11px; vertical-align: middle; margin-right: 2px; }
.ankizoo-widget .az-quest-list { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.ankizoo-widget .az-quest-row { display: flex; justify-content: space-between; align-items: center; gap: 6px;
    padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,0.08); font-size: 10px; }
.ankizoo-widget .az-quest-row:last-child { border-bottom: none; }
.ankizoo-widget .az-quest-row .az-quest-label { font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ankizoo-widget .az-quest-status { font-weight: 700; white-space: nowrap; }
.ankizoo-widget .az-quest-status.done { color: var(--az-questdone, #6fbf73); }
.ankizoo-widget .az-quest-status.pending { opacity: 0.7; font-weight: 400; }
.ankizoo-widget .az-quests-empty { font-size: 10px; opacity: 0.6; }
</style>
"""


_rank_sprite_uri_cache: str | None = None


def _rank_sprite_uri() -> str:
    global _rank_sprite_uri_cache
    if _rank_sprite_uri_cache is None:
        path = os.path.join(animals_module.SPRITES_DIR, "rank_upgrade_sprite_sheet.png")
        _rank_sprite_uri_cache = sprite_render.file_data_uri(path)
    return _rank_sprite_uri_cache


def _rank_icon_position(level: int) -> str:
    """CSS background-position for the level's cell in the uniform 10x5 sheet."""
    idx = max(1, min(RANK_SPRITE_MAX_LEVEL, level)) - 1
    col, row = idx % RANK_SPRITE_COLS, idx // RANK_SPRITE_COLS
    x = col / (RANK_SPRITE_COLS - 1) * 100
    y = row / (RANK_SPRITE_ROWS - 1) * 100
    return f"{x:.4f}% {y:.4f}%"


_asset_uri_cache: dict[str, str] = {}


def _asset_uri(filename: str) -> str:
    if filename not in _asset_uri_cache:
        _asset_uri_cache[filename] = sprite_render.file_data_uri(os.path.join(ASSETS_DIR, filename))
    return _asset_uri_cache[filename]


def _widget_style_vars() -> str:
    conf = config_module.get_config()
    parts = []
    for short_key, conf_key in config_module.WIDGET_COLOR_KEYS.items():
        value = config_module.valid_hex_color(conf.get(conf_key), config_module.DEFAULTS[conf_key])
        parts.append(f"--az-{short_key.lower()}:{value};")
    return " ".join(parts)


def _quest_rows_html(quest_list: list) -> str:
    if not quest_list:
        return '<div class="az-quests-empty">No quests yet -- answer a few cards to roll today\'s quests.</div>'
    rows = []
    for q in quest_list:
        if q.get("completed"):
            status = '<span class="az-quest-status done">✓ Done</span>'
        else:
            status = f'<span class="az-quest-status pending">{q.get("progress", 0)}/{q.get("target", 1)}</span>'
        rows.append(
            f'<div class="az-quest-row"><span class="az-quest-label">{html.escape(q.get("label", ""))}</span>{status}</div>'
        )
    return "".join(rows)


def _card_inner_html(state, progress: leveling.Progress) -> str:
    level, rank, percent = progress.level, progress.rank, progress.percent
    owned_count = len(state.owned_animals)
    total_count = len(animals_module.get_catalog())
    quests_done = sum(1 for q in state.quests if q.get("completed"))
    quests_total = len(state.quests)

    return f"""
        <span class="az-settings-btn" id="az-settings-btn" title="Settings"
            onclick="event.stopPropagation(); pycmd('ankiZoo_openSettings')">⚙</span>
        <div class="az-gate-pane"><img src="{_asset_uri('zoo_icon.png')}" alt="Zoo"></div>
        <div class="az-info">
            <div class="az-title-row">
                <span class="az-rank-icon" id="az-rank-icon" style="background-image:url({_rank_sprite_uri()}); background-position:{_rank_icon_position(level)};"></span>
                <div class="az-title-stack">
                    <div class="az-rank-level-row">
                        <span class="az-rank" id="az-rank">{html.escape(rank)}</span>
                        <span class="az-level" id="az-level">Lv. {level}</span>
                    </div>
                    <div class="az-bar-row">
                        <div class="az-bar"><div class="az-bar-fill" id="az-bar-fill" style="width: {percent}%;"></div></div>
                        <span class="az-xp-label" id="az-xp-label">{progress.xp_into}/{progress.xp_next} XP</span>
                    </div>
                </div>
            </div>
            <div class="az-bottom-row">
                <div class="az-stats-col">
                    <span class="az-quest-count" id="az-quest-count">Quests: {quests_done}/{quests_total}</span>
                    <span id="az-animals">\U0001F43E {owned_count} / {total_count}</span>
                    <span id="az-coins"><img class="az-coin-icon" src="{_asset_uri('coin.png')}" alt="">{state.coins}</span>
                </div>
                <div class="az-quest-list" id="az-quest-list">{_quest_rows_html(state.quests)}</div>
            </div>
        </div>
    """


def get_widget_html() -> str:
    data = get_zoo_data()
    state = data.state
    progress = leveling.get_progress(state.total_xp)
    quests_module.ensure_daily_quests_and_save(data, progress.level)

    return f"""
    {TOAST_ASSETS}
    {WIDGET_CSS}
    <div class="ankizoo-widget" id="ankizoo-widget" style="{_widget_style_vars()}" onclick="pycmd('ankiZoo_openZoo')">
        {_card_inner_html(state, progress)}
    </div>
    """


def _on_will_render_content(deck_browser: DeckBrowser, content: Any) -> None:
    try:
        content.stats += get_widget_html()
    except Exception as e:
        print(f"ankiZoo: error rendering deck browser widget: {e}")


def refresh_active_widget() -> None:
    data = get_zoo_data()
    state = data.state
    progress = leveling.get_progress(state.total_xp)
    quests_module.ensure_daily_quests_and_save(data, progress.level)

    inner_html = _card_inner_html(state, progress)
    style_vars = _widget_style_vars()
    script = f"""
    (function() {{
        const el = document.getElementById('ankizoo-widget');
        if (el) {{
            el.innerHTML = {json.dumps(inner_html, ensure_ascii=False)};
            el.style.cssText = {json.dumps(style_vars, ensure_ascii=False)};
        }}
    }})();
    """
    web = getattr(mw.deckBrowser, "web", None) if hasattr(mw, "deckBrowser") else None
    if web:
        try:
            web.eval(script)
        except Exception:
            pass


def _on_js_message(handled, message: str, context: Any):
    if isinstance(context, DeckBrowser):
        if message == "ankiZoo_openZoo":
            from . import zoo_dialog
            zoo_dialog.open_zoo_dialog()
            return (True, None)
        if message == "ankiZoo_openSettings":
            from . import zoo_dialog
            zoo_dialog.open_zoo_dialog(initial_tab="settings")
            return (True, None)
    return handled


def register_hooks() -> None:
    from aqt import gui_hooks

    gui_hooks.deck_browser_will_render_content.append(_on_will_render_content)
    gui_hooks.webview_did_receive_js_message.append(_on_js_message)
