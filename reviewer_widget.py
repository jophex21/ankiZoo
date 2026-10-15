from __future__ import annotations

import json
from typing import Any

from aqt import mw
from aqt.reviewer import Reviewer

from . import config, economy, leveling, notify, pomodoro
from .deck_browser_widget import TOAST_ASSETS
from .zoo_data import get_zoo_data

# All sizes/colors come from `--az-<key>` variables (config.REVIEWER_STYLE),
# set on :root by _style_vars_css(); the fallbacks here are the defaults /
# Anki theme. Custom properties inherit into Onigiri's shadow header too.
POMODORO_CSS = """
/* Small circle with a progress ring; click opens a menu above it. */
#ankizoo-pomodoro { position: fixed; right: var(--az-pomodoroOffsetPx, 14px); bottom: var(--az-pomodoroOffsetPx, 14px);
    z-index: 9998; --az-pomo-p: 0; font-family: -apple-system, sans-serif;
    color: var(--az-pomodoroTextColor, var(--fg, #f2f2f2)); transition: opacity 0.25s; }
#ankizoo-pomodoro.az-pomo-dim { opacity: var(--az-pomodoroDimOpacity, 0.35); }
#ankizoo-pomodoro.az-pomo-dim:hover, #ankizoo-pomodoro.az-pomo-open { opacity: 1; }
#ankizoo-pomodoro .az-pomo-circle { position: relative; width: var(--az-pomodoroSizePx, 40px);
    height: var(--az-pomodoroSizePx, 40px); border-radius: 50%; border: none; padding: 0; cursor: pointer;
    color: inherit; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    background: conic-gradient(var(--az-pomodoroRingColor, #6fbf73) calc(var(--az-pomo-p) * 1turn),
        var(--az-pomodoroTrackColor, var(--border, #444)) 0); }
#ankizoo-pomodoro .az-pomo-circle::before { content: ""; position: absolute; inset: var(--az-pomodoroRingPx, 3px);
    border-radius: 50%; background: var(--az-pomodoroBgColor, var(--canvas-elevated, #2b2f36)); }
#ankizoo-pomodoro .az-pomo-time { position: relative; font-size: var(--az-pomodoroFontPx, 11px); font-weight: 700;
    font-variant-numeric: tabular-nums; line-height: 1; }
#ankizoo-pomodoro .az-pomo-time svg { width: calc(var(--az-pomodoroSizePx, 40px) * 0.45);
    height: calc(var(--az-pomodoroSizePx, 40px) * 0.45); display: block; opacity: 0.8; }
#ankizoo-pomodoro .az-pomo-menu { display: none; position: absolute; right: 0; bottom: calc(100% + 8px);
    min-width: 150px; flex-direction: column; gap: 6px; padding: 10px; border-radius: 10px;
    background: var(--az-pomodoroMenuBgColor, var(--az-pomodoroBgColor, var(--canvas-elevated, #2b2f36)));
    border: 1px solid var(--az-pomodoroMenuBorderColor, var(--border, #444));
    color: var(--az-pomodoroMenuTextColor, inherit); box-shadow: 0 4px 14px rgba(0,0,0,0.3); font-size: 13px; }
#ankizoo-pomodoro.az-pomo-open .az-pomo-menu { display: flex; }
#ankizoo-pomodoro .az-pomo-menu-title { font-weight: 700; font-variant-numeric: tabular-nums; text-align: center; }
#ankizoo-pomodoro .az-pomo-menu button { border: none; border-radius: 8px; padding: 6px 10px; font-size: 12px;
    cursor: pointer; background: var(--az-pomodoroStartColor, #3f9142); color: var(--az-pomodoroButtonTextColor, white); }
#ankizoo-pomodoro .az-pomo-menu button.az-pomo-cancel { background: var(--az-pomodoroCancelColor, #8a3f3f); }
#ankizoo-pomodoro .az-pomo-menu button.az-pomo-link { background: transparent; color: inherit; opacity: 0.7; padding: 2px; }
#ankizoo-pomodoro .az-pomo-menu button.az-pomo-link:hover { opacity: 1; }
"""

