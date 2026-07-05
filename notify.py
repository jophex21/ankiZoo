from __future__ import annotations

import json
from typing import Any, Dict

from aqt import mw


def _active_webviews():
    webviews = []
    state = getattr(mw, "state", None)
    reviewer = getattr(mw, "reviewer", None)
    overview = getattr(mw, "overview", None)
    deck_browser = getattr(mw, "deckBrowser", None)

    ordered = []
    if state == "review":
        ordered = [reviewer, overview, deck_browser]
    elif state == "overview":
        ordered = [overview, deck_browser, reviewer]
    else:
        ordered = [deck_browser, overview, reviewer]

    for obj in ordered:
        web = getattr(obj, "web", None)
        if web and web not in webviews:
            webviews.append(web)
    return webviews


def show_toast(title: str, description: str = "", kind: str = "info") -> None:
    """Show a small toast in whichever ankiZoo-aware webview is currently visible.

    Silently no-ops if AnkiZooToast hasn't been injected into that webview
    (e.g. Onigiri or another add-on has taken over deck_browser rendering
    in a way that dropped our script tag) -- this is cosmetic only.
    """
    payload: Dict[str, Any] = {"title": title, "description": description, "kind": kind}
    payload_json = json.dumps(payload, ensure_ascii=False)
    script = (
        "(function() {"
        f"const p = {payload_json};"
        "if (window.AnkiZooToast) { window.AnkiZooToast.show(p); }"
        "})();"
    )
    for web in _active_webviews():
        try:
            web.eval(script)
            break
        except Exception:
            continue
