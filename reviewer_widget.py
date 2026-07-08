from __future__ import annotations

import json
from typing import Any

from aqt import mw
from aqt.reviewer import Reviewer

from . import economy, leveling, notify, pomodoro
from .deck_browser_widget import TOAST_ASSETS
from .zoo_data import get_zoo_data

WIDGET_CSS = """
<style>
#ankizoo-pomodoro { position: fixed; right: 14px; bottom: 14px; z-index: 9998; background: var(--canvas-elevated, #2b2f36);
    color: var(--fg, #f2f2f2); border: 1px solid var(--border, #444); border-radius: 12px; padding: 8px 12px;
    font-family: -apple-system, sans-serif; font-size: 13px; display: flex; align-items: center; gap: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.25); }
#ankizoo-pomodoro .az-pomo-time { font-weight: 700; font-variant-numeric: tabular-nums; min-width: 44px; }
#ankizoo-pomodoro button { border: none; border-radius: 8px; padding: 4px 10px; font-size: 12px; cursor: pointer;
    background: #3f9142; color: white; }
#ankizoo-pomodoro button.az-pomo-cancel { background: #8a3f3f; }

/* One seamless pill, matching Onigiri's restaurant-level-chip structure:
   a single rounded box with the progress fill absolutely positioned behind
   the text, rather than several separate boxes stitched together.
   Default top-right position is used when Onigiri's own reviewer header
   isn't found on the page; when it is, JS repositions this to sit flush
   next to it instead (see ankiZooPositionChip in CHIP_POSITION_SCRIPT). */
#ankizoo-level-chip { position: fixed; top: 20px; right: 20px; z-index: 9998; cursor: pointer;
    display: flex; align-items: center; width: 230px; height: 28px; box-sizing: border-box;
    background: rgba(0, 0, 0, 0.2); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; font-family: -apple-system, sans-serif; }
#ankizoo-level-chip:hover { box-shadow: 0 3px 6px rgba(0,0,0,0.15); }
#ankizoo-level-chip .az-chip-progress-bar { position: absolute; left: 0; top: 0; height: 100%;
    background: linear-gradient(90deg, #6fbf73, #3f9142); border-radius: 8px;
    transition: width 0.5s ease-out; box-shadow: 0 0 10px rgba(76, 175, 80, 0.3); }
#ankizoo-level-chip .az-chip-progress-text { position: relative; z-index: 2; display: flex;
    justify-content: space-between; align-items: center; width: 100%; height: 100%;
    padding: 0 10px; box-sizing: border-box; font-size: 12px; font-weight: 600; color: white;
    text-shadow: 0 1px 2px rgba(0,0,0,0.7); gap: 6px; }
#ankizoo-level-chip .az-chip-level-text { font-weight: 700; text-shadow: none; flex-shrink: 0; }
#ankizoo-level-chip .az-chip-xp-text, #ankizoo-level-chip .az-chip-coins { font-size: 11px;
    font-weight: 500; opacity: 0.95; background: rgba(0, 0, 0, 0.25); padding: 2px 6px;
    border-radius: 4px; white-space: nowrap; }
#ankizoo-level-chip .az-chip-coins { color: #f2c96a; font-weight: 700; }
#ankizoo-level-chip .az-chip-coins::before { content: "\U0001FA99"; margin-right: 2px; }
</style>
"""

# Defined once per genuine page load (via webview_will_set_content, where
# <script> tags actually execute). Re-injections after that go through
# insertAdjacentHTML, which never executes embedded <script> tags -- so the
# tick loop has to be a persistent named function we call explicitly with eval,
# not a script tag bundled into the re-injected fragment.
TICK_SCRIPT = """
<script>
window.ankiZooStartPomodoroTick = function() {
    if (window.__ankiZooPomodoroTick) clearInterval(window.__ankiZooPomodoroTick);
    let firedComplete = false;
    function tick() {
        const el = document.getElementById('ankizoo-pomodoro');
        if (!el) return;
        const timeEl = document.getElementById('az-pomo-time');
        if (el.dataset.running === '1') {
            const end = parseFloat(el.dataset.end);
            const remaining = Math.max(0, end - (Date.now() / 1000));
            const m = Math.floor(remaining / 60);
            const s = Math.floor(remaining % 60);
            if (timeEl) timeEl.textContent = String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
            if (remaining <= 0 && !firedComplete) {
                firedComplete = true;
                pycmd('ankiZoo_completePomodoro');
            }
        }
    }
    tick();
    window.__ankiZooPomodoroTick = setInterval(tick, 1000);
};
window.ankiZooStartPomodoroTick();
</script>
"""

# Aligns the level chip next to Onigiri's reviewer header if present (so it
# reads as one bar instead of floating in a different row), falling back to a
# fixed top-right position when Onigiri isn't installed or that header is
# hidden. Re-checked every second since Onigiri's header can appear/resize
# after this script first runs.
CHIP_POSITION_SCRIPT = """
<script>
window.ankiZooPositionChip = function() {
    const chip = document.getElementById('ankizoo-level-chip');
    if (!chip) return;
    const onigiriHeader = document.getElementById('onigiri-reviewer-header');
    if (onigiriHeader) {
        const rect = onigiriHeader.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
            chip.style.top = rect.top + 'px';
            chip.style.left = (rect.right + 12) + 'px';
            chip.style.right = 'auto';
            chip.style.height = rect.height + 'px';
            return;
        }
    }
    chip.style.top = '20px';
    chip.style.right = '20px';
    chip.style.left = 'auto';
    chip.style.height = '';
};
window.ankiZooPositionChip();
window.addEventListener('resize', window.ankiZooPositionChip);
if (window.__ankiZooChipPositionInterval) clearInterval(window.__ankiZooChipPositionInterval);
window.__ankiZooChipPositionInterval = setInterval(window.ankiZooPositionChip, 1000);
</script>
"""