CHIP_CSS = """
/* One seamless pill, matching Onigiri's restaurant-level-chip structure:
   a single rounded box with the progress fill absolutely positioned behind
   the text, rather than several separate boxes stitched together.
   Fixed top-right by default; when Onigiri's reviewer header is present,
   JS moves the chip into that header instead (see CHIP_POSITION_SCRIPT). */
#ankizoo-level-chip { position: fixed; top: var(--az-chipOffsetPx, 20px); right: var(--az-chipOffsetPx, 20px);
    z-index: 9998; cursor: pointer; display: flex; align-items: center; box-sizing: border-box;
    width: var(--az-chipWidthPx, 230px); height: var(--az-chipHeightPx, 28px); opacity: var(--az-chipOpacity, 1);
    background: var(--az-chipBgColor, rgba(0, 0, 0, 0.2)); border: 1px solid var(--az-chipBorderColor, rgba(255, 255, 255, 0.1));
    border-radius: var(--az-chipRadiusPx, 12px); box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden;
    font-family: -apple-system, sans-serif; }
#ankizoo-level-chip:hover { box-shadow: 0 3px 6px rgba(0,0,0,0.15); }
#ankizoo-level-chip .az-chip-progress-bar { position: absolute; left: 0; top: 0; height: 100%;
    background: linear-gradient(90deg, var(--az-chipBarStartColor, #6fbf73), var(--az-chipBarEndColor, #3f9142));
    border-radius: max(0px, calc(var(--az-chipRadiusPx, 12px) - 4px));
    transition: width 0.5s ease-out; box-shadow: 0 0 10px rgba(76, 175, 80, 0.3); }
#ankizoo-level-chip .az-chip-progress-text { position: relative; z-index: 2; display: flex;
    justify-content: space-between; align-items: center; width: 100%; height: 100%;
    padding: 0 var(--az-chipPaddingPx, 10px); box-sizing: border-box; font-size: var(--az-chipFontPx, 12px);
    font-weight: 600; color: var(--az-chipTextColor, white); text-shadow: 0 1px 2px rgba(0,0,0,0.7); gap: 6px; }
#ankizoo-level-chip .az-chip-level-text { font-weight: 700; text-shadow: none; flex-shrink: 0; }
#ankizoo-level-chip .az-chip-xp-text, #ankizoo-level-chip .az-chip-coins { font-size: calc(var(--az-chipFontPx, 12px) - 1px);
    font-weight: 500; opacity: 0.95; background: rgba(0, 0, 0, 0.25); padding: 2px 6px;
    border-radius: 4px; white-space: nowrap; }
#ankizoo-level-chip .az-chip-coins { color: var(--az-chipCoinsColor, #f2c96a); font-weight: 700; }
#ankizoo-level-chip .az-chip-coin-icon { width: 1.15em; height: 1.15em; vertical-align: -0.22em; margin-right: 2px; }
"""

# Inside Onigiri's header the chip flows inline with its buttons instead of
# floating, so Onigiri's own #qa offset makes room for it.
CHIP_IN_HEADER_CSS = CHIP_CSS + """
#ankizoo-level-chip { position: relative; top: auto; right: auto; left: auto; margin-left: 6px; flex-shrink: 0; }
"""

WIDGET_CSS = "<style>" + POMODORO_CSS + CHIP_CSS + "</style>"

