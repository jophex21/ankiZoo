from __future__ import annotations

import html
import json
from typing import Any

from aqt import mw
from aqt.deckbrowser import DeckBrowser

from . import animals as animals_module
from . import leveling
from .zoo_data import get_zoo_data

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
.ankizoo-widget { display: flex; align-items: center; gap: 14px; background: var(--canvas-elevated, #f5f5f5);
    border: 1px solid var(--border, #ddd); border-radius: 14px; padding: 12px 16px; margin: 12px auto; max-width: 420px;
    cursor: pointer; font-family: -apple-system, sans-serif; user-select: none; }
.ankizoo-widget:hover { border-color: var(--border-focus, #999); }
.ankizoo-widget .az-hero { width: 48px; height: 48px; image-rendering: pixelated; flex-shrink: 0; }
.ankizoo-widget .az-info { flex: 1; min-width: 0; }
.ankizoo-widget .az-title-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.ankizoo-widget .az-name { font-weight: 700; font-size: 14px; }
.ankizoo-widget .az-rank { font-size: 11px; opacity: 0.75; }
.ankizoo-widget .az-level { font-weight: 800; font-size: 16px; }
.ankizoo-widget .az-bar { height: 8px; border-radius: 999px; background: rgba(120,120,120,0.25); margin: 6px 0 4px; overflow: hidden; }
.ankizoo-widget .az-bar-fill { height: 100%; background: linear-gradient(90deg, #6fbf73, #3f9142); }
.ankizoo-widget .az-stats-row { display: flex; justify-content: space-between; font-size: 12px; opacity: 0.85; }
</style>
"""


def _hero_sprite_uri() -> str:
    data = get_zoo_data()
    owned = data.state.owned_animals
    if owned:
        try:
            animal = animals_module.get_animal(owned[-1])
            return animal["sprite_idle_uri"]
        except KeyError:
            pass
    # Default: first (lowest-level) animal in the catalog, unowned or not.
    catalog = animals_module.get_catalog()
    return catalog[0]["sprite_idle_uri"] if catalog else ""


def get_widget_html() -> str:
    data = get_zoo_data()
    state = data.state
    base = leveling.get_level_base()
    level, xp_into, xp_next = leveling.collapse_xp(state.total_xp, base)
    rank = leveling.rank_for_level(level)
    percent = 0 if xp_next <= 0 else min(100, int(xp_into / xp_next * 100))
    owned_count = len(state.owned_animals)
    total_count = len(animals_module.get_catalog())
    quests_done = sum(1 for q in state.quests if q.get("completed"))
    quests_total = len(state.quests) if state.quests else 3

    hero_uri = _hero_sprite_uri()

    return f"""
    {TOAST_ASSETS}
    {WIDGET_CSS}
    <div class="ankizoo-widget" id="ankizoo-widget" onclick="pycmd('ankiZoo_openZoo')">
        <img class="az-hero" id="az-hero-img" src="{hero_uri}">
        <div class="az-info">
            <div class="az-title-row">
                <span class="az-name">ankiZoo <span class="az-rank" id="az-rank">{html.escape(rank)}</span></span>
                <span class="az-level" id="az-level">Lv. {level}</span>
            </div>
            <div class="az-bar"><div class="az-bar-fill" id="az-bar-fill" style="width: {percent}%;"></div></div>
            <div class="az-stats-row">
                <span id="az-coins">\U0001FA99 {state.coins}</span>
                <span id="az-animals">\U0001F43E {owned_count} / {total_count}</span>
                <span id="az-quests">Quests: {quests_done}/{quests_total}</span>
            </div>
        </div>
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
    base = leveling.get_level_base()
    level, xp_into, xp_next = leveling.collapse_xp(state.total_xp, base)
    rank = leveling.rank_for_level(level)
    percent = 0 if xp_next <= 0 else min(100, int(xp_into / xp_next * 100))
    owned_count = len(state.owned_animals)
    total_count = len(animals_module.get_catalog())
    quests_done = sum(1 for q in state.quests if q.get("completed"))
    quests_total = len(state.quests) if state.quests else 3

    payload = {
        "rank": rank,
        "level": level,
        "percent": percent,
        "coins": state.coins,
        "owned": owned_count,
        "total": total_count,
        "questsDone": quests_done,
        "questsTotal": quests_total,
        "heroUri": _hero_sprite_uri(),
    }
    script = f"""
    (function() {{
        const p = {json.dumps(payload, ensure_ascii=False)};
        const rank = document.getElementById('az-rank'); if (rank) rank.textContent = p.rank;
        const level = document.getElementById('az-level'); if (level) level.textContent = 'Lv. ' + p.level;
        const bar = document.getElementById('az-bar-fill'); if (bar) bar.style.width = p.percent + '%';
        const coins = document.getElementById('az-coins'); if (coins) coins.textContent = '\\u{{1FA99}} ' + p.coins;
        const animalsEl = document.getElementById('az-animals'); if (animalsEl) animalsEl.textContent = '\\u{{1F43E}} ' + p.owned + ' / ' + p.total;
        const quests = document.getElementById('az-quests'); if (quests) quests.textContent = 'Quests: ' + p.questsDone + '/' + p.questsTotal;
        const hero = document.getElementById('az-hero-img'); if (hero) hero.src = p.heroUri;
    }})();
    """
    web = getattr(mw.deckBrowser, "web", None) if hasattr(mw, "deckBrowser") else None
    if web:
        try:
            web.eval(script)
        except Exception:
            pass


def _on_js_message(handled, message: str, context: Any):
    if isinstance(context, DeckBrowser) and message == "ankiZoo_openZoo":
        from . import zoo_dialog
        zoo_dialog.open_zoo_dialog()
        return (True, None)
    return handled


def register_hooks() -> None:
    from aqt import gui_hooks

    gui_hooks.deck_browser_will_render_content.append(_on_will_render_content)
    gui_hooks.webview_did_receive_js_message.append(_on_js_message)