def _widget_markup() -> str:
    running = pomodoro.is_running()
    end_epoch = pomodoro.target_end_epoch()
    minutes = pomodoro.default_minutes()

    if running:
        button_html = '<button class="az-pomo-cancel" onclick="pycmd(\'ankiZoo_cancelPomodoro\')">Cancel</button>'
    else:
        button_html = '<button onclick="pycmd(\'ankiZoo_startPomodoro\')">Start Pomodoro</button>'

    return f"""
    <div id="ankizoo-pomodoro" data-running="{'1' if running else '0'}" data-end="{end_epoch or ''}" data-minutes="{minutes}">
        <span class="az-pomo-time" id="az-pomo-time">{minutes:02d}:00</span>
        {button_html}
    </div>
    """


def _level_chip_markup() -> str:
    data = get_zoo_data()
    state = data.state
    progress = leveling.get_progress(state.total_xp)
    level, percent = progress.level, progress.percent
    xp_label = f"{progress.xp_into}/{progress.xp_next} XP" if progress.xp_next > 0 else "Max level"

    return f"""
    <div id="ankizoo-level-chip" onclick="pycmd('ankiZoo_openZoo')">
        <div class="az-chip-progress-bar" id="az-chip-progress-bar" style="width: {percent}%;"></div>
        <div class="az-chip-progress-text">
            <span class="az-chip-level-text" id="az-chip-level-text">Lv. {level}</span>
            <span class="az-chip-xp-text" id="az-chip-xp-text">{xp_label}</span>
            <span class="az-chip-coins" id="az-chip-coins">{state.coins}</span>
        </div>
    </div>
    """


def _on_will_set_content(web_content: Any, context: Any) -> None:
    if not isinstance(context, Reviewer):
        return
    try:
        web_content.body += (
            TOAST_ASSETS + WIDGET_CSS + _widget_markup() + _level_chip_markup() + CHIP_POSITION_SCRIPT + TICK_SCRIPT
        )
    except Exception as e:
        print(f"ankiZoo: error injecting reviewer widgets: {e}")


def refresh_active_widget() -> None:
    """Live-patch the level chip's numbers after each answer; the Pomodoro
    widget's own display doesn't depend on XP/coins so it's left alone."""
    reviewer = getattr(mw, "reviewer", None)
    web = getattr(reviewer, "web", None) if reviewer else None
    if not web or mw.state != "review":
        return

    data = get_zoo_data()
    state = data.state
    progress = leveling.get_progress(state.total_xp)
    level, percent = progress.level, progress.percent
    xp_label = f"{progress.xp_into}/{progress.xp_next} XP" if progress.xp_next > 0 else "Max level"

    payload = {"level": level, "percent": percent, "xpLabel": xp_label, "coins": state.coins}
    script = f"""
    (function() {{
        const p = {json.dumps(payload, ensure_ascii=False)};
        const bar = document.getElementById('az-chip-progress-bar'); if (bar) bar.style.width = p.percent + '%';
        const levelEl = document.getElementById('az-chip-level-text'); if (levelEl) levelEl.textContent = 'Lv. ' + p.level;
        const xpEl = document.getElementById('az-chip-xp-text'); if (xpEl) xpEl.textContent = p.xpLabel;
        const coinsEl = document.getElementById('az-chip-coins'); if (coinsEl) coinsEl.textContent = p.coins;
    }})();
    """
    try:
        web.eval(script)
    except Exception:
        pass


def _on_js_message(handled, message: str, context: Any):
    if not isinstance(context, Reviewer):
        return handled

    if message == "ankiZoo_openZoo":
        from . import zoo_dialog
        zoo_dialog.open_zoo_dialog()
        return (True, None)

    if message == "ankiZoo_startPomodoro":
        pomodoro.start()
        _reload_reviewer_widget()
        return (True, None)

    if message == "ankiZoo_cancelPomodoro":
        pomodoro.cancel()
        _reload_reviewer_widget()
        return (True, None)

    if message == "ankiZoo_completePomodoro":
        if pomodoro.is_complete():
            loot = pomodoro.complete_and_roll()
            data = get_zoo_data()
            data.state.coins += int(loot["amount"])
            data.save()
            notify.show_toast(
                "Loot Box Opened!",
                f"You found {loot['amount']} coins ({loot['tier']})!",
                kind="loot",
            )
            economy._refresh_widgets()
        _reload_reviewer_widget()
        return (True, None)

    return handled


def _reload_reviewer_widget() -> None:
    reviewer = getattr(mw, "reviewer", None)
    web = getattr(reviewer, "web", None) if reviewer else None
    if not web:
        return
    markup_json = json.dumps(_widget_markup())
    script = f"""
    (function() {{
        const old = document.getElementById('ankizoo-pomodoro');
        if (old) old.remove();
        document.body.insertAdjacentHTML('beforeend', {markup_json});
        if (window.ankiZooStartPomodoroTick) window.ankiZooStartPomodoroTick();
    }})();
    """
    try:
        web.eval(script)
    except Exception:
        pass


def register_hooks() -> None:
    from aqt import gui_hooks

    gui_hooks.webview_will_set_content.append(_on_will_set_content)
    gui_hooks.webview_did_receive_js_message.append(_on_js_message)