# Defined once per genuine page load (via webview_will_set_content, where
# <script> tags actually execute). Re-injections after that go through
# insertAdjacentHTML, which never executes embedded <script> tags -- so the
# tick loop has to be a persistent named function we call explicitly with eval,
# not a script tag bundled into the re-injected fragment.
TICK_SCRIPT = """
<script>
window.ankiZooTogglePomoMenu = function(ev) {
    if (ev) { ev.stopPropagation(); ev.currentTarget.blur(); }  // keep Space/Enter for Anki
    const el = document.getElementById('ankizoo-pomodoro');
    if (el) el.classList.toggle('az-pomo-open');
};
document.addEventListener('click', function(ev) {
    const el = document.getElementById('ankizoo-pomodoro');
    if (el && !el.contains(ev.target)) el.classList.remove('az-pomo-open');
});
window.ankiZooStartPomodoroTick = function() {
    if (window.__ankiZooPomodoroTick) clearInterval(window.__ankiZooPomodoroTick);
    let firedComplete = false;
    const pad = (n) => String(n).padStart(2, '0');
    function tick() {
        const el = document.getElementById('ankizoo-pomodoro');
        if (!el || el.dataset.running !== '1') return;
        const remaining = Math.max(0, parseFloat(el.dataset.end) - (Date.now() / 1000));
        const total = parseFloat(el.dataset.total) || 1;
        const mmss = Math.floor(remaining / 60) + ':' + pad(Math.floor(remaining % 60));
        const timeEl = document.getElementById('az-pomo-time');
        if (timeEl) timeEl.textContent = el.dataset.format === 'mm' ? Math.ceil(remaining / 60) + 'm' : mmss;
        const menuTime = document.getElementById('az-pomo-menu-time');
        if (menuTime) menuTime.textContent = mmss + ' left';
        el.style.setProperty('--az-pomo-p', remaining / total);
        if (remaining <= 0 && !firedComplete) {
            firedComplete = true;
            pycmd('ankiZoo_completePomodoro');
        }
    }
    tick();
    window.__ankiZooPomodoroTick = setInterval(tick, 1000);
};
window.ankiZooStartPomodoroTick();
</script>
"""

# Keeps the floating widgets from covering the card. With Onigiri's reviewer
# header present (it lives in a shadow root under #onigiri-reviewer-ui-host),
# the chip is moved into that header's button row and Onigiri re-offsets #qa
# itself. Otherwise the chip floats top-right and we pad <body> so the card
# starts below it. The Pomodoro timer likewise reserves space at the bottom.
# Re-checked every second since Onigiri's header can appear after load.
CHIP_POSITION_SCRIPT = (
    """
<script>
window.ankiZooChipInHeaderCss = """
    + json.dumps("<style id='ankizoo-shadow-style'>" + CHIP_IN_HEADER_CSS + "</style>")
    + """;
window.ankiZooOnigiriHeader = function() {
    const host = document.getElementById('onigiri-reviewer-ui-host');
    const header = host && host.shadowRoot && host.shadowRoot.getElementById('onigiri-reviewer-header');
    return header && header.offsetHeight > 0 ? header : null;
};
window.ankiZooGetChip = function() {
    const host = document.getElementById('onigiri-reviewer-ui-host');
    return document.getElementById('ankizoo-level-chip')
        || (host && host.shadowRoot && host.shadowRoot.getElementById('ankizoo-level-chip'));
};
window.ankiZooPositionChip = function() {
    const chip = window.ankiZooGetChip();
    const body = document.body;
    const header = window.ankiZooOnigiriHeader();
    let headerChanged = false;

    if (chip && header) {
        const row = header.querySelector('.onigiri-reviewer-header-buttons') || header;
        const root = header.getRootNode();
        if (!root.getElementById('ankizoo-shadow-style')) {
            root.appendChild(document.createRange().createContextualFragment(window.ankiZooChipInHeaderCss));
        }
        if (chip.parentNode !== row) { row.appendChild(chip); headerChanged = true; }
    } else if (chip && chip.getRootNode() !== document) {
        body.appendChild(chip);  // Onigiri header went away; float again.
    }

    const visible = chip && chip.style.display !== 'none';
    const state = (header ? 'h' : 'f') + (visible ? '1' : '0');
    if (state !== window.__ankiZooChipState) { window.__ankiZooChipState = state; headerChanged = true; }
    if (header && headerChanged && typeof window.onigiriRefreshReviewerHeaderOffset === 'function') {
        window.onigiriRefreshReviewerHeaderOffset();
    }

    const baseTop = parseFloat(getComputedStyle(body).marginTop) || 0;
    body.style.paddingTop = (!header && visible)
        ? Math.max(0, chip.getBoundingClientRect().bottom + 8 - baseTop) + 'px' : '';

    const pomo = document.getElementById('ankizoo-pomodoro');
    body.style.paddingBottom = (pomo && pomo.style.display !== 'none')
        ? (window.innerHeight - pomo.getBoundingClientRect().top + 8) + 'px' : '';
};
window.ankiZooPositionChip();
window.addEventListener('resize', window.ankiZooPositionChip);
if (window.__ankiZooChipPositionInterval) clearInterval(window.__ankiZooChipPositionInterval);
window.__ankiZooChipPositionInterval = setInterval(window.ankiZooPositionChip, 1000);
</script>
"""
)


def _style_vars_css() -> str:
    return config.style_vars_css(config.get_config(), ("pomo", "chip"))


def apply_style() -> None:
    """Live-apply Settings-tab appearance changes to an open reviewer."""
    reviewer = getattr(mw, "reviewer", None)
    web = getattr(reviewer, "web", None) if reviewer else None
    if not web or mw.state != "review":
        return
    script = f"""
    (function() {{
        const tag = document.getElementById('ankizoo-style-vars');
        if (tag) tag.textContent = {json.dumps(_style_vars_css())};
    }})();
    """
    try:
        web.eval(script)
    except Exception:
        pass
    _reload_reviewer_widget()  # dim mode / time format live in the markup


def _hidden_style(conf_key: str) -> str:
    return "" if config.get_config().get(conf_key, True) else ' style="display: none;"'


def apply_visibility() -> None:
    """Live-apply the Settings-tab show/hide toggles to an open reviewer."""
    reviewer = getattr(mw, "reviewer", None)
    web = getattr(reviewer, "web", None) if reviewer else None
    if not web:
        return
    conf = config.get_config()
    vis = {
        "ankizoo-pomodoro": conf.get("reviewerShowPomodoro", True),
        "ankizoo-level-chip": conf.get("reviewerShowHeader", True),
    }
    script = f"""
    (function() {{
        const vis = {json.dumps(vis)};
        Object.keys(vis).forEach((id) => {{
            const el = id === 'ankizoo-level-chip' && window.ankiZooGetChip
                ? window.ankiZooGetChip() : document.getElementById(id);
            if (el) el.style.display = vis[id] ? '' : 'none';
        }});
        if (window.ankiZooPositionChip) window.ankiZooPositionChip();
    }})();
    """
    try:
        web.eval(script)
    except Exception:
        pass


TIMER_ICON_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'
    '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2.5M9 2h6"/></svg>'
)


def _widget_markup() -> str:
    conf = config.get_config()
    style = config.style_values(conf)
    running = pomodoro.is_running()
    end_epoch = pomodoro.target_end_epoch()
    total_secs = pomodoro.duration_minutes() * 60
    minutes = pomodoro.default_minutes()

    dim_mode = style["pomodoroDim"]
    dim = dim_mode == "always" or dim_mode == ("running" if running else "idle")

    if running:
        menu = (
            '<div class="az-pomo-menu-title" id="az-pomo-menu-time"></div>'
            '<button class="az-pomo-cancel" onclick="this.blur(); pycmd(\'ankiZoo_cancelPomodoro\')">Cancel</button>'
        )
        face = ""  # filled by the tick loop
    else:
        menu = (
            f'<div class="az-pomo-menu-title">Pomodoro \u00b7 {minutes} min</div>'
            '<button onclick="this.blur(); pycmd(\'ankiZoo_startPomodoro\')">Start</button>'
        )
        face = TIMER_ICON_SVG
    menu += '<button class="az-pomo-link" onclick="this.blur(); pycmd(\'ankiZoo_openPomodoroSettings\')">Settings\u2026</button>'

    return f"""
    <div id="ankizoo-pomodoro" class="{'az-pomo-dim' if dim else ''}"{_hidden_style("reviewerShowPomodoro")}
         data-running="{'1' if running else '0'}" data-end="{end_epoch or ''}" data-total="{total_secs}"
         data-format="{style['pomodoroTimeFormat']}">
        <div class="az-pomo-menu">{menu}</div>
        <button class="az-pomo-circle" aria-label="Pomodoro timer" title="Pomodoro timer"
                onclick="ankiZooTogglePomoMenu(event)"><span class="az-pomo-time" id="az-pomo-time">{face}</span></button>
    </div>
    """


def _coin_icon_html() -> str:
    from .zoo_dialog import _coin_data_uri  # lazy: zoo_dialog lazily imports this module too
    uri = _coin_data_uri()
    return f'<img class="az-chip-coin-icon" src="{uri}" alt="coins">' if uri else "\U0001FA99"


def _level_chip_markup() -> str:
    data = get_zoo_data()
    state = data.state
    progress = leveling.get_progress(state.total_xp)
    level, percent = progress.level, progress.percent
    xp_label = f"{progress.xp_into}/{progress.xp_next} XP" if progress.xp_next > 0 else "Max level"

    return f"""
    <div id="ankizoo-level-chip"{_hidden_style("reviewerShowHeader")} onclick="pycmd('ankiZoo_openZoo')">
        <div class="az-chip-progress-bar" id="az-chip-progress-bar" style="width: {percent}%;"></div>
        <div class="az-chip-progress-text">
            <span class="az-chip-level-text" id="az-chip-level-text">Lv. {level}</span>
            <span class="az-chip-xp-text" id="az-chip-xp-text">{xp_label}</span>
            <span class="az-chip-coins">{_coin_icon_html()}<span id="az-chip-coins">{state.coins}</span></span>
        </div>
    </div>
    """


def _on_will_set_content(web_content: Any, context: Any) -> None:
    if not isinstance(context, Reviewer):
        return
    try:
        web_content.body += (
            TOAST_ASSETS + WIDGET_CSS + f'<style id="ankizoo-style-vars">{_style_vars_css()}</style>' + _widget_markup() + _level_chip_markup() + CHIP_POSITION_SCRIPT + TICK_SCRIPT
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
        const chip = window.ankiZooGetChip ? window.ankiZooGetChip() : document.getElementById('ankizoo-level-chip');
        if (!chip) return;
        const bar = chip.querySelector('#az-chip-progress-bar'); if (bar) bar.style.width = p.percent + '%';
        const levelEl = chip.querySelector('#az-chip-level-text'); if (levelEl) levelEl.textContent = 'Lv. ' + p.level;
        const xpEl = chip.querySelector('#az-chip-xp-text'); if (xpEl) xpEl.textContent = p.xpLabel;
        const coinsEl = chip.querySelector('#az-chip-coins'); if (coinsEl) coinsEl.textContent = p.coins;
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

    if message == "ankiZoo_openPomodoroSettings":
        from . import zoo_dialog
        zoo_dialog.open_zoo_dialog("settings")
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
    # reviewer.web is mw.web, shared with the deck browser -- only patch it mid-review.
    if not web or mw.state != "review":
        return
    markup_json = json.dumps(_widget_markup())
    script = f"""
    (function() {{
        const old = document.getElementById('ankizoo-pomodoro');
        if (old) old.remove();
        document.body.insertAdjacentHTML('beforeend', {markup_json});
        if (window.ankiZooStartPomodoroTick) window.ankiZooStartPomodoroTick();
        if (window.ankiZooPositionChip) window.ankiZooPositionChip();
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
